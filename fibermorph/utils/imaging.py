"""Image utilities — resolution-aware downsampling.

Cross-section scans are often 20 MP / tens of MB, far more pixels than a shape
measurement needs. Downsampling to a target working resolution (and scaling the
resolution together with the pixel count) keeps the µm measurements essentially
unchanged (<0.5% on area/eccentricity in testing) while making processing much
lighter.
"""

from __future__ import annotations

import cv2
import numpy as np

# Target working resolution for cross-section analysis, in PIXELS PER µm. A
# ~100 µm section is ~200 px across at 2.0 px/µm — ample for area/eccentricity/EFD.
TARGET_SECTION_RES_MU = 2.0


# Never shrink an image below this longest-side (px); protects already-small
# images from being over-reduced.
MIN_LONG_SIDE = 400


def downsample_to_resolution(
    gray: np.ndarray,
    resolution_mu: float | None,
    target: float = TARGET_SECTION_RES_MU,
    min_long_side: int = MIN_LONG_SIDE,
) -> tuple[np.ndarray, float | None]:
    """Downsample ``gray`` so its working resolution is ~= ``target`` px/µm.

    Never upsamples, and never shrinks the longest side below ``min_long_side``.
    Returns ``(gray_out, effective_resolution_mu)`` where the effective
    resolution reflects the actual (rounded) resize ratio, so µm measurements
    computed at that resolution match the full-resolution values.

    If ``resolution_mu`` is None, already <= target, or the image is already
    small, it is returned unchanged.
    """
    if resolution_mu is None or resolution_mu <= target:
        return gray, resolution_mu

    factor = resolution_mu / target
    if max(gray.shape[:2]) / factor < min_long_side:
        return gray, resolution_mu

    new_w  = max(1, round(gray.shape[1] / factor))
    new_h  = max(1, round(gray.shape[0] / factor))
    gray_ds = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    effective_res = resolution_mu * (new_w / gray.shape[1])
    return gray_ds, effective_res
