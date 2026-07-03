"""Curvature analysis pipeline for fibermorph package."""

from __future__ import annotations

import pathlib
from typing import Union, List
import logging

import numpy as np
import pandas as pd
from tqdm import tqdm
from PIL import UnidentifiedImageError

logger = logging.getLogger(__name__)


def curvature_seq(
    input_file: Union[str, pathlib.Path],
    output_path: Union[str, pathlib.Path],
    resolution: float,
    window_size: Union[float, int, List],
    window_unit: str,
    save_img: bool,
    test: bool,
    within_element: bool,
    use_clahe: bool       = False,
    extended_curvature: bool = False,
) -> pd.DataFrame:
    """Sequence of steps to calculate curvature for a single image.

    Parameters
    ----------
    input_file          : path to the input image
    output_path         : output directory
    resolution          : pixels per mm
    window_size         : window size for Taubin fit (scalar or list for sweep)
    window_unit         : 'px' or 'mm'
    save_img            : save intermediate images
    test                : running under test suite (skips some I/O)
    within_element      : save per-hair curvature CSV distributions
    use_clahe           : CLAHE preprocessing (improved contrast handling)
    extended_curvature  : compute curl_index, wave_count, diameter, std, CV, IQR

    Returns
    -------
    pd.DataFrame — curvature summary (one row per image / window size)
    """
    from ..core.filters import filter_curv, filter_curv_clahe
    from ..processing.binary import binarize_curv, remove_particles
    from ..processing.morphology import skeletonize, prune
    from ..core.curvature import (analyze_all_curv,
                                   curl_index_from_skeleton,
                                   wave_count as wave_count_fn)

    try:
        with tqdm(
            total=6,
            desc="curvature analysis sequence",
            unit="steps",
            position=1,
            leave=None,
        ) as pbar:
            # ----------------------------------------------------------------
            # Step 1 — Filter
            # ----------------------------------------------------------------
            if use_clahe:
                filter_img, im_name = filter_curv_clahe(input_file, output_path, save_img)
                # filter_curv_clahe returns uint8 binary; wrap to float for downstream compat
                filter_img = filter_img.astype(np.float64) / 255.0
            else:
                filter_img, im_name = filter_curv(input_file, output_path, save_img)
            pbar.update(1)

            # ----------------------------------------------------------------
            # Step 2 — Binarize
            # ----------------------------------------------------------------
            binary_img = binarize_curv(filter_img, im_name, output_path, save_img)
            pbar.update(1)

            # ----------------------------------------------------------------
            # Step 3 — Remove particles
            # ----------------------------------------------------------------
            clean_im = remove_particles(
                binary_img,
                output_path,
                im_name,
                minpixel=int(resolution / 2),
                prune=False,
                save_img=save_img,
            )
            pbar.update(1)

            # ----------------------------------------------------------------
            # Step 4 — Skeletonize
            # ----------------------------------------------------------------
            if extended_curvature:
                # Medial-axis skeleton also returns a distance map for diameter stats
                from skimage.morphology import medial_axis
                skel_bool, dist_map = medial_axis(clean_im > 0, return_distance=True)
                skeleton_im = (skel_bool * 255).astype(np.uint8)
            else:
                skeleton_im = skeletonize(clean_im, im_name, output_path, save_img)
                dist_map    = None
            pbar.update(1)

            # ----------------------------------------------------------------
            # Step 5 — Prune
            # ----------------------------------------------------------------
            pruned_im = prune(skeleton_im, im_name, output_path, save_img)
            pbar.update(1)

            # ----------------------------------------------------------------
            # Step 6 — Analyze curvature
            # ----------------------------------------------------------------
            im_df = analyze_all_curv(
                pruned_im,
                im_name,
                output_path,
                resolution,
                window_size,
                window_unit,
                test,
                within_element,
            )

            if extended_curvature and im_df is not None and not im_df.empty:
                pruned_bool = pruned_im > 0

                # Curl index
                curl_mean, curl_std, len_vals = curl_index_from_skeleton(
                    pruned_bool, resolution
                )
                im_df["curl_index"]     = curl_mean
                im_df["curl_index_std"] = curl_std

                # Wave count from all per-element curvature values
                # (approximate: use curv_mean_mean as a single representative value
                #  since we don't retain per-window traces here)
                if "curv_mean_mean" in im_df.columns:
                    curv_vals = im_df["curv_mean_mean"].dropna().values
                else:
                    curv_vals = np.array([])
                wc = int(wave_count_fn(curv_vals)) if len(curv_vals) > 0 else 0
                im_df["wave_count"] = wc
                total_length_mm = float(sum(len_vals)) if len_vals else float("nan")
                im_df["wave_count_per_mm"] = (
                    wc / (total_length_mm + 1e-10) if not np.isnan(total_length_mm) else float("nan")
                )
                im_df["length_total"] = total_length_mm

                # Fiber diameter from medial-axis distance map
                if dist_map is not None:
                    rows, cols = np.where(pruned_bool)
                    if len(rows) > 0:
                        resolution_mu = 1000.0 / resolution
                        diam = 2.0 * dist_map[rows, cols] / resolution_mu
                        im_df["diameter_mean_mu"] = float(np.mean(diam))
                        mean_d = float(np.mean(diam))
                        im_df["diameter_cv"] = float(np.std(diam) / (mean_d + 1e-10))

            pbar.update(1)
            return im_df

    except UnidentifiedImageError as e:
        logger.error(f"Cannot process image file {input_file}: {e}")
        raise
    except FileNotFoundError as e:
        logger.error(f"Image file not found: {input_file}")
        raise
    except Exception as e:
        logger.error(f"Error processing image {input_file}: {e}")
        raise
