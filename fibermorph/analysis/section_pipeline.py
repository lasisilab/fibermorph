"""Section analysis pipeline for fibermorph package."""

from __future__ import annotations

import pathlib
from typing import Union
import logging

import numpy as np
import pandas as pd
import skimage
import skimage.measure
import skimage.util
from PIL import Image
from tqdm import tqdm

logger = logging.getLogger(__name__)


def section_seq(
    input_file: Union[str, pathlib.Path],
    output_path: Union[str, pathlib.Path],
    resolution: float,
    minsize: float,
    maxsize: float,
    save_img: bool,
    use_sam2: bool       = False,
    sam2_checkpoint: str = "",
    sam2_cfg: str        = "",
    extended_features: bool = False,
) -> pd.DataFrame:
    """Segment the input image to isolate the cross-section and extract measurements.

    Parameters
    ----------
    input_file        : path to input image file
    output_path       : output directory
    resolution        : pixels per µm
    minsize           : minimum diameter in µm
    maxsize           : maximum diameter in µm
    save_img          : save intermediate images
    use_sam2          : use SAM2 GPU segmentation (falls back to watershed)
    sam2_checkpoint   : path to SAM2 model checkpoint
    sam2_cfg          : SAM2 model config YAML path
    extended_features : add EFD, Hu moments, radial profile, and shape class columns

    Returns
    -------
    pd.DataFrame — section measurements (one row per image)
    """
    from ..io.readers import imread
    from ..core.section import section_props, crop_section, segment_section, save_sections
    from ..processing.section_sam2 import segment_section as sam2_segment_fn

    with tqdm(
        total=3, desc="section analysis sequence", unit="steps", position=1, leave=None
    ) as pbar:
        section_data = pd.DataFrame()

        try:
            img, im_name = imread(input_file, use_skimage=True)
            unique, _ = np.unique(img, return_counts=True)
            im_center = list(np.divide(img.shape, 2))
            minpixel  = minsize * resolution
            maxpixel  = maxsize * resolution
            pbar.update(1)

            # ----------------------------------------------------------------
            # Segmentation
            # ----------------------------------------------------------------
            if use_sam2 or extended_features:
                # New path: SAM2 / watershed via section_sam2.py
                sam2_ckpt = sam2_checkpoint or ""
                sam2_c    = sam2_cfg or ""
                seg_result = sam2_segment_fn(
                    img,
                    resolution_mu=resolution,
                    min_diam=minsize,
                    max_diam=maxsize,
                    use_sam2=use_sam2,
                    checkpoint=sam2_ckpt,
                    model_cfg=sam2_c,
                )
                pbar.update(1)

                if seg_result is None:
                    logger.warning(f"No section candidate found in {input_file}")
                    return pd.DataFrame()

                mask_uint8, confidence, method = seg_result

                if extended_features:
                    from ..core.section import section_props_extended
                    section_data = section_props_extended(mask_uint8, im_name, resolution)
                    section_data["segmentation_method"] = method
                    section_data["confidence"]          = confidence
                else:
                    # Basic metrics only, using the new segmentation
                    labeled  = skimage.measure.label(mask_uint8 > 0, connectivity=2)
                    props    = skimage.measure.regionprops(labeled, intensity_image=img)
                    if props:
                        p = props[0]
                        area_mu   = p.filled_area / (resolution ** 2)
                        min_diam  = p.minor_axis_length / resolution
                        max_diam  = p.major_axis_length / resolution
                        section_data = pd.DataFrame({
                            "ID":           [im_name],
                            "area":         [area_mu],
                            "eccentricity": [p.eccentricity],
                            "min":          [min_diam],
                            "max":          [max_diam],
                            "segmentation_method": [method],
                        })

                if save_img:
                    save_sections(output_path, im_name,
                                  Image.fromarray(mask_uint8), save_crop=True)
                pbar.update(1)

            else:
                # Original path: Otsu → crop → morphological active contours
                if len(unique) == 2:
                    seg_im = skimage.util.invert(img)
                    pbar.update(1)
                    label_im, _ = skimage.measure.label(seg_im, connectivity=2, return_num=True)
                    props = skimage.measure.regionprops(label_image=label_im,
                                                        intensity_image=img)
                    section_data, bin_im, bbox = section_props(
                        props, im_name, resolution, minpixel, maxpixel, im_center
                    )
                    pad = 100
                    crop_im = Image.fromarray(img).crop(
                        [bbox[1] - pad, bbox[0] - pad, bbox[3] + pad, bbox[2] + pad]
                    )
                    if save_img:
                        save_sections(output_path, im_name, crop_im, save_crop=True)
                        save_sections(output_path, im_name, bin_im, save_crop=False)
                    pbar.update(1)
                else:
                    crop_im = crop_section(img, im_name, resolution, minpixel, maxpixel, im_center)
                    pbar.update(1)
                    section_data, bin_im = segment_section(
                        crop_im, im_name, resolution, minpixel, maxpixel, im_center
                    )
                    if save_img:
                        save_sections(output_path, im_name, crop_im, save_crop=True)
                        save_sections(output_path, im_name, bin_im, save_crop=False)
                    pbar.update(1)

        except Exception as exc:
            logger.error(f"Error processing {input_file}: {exc}")

        return section_data
