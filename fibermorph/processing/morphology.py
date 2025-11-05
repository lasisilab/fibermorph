"""Morphological operations for fibermorph package."""

import pathlib
from typing import Union, Tuple
import logging

import numpy as np
import skimage
import skimage.morphology
import skimage.util
from PIL import Image
from scipy import ndimage

logger = logging.getLogger(__name__)


def skeletonize(
    clean_img: np.ndarray, 
    name: str, 
    output_path: Union[str, pathlib.Path], 
    save_img: bool
) -> np.ndarray:
    """Reduces curves and lines to 1 pixel width (skeletons).

    Parameters
    ----------
    clean_img : np.ndarray
        Binary array.
    name : str
        Image name.
    output_path : str or pathlib.Path
        Output directory path.
    save_img : bool
        True or false for saving image.

    Returns
    -------
    np.ndarray
        Boolean array of skeletonized image.
    """
    from ..processing.binary import check_bin
    from ..utils.filesystem import make_subdirectory
    
    # check if image is binary and properly inverted
    clean_img = check_bin(clean_img)

    # skeletonize the hair
    skeleton = skimage.morphology.thin(clean_img)

    if save_img:
        output_path = make_subdirectory(output_path, append_name="skeletonized")
        img_inv = skimage.util.invert(skeleton)
        save_path = pathlib.Path(output_path) / f"{name}.tiff"
        im = Image.fromarray(img_inv)
        im.save(save_path)
        logger.debug(f"Saved skeletonized image to {save_path}")

    return skeleton


def prune(
    skeleton: np.ndarray, 
    name: str, 
    pruned_dir: Union[str, pathlib.Path], 
    save_img: bool
) -> np.ndarray:
    """Prunes branches from skeletonized image.
    
    Adapted from: http://homepages.inf.ed.ac.uk/rbf/HIPR2/thin.htm

    Parameters
    ----------
    skeleton : np.ndarray
        Boolean array.
    name : str
        Image name.
    pruned_dir : str or pathlib.Path
        Output directory path.
    save_img : bool
        True or false for saving image.

    Returns
    -------
    np.ndarray
        Boolean array of pruned skeleton image.
    """
    from ..processing.binary import check_bin, remove_particles
    
    logger.debug(f"Pruning {name}...")

    # identify 3-way branch-points
    hit1 = np.array([[0, 1, 0], [0, 1, 0], [1, 0, 1]], dtype=np.uint8)
    hit2 = np.array([[1, 0, 0], [0, 1, 0], [1, 0, 1]], dtype=np.uint8)
    hit3 = np.array([[1, 0, 0], [0, 1, 1], [0, 1, 0]], dtype=np.uint8)
    hit_list = [hit1, hit2, hit3]

    # numpy slicing to create 3 remaining rotations
    for ii in range(9):
        hit_list.append(np.transpose(hit_list[-3])[::-1, ...])

    # add structure elements for branch-points four 4-way branchpoints
    hit3 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    hit4 = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.uint8)
    hit_list.append(hit3)
    hit_list.append(hit4)

    skel_image = check_bin(skeleton)
    branch_points = np.zeros(skel_image.shape)

    for hit in hit_list:
        target = hit.sum()
        curr = ndimage.convolve(skel_image, hit, mode="constant")
        branch_points = np.logical_or(branch_points, np.where(curr == target, 1, 0))

    # pixels may "hit" multiple structure elements, ensure the output is a binary image
    branch_points_image = np.where(branch_points, 1, 0)

    # use SciPy's ndimage module for locating and determining coordinates of each branch-point
    labels, num_labels = ndimage.label(branch_points_image)

    # use SciPy's ndimage module to determine the coordinates/pixel corresponding to the
    # center of mass of each branchpoint
    branch_points = ndimage.center_of_mass(
        skel_image, labels=labels, index=range(1, num_labels + 1)
    )
    branch_points = np.array(
        [
            value
            for value in branch_points
            if not np.isnan(value[0]) or not np.isnan(value[1])
        ],
        dtype=int,
    )

    hit = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.uint8)

    dilated_branches = ndimage.convolve(branch_points_image, hit, mode="constant")
    dilated_branches_image = np.where(dilated_branches, 1, 0)
    pruned_image = np.subtract(skel_image, dilated_branches_image)

    pruned_image = remove_particles(
        pruned_image, pruned_dir, name, minpixel=5, prune=True, save_img=save_img
    )

    return pruned_image


def diag(skeleton: np.ndarray) -> Tuple[int, int, int]:
    """Analyzes diagonal, middle, and adjacent points in skeleton.
    
    Adapted from: http://homepages.inf.ed.ac.uk/rbf/HIPR2/thin.htm

    Parameters
    ----------
    skeleton : np.ndarray
        Boolean array.

    Returns
    -------
    Tuple[int, int, int]
        Number of diagonal points, middle points, and adjacent points.
    """
    from ..processing.binary import check_bin
    
    # identify diagonals
    hit1 = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 0]], dtype=np.uint8)
    hit2 = np.array([[1, 0, 0], [0, 1, 1], [0, 0, 0]], dtype=np.uint8)
    hit3 = np.array([[0, 0, 1], [1, 1, 0], [0, 0, 0]], dtype=np.uint8)
    hit4 = np.array([[0, 0, 0], [1, 1, 0], [0, 0, 1]], dtype=np.uint8)
    hit5 = np.array([[0, 1, 0], [0, 1, 0], [1, 0, 0]], dtype=np.uint8)
    hit6 = np.array([[0, 1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.uint8)
    hit7 = np.array([[1, 0, 0], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)
    hit8 = np.array([[0, 0, 1], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)

    mid_list = [hit1, hit2, hit3, hit4, hit5, hit6, hit7, hit8]

    hit9 = np.array([[0, 0, 1], [0, 1, 0], [1, 0, 0]], dtype=np.uint8)
    hit10 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.uint8)

    diag_list = [hit9, hit10]

    hit11 = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], dtype=np.uint8)
    hit12 = np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0]], dtype=np.uint8)

    adj_list = [hit11, hit12]

    skel_image = check_bin(skeleton).astype(int)

    diag_points = np.zeros(skel_image.shape)
    mid_points = np.zeros(skel_image.shape)
    adj_points = np.zeros(skel_image.shape)

    for hit in diag_list:
        target = hit.sum()
        curr = ndimage.convolve(skel_image, hit, mode="constant")
        diag_points = np.logical_or(diag_points, np.where(curr == target, 1, 0))

    for hit in mid_list:
        target = hit.sum()
        curr = ndimage.convolve(skel_image, hit, mode="constant")
        mid_points = np.logical_or(mid_points, np.where(curr == target, 1, 0))

    for hit in adj_list:
        target = hit.sum()
        curr = ndimage.convolve(skel_image, hit, mode="constant")
        adj_points = np.logical_or(adj_points, np.where(curr == target, 1, 0))

    # pixels may "hit" multiple structure elements, ensure the output is a binary image
    diag_points_image = np.where(diag_points, 1, 0)
    mid_points_image = np.where(mid_points, 1, 0)
    adj_points_image = np.where(adj_points, 1, 0)

    # use SciPy's ndimage module for locating and determining coordinates of each point
    labels, num_labels = ndimage.label(diag_points_image)
    labels2, num_labels2 = ndimage.label(mid_points_image)
    labels3, num_labels3 = ndimage.label(adj_points_image)

    # use SciPy's ndimage module to determine the coordinates/pixel corresponding to the
    # center of mass of each point
    diag_points = ndimage.center_of_mass(
        skel_image, labels=labels, index=range(1, num_labels + 1)
    )
    mid_points = ndimage.center_of_mass(
        skel_image, labels=labels2, index=range(1, num_labels2 + 1)
    )
    adj_points = ndimage.center_of_mass(
        skel_image, labels=labels3, index=range(1, num_labels3 + 1)
    )

    diag_points = np.array(
        [
            value
            for value in diag_points
            if not np.isnan(value[0]) or not np.isnan(value[1])
        ],
        dtype=int,
    )
    mid_points = np.array(
        [
            value
            for value in mid_points
            if not np.isnan(value[0]) or not np.isnan(value[1])
        ],
        dtype=int,
    )
    adj_points = np.array(
        [
            value
            for value in adj_points
            if not np.isnan(value[0]) or not np.isnan(value[1])
        ],
        dtype=int,
    )

    num_diag_points = len(diag_points)
    num_mid_points = len(mid_points)
    num_adj_points = len(adj_points)

    return num_diag_points, num_mid_points, num_adj_points
