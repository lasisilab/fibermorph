"""Binary image processing operations for fibermorph package."""

import pathlib
from typing import Union
import logging

import numpy as np
import scipy
import skimage
import skimage.exposure
import skimage.morphology
import skimage.segmentation
import skimage.util
from PIL import Image
from skimage import filters
from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)


def check_bin(img: np.ndarray) -> np.ndarray:
    """Checks whether image has been properly binarized.
    
    Works on the assumption that there should be more background pixels than element pixels.

    Parameters
    ----------
    img : np.ndarray
        Binary image array.

    Returns
    -------
    np.ndarray
        A binary array of the image with correct orientation.
    """
    img_bool = np.asarray(img, dtype=bool)

    # Gets the unique values in the image matrix. Since it is binary, there should only be 2.
    unique, counts = np.unique(img_bool, return_counts=True)
    
    # If the length of unique is not 2 then log that the image isn't a binary.
    if len(unique) != 2:
        hair_pixels = len(counts)
        logger.warning(
            f"Image is not binarized! There is/are {hair_pixels} value(s) present, "
            "but there should be 2!"
        )
    
    # If it is binarized, check the orientation
    if counts[0] < counts[1]:
        logger.debug("Image orientation corrected")
        img = skimage.util.invert(img_bool)
        return img
    else:
        logger.debug("Image orientation is correct")
        img = img_bool
        return img


def binarize_curv(
    filter_img: np.ndarray, 
    im_name: str, 
    output_path: Union[str, pathlib.Path], 
    save_img: bool
) -> np.ndarray:
    """Binarizes the filtered output of the filter_curv function.

    Parameters
    ----------
    filter_img : np.ndarray
        Image after ridge filter (float64).
    im_name : str
        Image name.
    output_path : str or pathlib.Path
        Output directory path.
    save_img : bool
        True or false for saving image.

    Returns
    -------
    np.ndarray
        An array with the binarized image.
    """
    from ..utils.filesystem import make_subdirectory
    
    selem = skimage.morphology.disk(5)
    filter_img = skimage.exposure.adjust_log(filter_img)

    try:
        thresh_im = filter_img > filters.threshold_otsu(filter_img)
    except Exception as e:
        logger.warning(f"Otsu thresholding failed, using image inversion: {e}")
        thresh_im = skimage.util.invert(filter_img)

    # clear the border of the image (buffer is the px width to be considered as border)
    cleared_im = skimage.segmentation.clear_border(thresh_im, buffer_size=10)

    # dilate the hair fibers
    binary_im = scipy.ndimage.binary_dilation(cleared_im, structure=selem, iterations=2)

    if save_img:
        output_path = make_subdirectory(output_path, append_name="binarized")
        # invert image
        save_im = skimage.util.invert(binary_im)

        # save image
        save_name = pathlib.Path(output_path) / f"{im_name}.tiff"
        im = Image.fromarray(save_im)
        im.save(save_name)
        logger.debug(f"Saved binarized image to {save_name}")

    return binary_im


def remove_particles(
    img: np.ndarray,
    output_path: Union[str, pathlib.Path],
    name: str,
    minpixel: int,
    prune: bool,
    save_img: bool
) -> np.ndarray:
    """Removes particles under a particular size in the images.

    Parameters
    ----------
    img : np.ndarray
        Binary image to be cleaned.
    output_path : str or pathlib.Path
        A path to the output directory.
    name : str
        Input image name.
    minpixel : int
        Minimum pixel size below which elements should be removed.
    prune : bool
        True or false for whether the input is a pruned skeleton.
    save_img : bool
        True or false for saving image.

    Returns
    -------
    np.ndarray
        An array with the noise particles removed.
    """
    from ..utils.filesystem import make_subdirectory
    
    img_bool = np.asarray(img, dtype=bool)
    img = check_bin(img_bool)

    minimum = minpixel
    clean = skimage.morphology.remove_small_objects(
        img, connectivity=2, min_size=minimum
    )

    if save_img:
        img_inv = skimage.util.invert(clean)
        if prune:
            output_path = make_subdirectory(output_path, append_name="pruned")
        else:
            output_path = make_subdirectory(output_path, append_name="clean")
        savename = pathlib.Path(output_path) / f"{name}.tiff"
        plt.imsave(savename, img_inv, cmap="gray")
        logger.debug(f"Saved cleaned image to {savename}")

    return clean
