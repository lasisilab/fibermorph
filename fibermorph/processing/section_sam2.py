"""Cross-section segmentation using SAM2 (GPU) with watershed fallback (CPU).

All SAM2 imports are guarded by try/except so the module loads cleanly without
the optional sam2 package installed.

Public API
----------
segment_section(gray_img, resolution_mu, min_diam, max_diam,
                use_sam2, checkpoint, model_cfg)
    -> (mask_uint8, confidence, method_str) or None
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional SAM2 import (guarded)
# ---------------------------------------------------------------------------
_SAM2_AVAILABLE       = False
_SAM2_IMPORT_ERROR    = ""
_sam2_generator       = None
_sam2_init_logged     = False

try:
    import torch                                           # noqa: F401
    from sam2.build_sam import build_sam2                  # noqa: F401
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator  # noqa: F401
    _SAM2_AVAILABLE = True
except Exception as _e:
    _SAM2_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

# Default checkpoint paths (resolved relative to the fibermorph package root)
_PKG_ROOT        = Path(__file__).resolve().parents[2]
_DEFAULT_CKPT    = str(_PKG_ROOT / "checkpoints" / "sam2.1_hiera_tiny.pt")
_DEFAULT_CFG     = "configs/sam2.1/sam2.1_hiera_t.yaml"

RESOLUTION_MU = 4.25
_MIN_DIAM_MU  = 30.0
_MAX_DIAM_MU  = 150.0


# ---------------------------------------------------------------------------
# SAM2 generator singleton
# ---------------------------------------------------------------------------

def _get_sam2_generator(checkpoint: str = _DEFAULT_CKPT,
                         model_cfg: str  = _DEFAULT_CFG):
    global _sam2_generator, _sam2_init_logged

    if _sam2_generator is not None:
        return _sam2_generator

    if not _SAM2_AVAILABLE:
        if not _sam2_init_logged:
            logger.warning(
                f"SAM2 import failed ({_SAM2_IMPORT_ERROR}) — using watershed fallback. "
                "Install with: pip install git+https://github.com/facebookresearch/segment-anything-2"
            )
            _sam2_init_logged = True
        return None

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"  # noqa: F821
        if device == "cpu":
            if not _sam2_init_logged:
                logger.warning(
                    "SAM2: No CUDA GPU detected — falling back to watershed. "
                    "Submit to a GPU partition (--partition=spgpu --gpus=1) to enable SAM2."
                )
                _sam2_init_logged = True
            return None

        ckpt = checkpoint or os.environ.get("SAM2_CHECKPOINT", _DEFAULT_CKPT)
        if not os.path.exists(ckpt):
            if not _sam2_init_logged:
                logger.warning(f"SAM2 checkpoint not found: {ckpt} — using watershed fallback.")
                _sam2_init_logged = True
            return None

        logger.info(f"SAM2: Loading model on {device} from {ckpt}")
        sam2 = build_sam2(model_cfg, ckpt, device=device, apply_postprocessing=True)  # noqa: F821
        _sam2_generator = SAM2AutomaticMaskGenerator(  # noqa: F821
            model=sam2,
            points_per_side=32,
            points_per_batch=16,
            stability_score_threshold=0.92,
            pred_iou_thresh=0.9,
        )
        logger.info("SAM2: Model loaded successfully.")
        return _sam2_generator

    except Exception as exc:
        if not _sam2_init_logged:
            logger.warning(f"SAM2 load failed: {exc} — using watershed fallback.")
            _sam2_init_logged = True
        return None


# ---------------------------------------------------------------------------
# Watershed segmentation (CPU — always available)
# ---------------------------------------------------------------------------

def _watershed_segment(
    img_gray: np.ndarray,
    resolution_mu: float = RESOLUTION_MU,
    min_diam: float      = _MIN_DIAM_MU,
    max_diam: float      = _MAX_DIAM_MU,
):
    """Multi-factor candidate scoring: centre-bias + circularity + solidity + darkness."""
    from skimage.measure import regionprops, label as sk_label
    from skimage.morphology import opening, closing, disk

    h, w = img_gray.shape
    roi_top = int(0.15 * h)
    roi_bot = int(0.85 * h)

    _, thresh_roi = cv2.threshold(
        img_gray[roi_top:roi_bot, :], 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    binary = np.zeros_like(img_gray, dtype=np.uint8)
    binary[roi_top:roi_bot, :] = thresh_roi

    k      = disk(3)
    binary = (opening(binary, k) > 0).astype(np.uint8) * 255
    binary = (closing(binary, k) > 0).astype(np.uint8) * 255

    labels = sk_label(binary > 0)

    min_px = min_diam * resolution_mu
    max_px = max_diam * resolution_mu

    candidates = []
    for region in regionprops(labels):
        maj = region.major_axis_length
        if not (min_px <= maj <= max_px):
            continue
        circ  = min(4 * np.pi * region.area / (region.perimeter ** 2 + 1e-10), 1.0) \
                if region.perimeter > 0 else 0.0
        solid = region.solidity
        cy, cx = region.centroid
        dist_c = np.sqrt((cy - h / 2) ** 2 + (cx - w / 2) ** 2)
        intensity = float(img_gray[labels == region.label].mean())
        candidates.append({
            "region": region,
            "circ": circ, "solidity": solid,
            "dist": dist_c, "intensity": intensity,
        })

    if not candidates:
        return None

    max_dist  = max(c["dist"]      for c in candidates)
    max_int   = max(c["intensity"] for c in candidates)
    min_int   = min(c["intensity"] for c in candidates)
    int_range = max_int - min_int + 1e-10

    for c in candidates:
        nd   = c["dist"] / max_dist if max_dist > 0 else 0.0
        dark = (c["intensity"] - min_int) / int_range
        c["score"] = (0.35 * (1.0 - nd) +
                      0.25 * c["circ"] +
                      0.25 * c["solidity"] +
                      0.15 * (1.0 - dark))

    best   = max(candidates, key=lambda x: x["score"])
    region = best["region"]
    mask   = np.zeros(img_gray.shape, dtype=np.uint8)
    mask[labels == region.label] = 255
    conf   = 0.7 * best["circ"] + 0.3 * best["solidity"]
    return mask, float(conf), "watershed"


# ---------------------------------------------------------------------------
# SAM2 segmentation
# ---------------------------------------------------------------------------

def _sam2_segment(
    img_gray: np.ndarray,
    resolution_mu: float = RESOLUTION_MU,
    min_diam: float      = _MIN_DIAM_MU,
    max_diam: float      = _MAX_DIAM_MU,
    checkpoint: str      = _DEFAULT_CKPT,
    model_cfg: str       = _DEFAULT_CFG,
):
    from skimage.measure import regionprops

    gen = _get_sam2_generator(checkpoint, model_cfg)
    if gen is None:
        return None

    img_rgb = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)
    h, w    = img_gray.shape

    try:
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):  # noqa: F821
            masks = gen.generate(img_rgb)
    except Exception as exc:
        logger.debug(f"SAM2 generate() failed: {exc}")
        return None

    min_px = min_diam * resolution_mu
    max_px = max_diam * resolution_mu
    candidates = []

    for m in masks:
        seg   = m["segmentation"].astype(np.uint8)
        rp    = regionprops(seg)
        if not rp:
            continue
        props = rp[0]
        if not (min_px <= props.major_axis_length <= max_px):
            continue
        cy, cx = props.centroid
        dist_c    = np.sqrt((cy - h / 2) ** 2 + (cx - w / 2) ** 2)
        circ      = min(4 * np.pi * props.area / (props.perimeter ** 2 + 1e-10), 1.0) \
                    if props.perimeter > 0 else 0.0
        intensity = float(img_gray[seg > 0].mean())
        candidates.append({
            "mask": seg, "iou": m["predicted_iou"],
            "dist": dist_c, "circ": circ,
            "solidity": props.solidity, "intensity": intensity,
        })

    if not candidates:
        return None

    max_dist  = max(c["dist"]      for c in candidates)
    max_iou   = max(c["iou"]       for c in candidates)
    max_int   = max(c["intensity"] for c in candidates)
    min_int   = min(c["intensity"] for c in candidates)
    int_range = max_int - min_int + 1e-10

    for c in candidates:
        nd   = c["dist"] / max_dist if max_dist > 0 else 0.0
        ni   = c["iou"]  / max_iou  if max_iou  > 0 else 0.0
        dark = (c["intensity"] - min_int) / int_range
        c["score"] = (0.35 * (1.0 - nd) +
                      0.25 * c["circ"] +
                      0.25 * c["solidity"] +
                      0.15 * (1.0 - dark) +
                      0.10 * ni)

    best = max(candidates, key=lambda x: x["score"])
    mask = (best["mask"] * 255).astype(np.uint8)
    return mask, float(best["iou"]), "sam2"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def segment_section(
    gray_img: np.ndarray,
    resolution_mu: float = RESOLUTION_MU,
    min_diam: float      = _MIN_DIAM_MU,
    max_diam: float      = _MAX_DIAM_MU,
    use_sam2: bool       = False,
    checkpoint: str      = _DEFAULT_CKPT,
    model_cfg: str       = _DEFAULT_CFG,
):
    """Segment a hair cross-section from a grayscale microscopy image.

    Tries SAM2 (when use_sam2=True and GPU available), then falls back
    to watershed automatically.

    Parameters
    ----------
    gray_img      : 2D uint8 grayscale image
    resolution_mu : pixels per µm
    min_diam      : minimum diameter threshold in µm
    max_diam      : maximum diameter threshold in µm
    use_sam2      : attempt SAM2 segmentation first
    checkpoint    : path to SAM2 model checkpoint
    model_cfg     : SAM2 model config file

    Returns
    -------
    (mask_uint8, confidence, method_str) or None if no candidate found
    """
    if use_sam2:
        result = _sam2_segment(gray_img, resolution_mu, min_diam, max_diam,
                               checkpoint, model_cfg)
        if result is not None:
            return result

    return _watershed_segment(gray_img, resolution_mu, min_diam, max_diam)
