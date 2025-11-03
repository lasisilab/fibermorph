"""Geometric calculation functions for fibermorph package."""

from typing import List, Tuple
import logging

import numpy as np
from scipy import ndimage

logger = logging.getLogger(__name__)


def define_structure(structure: str) -> List[np.ndarray]:
    """Define structure elements for hit-and-miss algorithm.

    Parameters
    ----------
    structure : str
        Type of structure to define ('mid' or 'diag').

    Returns
    -------
    List[np.ndarray]
        List of structure elements.

    Raises
    ------
    TypeError
        If structure type is not 'mid' or 'diag'.
    """
    if structure == "mid":
        hit1 = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 0]], dtype=np.uint8)
        hit2 = np.array([[1, 0, 0], [0, 1, 1], [0, 0, 0]], dtype=np.uint8)
        hit3 = np.array([[0, 0, 1], [1, 1, 0], [0, 0, 0]], dtype=np.uint8)
        hit4 = np.array([[0, 0, 0], [1, 1, 0], [0, 0, 1]], dtype=np.uint8)
        hit5 = np.array([[0, 1, 0], [0, 1, 0], [1, 0, 0]], dtype=np.uint8)
        hit6 = np.array([[0, 1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.uint8)
        hit7 = np.array([[1, 0, 0], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)
        hit8 = np.array([[0, 0, 1], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)

        mid_list = [hit1, hit2, hit3, hit4, hit5, hit6, hit7, hit8]
        return mid_list
    elif structure == "diag":
        hit1 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], dtype=np.uint8)
        hit2 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.uint8)
        diag_list = [hit1, hit2]

        return diag_list
    else:
        raise TypeError(
            "Structure input for find_structure() is invalid, "
            "choose from 'mid', or 'diag' and input as str"
        )


def find_structure(skeleton: np.ndarray, structure: str) -> Tuple[np.ndarray, int]:
    """Find specific structure elements in skeleton using hit-and-miss algorithm.

    Parameters
    ----------
    skeleton : np.ndarray
        Skeleton image array.
    structure : str
        Type of structure to find ('mid' or 'diag').

    Returns
    -------
    labels : np.ndarray
        Labeled image of found structures.
    num_labels : int
        Number of structures found.
    """
    from ..processing.binary import check_bin
    
    skel_image = check_bin(skeleton).astype(int)

    # creating empty array for hit and miss algorithm
    hit_points = np.zeros(skel_image.shape)
    # defining the structure used in hit-and-miss algorithm
    hit_list = define_structure(structure)

    for hit in hit_list:
        target = hit.sum()
        curr = ndimage.convolve(skel_image, hit, mode="constant")
        hit_points = np.logical_or(hit_points, np.where(curr == target, 1, 0))

    # Ensuring target image is binary
    hit_points_image = np.where(hit_points, 1, 0)

    # use SciPy's ndimage module for locating and determining coordinates of each structure
    labels, num_labels = ndimage.label(hit_points_image)

    return labels, num_labels


def pixel_length_correction(element) -> float:
    """Calculate corrected pixel length accounting for diagonal and mid-point pixels.

    Parameters
    ----------
    element : skimage.measure._regionprops._RegionProperties
        Region properties object from skimage.

    Returns
    -------
    float
        Corrected element pixel length.
    """
    num_total_points = element.area
    skeleton = element.image

    diag_points, num_diag_points = find_structure(skeleton, "diag")
    mid_points, num_mid_points = find_structure(skeleton, "mid")

    num_adj_points = num_total_points - num_diag_points - num_mid_points

    corr_element_pixel_length = (
        num_adj_points
        + (num_diag_points * np.sqrt(2))
        + (num_mid_points * np.sqrt(1.25))
    )

    return corr_element_pixel_length
