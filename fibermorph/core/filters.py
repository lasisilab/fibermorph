"""Image filtering functions for fibermorph package."""

import pathlib
from typing import Tuple, Union
import logging

import numpy as np
import skimage
import skimage.filters
import skimage.io
import skimage.util

logger = logging.getLogger(__name__)


def filter_curv(
    input_file: Union[str, pathlib.Path], 
    output_path: Union[str, pathlib.Path], 
    save_img: bool
) -> Tuple[np.ndarray, str]:
    """Uses a ridge filter to extract curved (or straight) lines from background noise.

    Parameters
    ----------
    input_file : str or pathlib.Path
        A string path to the input image.
    output_path : str or pathlib.Path
        A string path to the output directory.
    save_img : bool
        True or False for saving filtered image.

    Returns
    -------
    filter_img : np.ndarray
        The filtered image.
    im_name : str
        A string with the image name.
    """
    from ..io.readers import imread
    from ..utils.filesystem import make_subdirectory
    
    # create pathlib object for input Image
    input_path = pathlib.Path(input_file)

    gray_img, im_name = imread(input_path)

    # use frangi ridge filter to find hairs, the output will be inverted
    filter_img = skimage.filters.frangi(gray_img)
    logger.debug(f"Filtered image size: {filter_img.shape}")

    if save_img:
        output_path = make_subdirectory(output_path, append_name="filtered")
        # inverting and saving the filtered image
        img_inv = skimage.util.invert(filter_img)
        img_uint8 = skimage.util.img_as_ubyte(np.clip(img_inv, 0, 1))
        save_path = pathlib.Path(output_path) / f"{im_name}.tiff"
        skimage.io.imsave(save_path, img_uint8)
        logger.debug(f"Saved filtered image to {save_path}")

    return filter_img, im_name


def filter_curv_clahe(
    input_file: Union[str, pathlib.Path],
    output_path: Union[str, pathlib.Path],
    save_img: bool,
) -> Tuple[np.ndarray, str]:
    """CLAHE-enhanced ridge filter for curvature analysis.

    Applies CLAHE contrast enhancement before Frangi filtering and uses a
    masked-ROI Otsu threshold that excludes bright bands at the top/bottom
    15% of the frame (common artefact in microscopy strip images).

    Parameters
    ----------
    input_file  : path to the input grayscale image
    output_path : directory for optional saved output
    save_img    : whether to save the preprocessed binary image

    Returns
    -------
    (binary_img, im_name) — uint8 binary (0/255), image stem name
    """
    import cv2
    from ..io.readers import imread
    from ..utils.filesystem import make_subdirectory

    input_path = pathlib.Path(input_file)
    gray_img, im_name = imread(input_path)

    # CLAHE enhancement
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_img)

    # Frangi ridge filter
    ridges   = skimage.filters.frangi(enhanced.astype(np.float64) / 255.0,
                                       sigmas=range(1, 4), black_ridges=False)
    ridges_u8 = (ridges * 255).astype(np.uint8)

    # Masked Otsu — exclude top/bottom 15% artefact bands
    h   = ridges_u8.shape[0]
    roi = ridges_u8[int(0.15 * h): int(0.85 * h), :]
    _, binary_roi = cv2.threshold(roi, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = np.zeros_like(ridges_u8)
    binary[int(0.15 * h): int(0.85 * h), :] = binary_roi

    if save_img:
        out_dir  = make_subdirectory(output_path, append_name="filtered_clahe")
        save_path = pathlib.Path(out_dir) / f"{im_name}.tiff"
        skimage.io.imsave(str(save_path), binary)
        logger.debug(f"Saved CLAHE binary to {save_path}")

    return binary, im_name
