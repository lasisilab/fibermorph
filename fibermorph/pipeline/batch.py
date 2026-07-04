"""Batch processor for section and/or curvature image directories.

Produces one CSV in output_dir:
  hair_analysis_per_image.csv   — one row per source image, carrying the source
                                  filename. No grouping/aggregation is performed;
                                  that is left to downstream analysis.

Section and curvature pipelines run independently; either can be omitted.
"""

from __future__ import annotations

import os
import pathlib
from typing import Callable

import numpy as np
import pandas as pd
from tqdm import tqdm

from ..utils.metadata import collect_images


def _process_dir(
    image_paths: list,
    process_fn: Callable,
    image_type: str,
    process_kwargs: dict,
) -> list:
    rows: list = []
    failed = 0
    for path in tqdm(image_paths, desc=f"  {image_type}", unit="img", ncols=80):
        fname = os.path.basename(path)
        try:
            result = process_fn(path, **process_kwargs)
            if result is None:
                failed += 1
                continue
            # result may be a dict (extended) or a pd.DataFrame (legacy)
            if isinstance(result, dict):
                row = {"image_type": image_type, "source_file": fname}
                row.update(result)
                rows.append(row)
            elif isinstance(result, pd.DataFrame) and not result.empty:
                row_dict = result.iloc[0].to_dict()
                row_dict["image_type"]  = image_type
                row_dict["source_file"] = fname
                rows.append(row_dict)
            else:
                failed += 1
        except Exception as exc:
            print(f"    WARNING [{fname}]: {exc}")
            failed += 1
    if failed:
        print(f"    {failed} image(s) failed or yielded no detections.")
    return rows


def run_batch(
    section_dir: str | None,
    curv_dir: str | None,
    output_dir: str,
    resolution_mu: float = 4.25,
    resolution_mm: float = 132.0,
    min_diam: float      = 30.0,
    max_diam: float      = 150.0,
    window_size: int     = 50,
    window_unit: str     = "px",
    use_sam2: bool       = False,
    sam2_checkpoint: str = "",
    sam2_cfg: str        = "",
    save_img: bool       = False,
    extended_features: bool  = True,
    extended_curvature: bool = True,
    use_clahe: bool      = False,
    jobs: int            = 1,
) -> pd.DataFrame:
    """Run batch processing for section and/or curvature images.

    Parameters
    ----------
    section_dir         : directory of cross-section images, or None to skip
    curv_dir            : directory of curvature images, or None to skip
    output_dir          : directory where CSVs are written
    resolution_mu       : cross-section resolution in pixels per µm
    resolution_mm       : curvature resolution in pixels/mm
    min_diam / max_diam : diameter filter in µm (section only)
    window_size         : Taubin sliding window in pixels
    window_unit         : 'px' or 'mm'
    use_sam2            : attempt SAM2 segmentation (falls back to watershed)
    sam2_checkpoint     : path to SAM2 .pt weights file
    sam2_cfg            : SAM2 model config yaml
    save_img            : save intermediate images
    extended_features   : compute EFD, Hu moments, radial profile, shape class
    extended_curvature  : compute curl index, wave count, total length
    use_clahe           : CLAHE preprocessing for curvature
    jobs                : parallel jobs (passed to section/curvature if supported)

    Returns
    -------
    per_image_df : one row per source image (empty DataFrame if nothing processed)
    """
    os.makedirs(output_dir, exist_ok=True)
    all_rows: list = []

    # -------------------------------------------------------------------------
    # Cross-section pipeline
    # -------------------------------------------------------------------------
    if section_dir and os.path.isdir(section_dir):
        from ..analysis.section_pipeline import section_seq

        print(f"\n[Section] Processing: {section_dir}")
        paths = collect_images(section_dir)
        print(f"  Found {len(paths)} images")

        def _run_section(img_path: str, **kwargs):
            out_dir = pathlib.Path(output_dir) / "section_output"
            out_dir.mkdir(exist_ok=True)
            df = section_seq(
                img_path,
                str(out_dir),
                resolution=kwargs["resolution_mu"],
                minsize=kwargs["min_diam"],
                maxsize=kwargs["max_diam"],
                save_img=kwargs.get("save_img", False),
                use_sam2=kwargs.get("use_sam2", False),
                sam2_checkpoint=kwargs.get("sam2_checkpoint", ""),
                sam2_cfg=kwargs.get("sam2_cfg", ""),
                extended_features=kwargs.get("extended_features", True),
            )
            return df

        sec_kwargs = {
            "resolution_mu":    resolution_mu,
            "min_diam":         min_diam,
            "max_diam":         max_diam,
            "save_img":         save_img,
            "use_sam2":         use_sam2,
            "sam2_checkpoint":  sam2_checkpoint,
            "sam2_cfg":         sam2_cfg,
            "extended_features": extended_features,
        }
        rows = _process_dir(paths, _run_section, "section", sec_kwargs)
        all_rows.extend(rows)
        print(f"  Processed {len(rows)} images successfully.")

    # -------------------------------------------------------------------------
    # Curvature pipeline
    # -------------------------------------------------------------------------
    if curv_dir and os.path.isdir(curv_dir):
        from ..analysis.curvature_pipeline import curvature_seq

        print(f"\n[Curvature] Processing: {curv_dir}")
        paths = collect_images(curv_dir)
        print(f"  Found {len(paths)} images")

        def _run_curvature(img_path: str, **kwargs):
            out_dir = pathlib.Path(output_dir) / "curvature_output"
            out_dir.mkdir(exist_ok=True)
            df = curvature_seq(
                img_path,
                str(out_dir),
                resolution=kwargs["resolution_mm"],
                window_size=kwargs["window_size"],
                window_unit=kwargs.get("window_unit", "px"),
                save_img=kwargs.get("save_img", False),
                test=False,
                within_element=False,
                use_clahe=kwargs.get("use_clahe", False),
                extended_curvature=kwargs.get("extended_curvature", True),
            )
            return df

        curv_kwargs = {
            "resolution_mm":      resolution_mm,
            "window_size":        window_size,
            "window_unit":        window_unit,
            "save_img":           save_img,
            "use_clahe":          use_clahe,
            "extended_curvature": extended_curvature,
        }
        rows = _process_dir(paths, _run_curvature, "curvature", curv_kwargs)
        all_rows.extend(rows)
        print(f"  Processed {len(rows)} images successfully.")

    if not all_rows:
        print("\nNo results produced. Check input paths and image formats.")
        return pd.DataFrame()

    per_image = pd.DataFrame(all_rows)

    # Identifier columns first. The source filename is recorded as-is; any
    # grouping (within/between individual) is left to downstream analysis.
    meta_cols    = ["source_file", "image_type", "segmentation_method"]
    present_meta = [c for c in meta_cols if c in per_image.columns]
    other_cols   = [c for c in per_image.columns if c not in present_meta]
    per_image    = per_image[present_meta + other_cols]

    per_image_path = os.path.join(output_dir, "hair_analysis_per_image.csv")
    per_image.to_csv(per_image_path, index=False)
    print(f"\nPer-image CSV  → {per_image_path}  ({len(per_image)} rows)")

    return per_image
