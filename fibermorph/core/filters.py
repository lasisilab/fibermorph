"""Image filtering functions for fibermorph package."""

import pathlib
from typing import Tuple, Union
import logging

import numpy as np
import skimage
import skimage.filters
import skimage.util
from matplotlib import pyplot as plt

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
        save_path = pathlib.Path(output_path) / f"{im_name}.tiff"
        plt.imsave(save_path, img_inv, cmap="gray")
        logger.debug(f"Saved filtered image to {save_path}")

    return filter_img, im_name
