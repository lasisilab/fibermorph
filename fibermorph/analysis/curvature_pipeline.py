"""Curvature analysis pipeline for fibermorph package."""

import pathlib
from typing import Union, List
import logging

import pandas as pd
from tqdm import tqdm

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
) -> pd.DataFrame:
    """Sequence of functions to be executed for calculating curvature in fibermorph.

    Parameters
    ----------
    input_file : str or pathlib.Path
        Path to image that needs to be analyzed.
    output_path : str or pathlib.Path
        Output directory.
    resolution : float
        Number of pixels per mm in original image.
    window_size : float or int or list
        Desired size for window of measurement in mm.
    window_unit : str
        Unit for window size ('px' or 'mm').
    save_img : bool
        True or false for saving images.
    test : bool
        True or false for whether this is being run for validation tests.
    within_element : bool
        True or False for whether to save spreadsheets with within element curvature values.

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame with curvature summary data for all images.
    """
    from ..core.filters import filter_curv
    from ..processing.binary import binarize_curv, remove_particles
    from ..processing.morphology import skeletonize, prune
    from ..core.curvature import analyze_all_curv

    with tqdm(
        total=6,
        desc="curvature analysis sequence",
        unit="steps",
        position=1,
        leave=None,
    ) as pbar:
        # filter
        filter_img, im_name = filter_curv(input_file, output_path, save_img)
        pbar.update(1)

        # binarize
        binary_img = binarize_curv(filter_img, im_name, output_path, save_img)
        pbar.update(1)

        # remove particles
        clean_im = remove_particles(
            binary_img,
            output_path,
            im_name,
            minpixel=int(resolution / 2),
            prune=False,
            save_img=save_img,
        )
        pbar.update(1)

        # skeletonize
        skeleton_im = skeletonize(clean_im, im_name, output_path, save_img)
        pbar.update(1)

        # prune
        pruned_im = prune(skeleton_im, im_name, output_path, save_img)
        pbar.update(1)

        # analyze
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
        pbar.update(1)

        return im_df
