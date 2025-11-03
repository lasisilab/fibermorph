"""Section analysis pipeline for fibermorph package."""

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
    save_img: bool
) -> pd.DataFrame:
    """Segments the input image to isolate the section(s).

    Parameters
    ----------
    input_file : str or pathlib.Path
        Path to input image file.
    output_path : str or pathlib.Path
        Output directory path.
    resolution : float
        Number of pixels per micron.
    minsize : float
        Minimum diameter in microns for sections.
    maxsize : float
        Maximum diameter in microns for sections.
    save_img : bool
        Whether to save intermediate images.

    Returns
    -------
    pd.DataFrame
        DataFrame with section measurements.
    """
    from ..io.readers import imread
    from ..core.section import section_props, crop_section, segment_section, save_sections

    with tqdm(
        total=3, desc="section analysis sequence", unit="steps", position=1, leave=None
    ) as pbar:
        section_data = pd.DataFrame()

        try:
            # read in file
            img, im_name = imread(input_file, use_skimage=True)

            # Gets the unique values in the image matrix. Since it is binary, there should only be 2.
            unique, counts = np.unique(img, return_counts=True)

            # find center of image
            im_center = list(np.divide(img.shape, 2))  # returns array of two floats

            minpixel = minsize * resolution
            maxpixel = maxsize * resolution

            pbar.update(1)

            if len(unique) == 2:
                seg_im = skimage.util.invert(img)
                pbar.update(1)
                label_im, num_elem = skimage.measure.label(
                    seg_im, connectivity=2, return_num=True
                )

                props = skimage.measure.regionprops(
                    label_image=label_im, intensity_image=img
                )

                section_data, bin_im, bbox = section_props(
                    props, im_name, resolution, minpixel, maxpixel, im_center
                )

                pad = 100
                minr = bbox[0] - pad
                minc = bbox[1] - pad
                maxr = bbox[2] + pad
                maxc = bbox[3] + pad
                bbox_pad = [minc, minr, maxc, maxr]
                crop_im = Image.fromarray(img).crop(bbox_pad)

                if save_img:
                    save_sections(output_path, im_name, crop_im, save_crop=True)
                    save_sections(output_path, im_name, bin_im, save_crop=False)

                pbar.update(1)
            else:
                crop_im = crop_section(
                    img, im_name, resolution, minpixel, maxpixel, im_center
                )
                pbar.update(1)

                section_data, bin_im = segment_section(
                    crop_im, im_name, resolution, minpixel, maxpixel, im_center
                )

                if save_img:
                    save_sections(output_path, im_name, crop_im, save_crop=True)
                    save_sections(output_path, im_name, bin_im, save_crop=False)
                pbar.update(1)
        except Exception as e:
            logger.error(f"Error processing {input_file}: {e}")

        return section_data
