"""Curvature analysis functions for fibermorph package."""

import pathlib
import warnings
from typing import Optional, List, Union, Any, Generator
import logging

import numpy as np
import pandas as pd
import skimage
import skimage.measure

logger = logging.getLogger(__name__)


def taubin_curv(coords: np.ndarray, resolution: float) -> float:
    """Curvature calculation based on algebraic circle fit by Taubin.
    
    Adapted from: https://github.com/PmagPy/PmagPy/
    G. Taubin, "Estimation Of Planar Curves, Surfaces And Nonplanar
                Space Curves Defined By Implicit Equations, With
                Applications To Edge And Range Image Segmentation",
    IEEE Trans. PAMI, Vol. 13, pages 1115-1138, (1991)

    Parameters
    ----------
    coords : np.ndarray
        Array of paired x and y coordinates for each point of the line where a curve needs 
        to be fitted. [[x_1, y_1], [x_2, y_2], ....]
    resolution : float
        Number of pixels per mm in original image.

    Returns
    -------
    float
        If the radius of the fitted circle is finite, returns the curvature (1/radius).
        If the radius is infinite, returns 0.
    """
    warnings.filterwarnings("ignore")  # suppress RuntimeWarnings from dividing by zero
    xy = np.array(coords)
    x = xy[:, 0] - np.mean(xy[:, 0])  # norming points by x avg
    y = xy[:, 1] - np.mean(xy[:, 1])  # norming points by y avg
    z = x * x + y * y
    zmean = np.mean(z)
    z0 = (z - zmean) / (2.0 * np.sqrt(zmean))
    zxy = np.array([z0, x, y]).T
    u, s, v = np.linalg.svd(zxy, full_matrices=False)
    v = v.transpose()
    a = v[:, 2]
    a[0] = (a[0]) / (2.0 * np.sqrt(zmean))
    a = np.concatenate([a, [(-1.0 * zmean * a[0])]], axis=0)
    r = np.sqrt(a[1] * a[1] + a[2] * a[2] - 4 * a[0] * a[3]) / abs(a[0]) / 2

    if np.isfinite(r):
        curv = 1 / (r / resolution)
        if curv >= 0.00001:
            return curv
        else:
            return 0
    else:
        return 0


def subset_gen(
    pixel_length: int, window_size_px: int, label: np.ndarray
) -> Generator[np.ndarray, None, None]:
    """Generator function for start and end indices of the window of measurement.

    Parameters
    ----------
    pixel_length : int
        Number of pixels in input curve/line.
    window_size_px : int
        The size of window of measurement.
    label : np.ndarray
        Array of coordinates for the input curve/line.

    Yields
    ------
    np.ndarray
        Array of coordinates for the window of measurement in the input curve/line.
    """
    subset_start = 0
    if window_size_px >= 10:
        subset_end = int(window_size_px + subset_start)
    else:
        subset_end = int(pixel_length)
        logger.warning(
            f"Window size {window_size_px} is less than 10 pixels, using full length"
        )
    
    while subset_end <= pixel_length:
        subset = label[subset_start:subset_end]
        yield subset
        subset_start += 1
        subset_end += 1


def within_element_func(
    output_path: Union[str, pathlib.Path],
    name: str,
    element: Any,
    taubin_df: pd.Series
) -> bool:
    """Save within-element curvature distribution.

    Parameters
    ----------
    output_path : str or pathlib.Path
        Output directory path.
    name : str
        Image name.
    element : Any
        Region properties element.
    taubin_df : pd.Series
        Series of curvature values.

    Returns
    -------
    bool
        True if saved successfully.
    """
    from ..utils.filesystem import make_subdirectory
    
    label_name = str(element.label)
    element_df = pd.DataFrame(taubin_df)
    element_df.columns = ["curv"]
    element_df["label"] = label_name

    output_path = make_subdirectory(output_path, append_name="WithinElement")
    save_path = pathlib.Path(output_path) / f"WithinElement_{name}_Label-{label_name}.csv"
    element_df.to_csv(save_path)
    logger.debug(f"Saved within-element data to {save_path}")

    return True


def analyze_each_curv(
    element: Any,
    window_size_px: Optional[int],
    resolution: float,
    output_path: Union[str, pathlib.Path],
    name: str,
    within_element: bool
) -> Optional[Union[List[float], pd.DataFrame]]:
    """Calculates curvature for each labeled element in an array.

    Parameters
    ----------
    element : Any
        A RegionProperties object from scikit-image regionprops function.
    window_size_px : int, optional
        Number of pixels to be used for window of measurement.
    resolution : float
        Number of pixels per mm in original image.
    output_path : str or pathlib.Path
        Output directory path.
    name : str
        Image name.
    within_element : bool
        Whether to save within-element data.

    Returns
    -------
    list or pd.DataFrame, optional
        A list of the mean and median curvatures and the element length, or DataFrame.
    """
    from ..processing.geometry import pixel_length_correction
    
    element_label = np.array(element.coords)

    element_pixel_length = int(element.area)
    corr_element_pixel_length = pixel_length_correction(element)
    length_mm = float(corr_element_pixel_length / resolution)

    if window_size_px is not None:
        window_size_px = int(window_size_px)

        subset_loop = subset_gen(element_pixel_length, window_size_px, element_label)

        curv = [
            taubin_curv(element_coords, resolution) for element_coords in subset_loop
        ]

        taubin_df = pd.Series(curv).astype("float")

        # Trim outliers
        taubin_df2 = taubin_df[
            taubin_df.between(taubin_df.quantile(0.01), taubin_df.quantile(0.99))
        ]

        curv_mean = taubin_df2.mean()
        curv_median = taubin_df2.median()

        within_element_df = [curv_mean, curv_median, length_mm]

        if within_element:
            within_element_func(output_path, name, element, taubin_df)

        if within_element_df is not None or np.nan:
            return within_element_df
        else:
            return None

    else:
        curv = taubin_curv(element.coords, resolution)
        within_element_df = pd.DataFrame({"curv": [curv], "length": [length_mm]})

        if within_element_df is not None or np.nan:
            return within_element_df
        else:
            return None


def analyze_all_curv(
    img: np.ndarray,
    name: str,
    output_path: Union[str, pathlib.Path],
    resolution: float,
    window_size: Union[float, int, List],
    window_unit: str,
    test: bool,
    within_element: bool
) -> pd.DataFrame:
    """Analyzes curvature for all elements in an image.

    Parameters
    ----------
    img : np.ndarray
        Pruned skeleton of curves/lines as a uint8 ndarray.
    name : str
        Image name.
    output_path : str or pathlib.Path
        Output directory.
    resolution : float
        Number of pixels per mm in original image.
    window_size : float or int or list
        Desired size for window of measurement in mm.
    window_unit : str
        Unit for window size ('px' or 'mm').
    test : bool
        True or False for whether this is being run for validation tests.
    within_element : bool
        True or False for whether to save spreadsheets with within element curvature values.

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame with summary data for all elements in image.
    """
    from ..processing.binary import check_bin
    
    if type(img) != np.ndarray:
        logger.debug(f"Converting image type from {type(img)} to ndarray")
        img = np.array(img)

    img = check_bin(img)

    label_image, num_elements = skimage.measure.label(
        img.astype(int), connectivity=2, return_num=True
    )
    logger.info(f"Found {num_elements} elements in the image")

    props = skimage.measure.regionprops(label_image)

    if not isinstance(window_size, list):
        window_size = [window_size]

    im_sumdf = [
        window_iter(
            props, name, i, window_unit, resolution, output_path, test, within_element
        )
        for i in window_size
    ]

    im_sumdf = pd.concat(im_sumdf)

    return im_sumdf


def window_iter(
    props: List,
    name: str,
    window_size: Optional[Union[float, int]],
    window_unit: str,
    resolution: float,
    output_path: Union[str, pathlib.Path],
    test: bool,
    within_element: bool
) -> pd.DataFrame:
    """Iterate over different window sizes for curvature analysis.

    Parameters
    ----------
    props : List
        List of region properties.
    name : str
        Image name.
    window_size : float or int, optional
        Window size for measurement.
    window_unit : str
        Unit for window size ('px' or 'mm').
    resolution : float
        Number of pixels per mm.
    output_path : str or pathlib.Path
        Output directory path.
    test : bool
        Whether this is a test run.
    within_element : bool
        Whether to save within-element data.

    Returns
    -------
    pd.DataFrame
        Summary DataFrame for the image.
    """
    from ..utils.filesystem import make_subdirectory
    
    tempdf = []

    if window_size is not None:
        if window_unit != "px":
            window_size_px = int(window_size * resolution)
        else:
            window_size_px = int(window_size)
            window_size = int(window_size)

        logger.debug(f"Window size for analysis is {window_size_px} {window_unit}")

        name = str(name + "_WindowSize-" + str(window_size) + str(window_unit))

        tempdf = [
            analyze_each_curv(
                hair, window_size_px, resolution, output_path, name, within_element
            )
            for hair in props
            if hair.area > window_size
        ]

        within_im_curvdf = pd.DataFrame(
            tempdf, columns=["curv_mean", "curv_median", "length"]
        )

        within_im_curvdf2 = pd.DataFrame(
            within_im_curvdf, columns=["curv_mean", "curv_median", "length"]
        ).dropna()

        output_path = make_subdirectory(output_path, append_name="analysis")
        save_path = pathlib.Path(output_path) / f"ImageSum_{name}.csv"
        within_im_curvdf2.to_csv(save_path)
        logger.debug(f"Saved image summary to {save_path}")

        curv_mean_im_mean = within_im_curvdf2["curv_mean"].mean()
        curv_mean_im_median = within_im_curvdf2["curv_mean"].median()
        curv_median_im_mean = within_im_curvdf2["curv_median"].mean()
        curv_median_im_median = within_im_curvdf2["curv_median"].median()
        length_mean = within_im_curvdf2["length"].mean()
        length_median = within_im_curvdf2["length"].median()
        hair_count = len(within_im_curvdf2.index)

        im_sumdf = pd.DataFrame(
            {
                "ID": [name],
                "curv_mean_mean": [curv_mean_im_mean],
                "curv_mean_median": [curv_mean_im_median],
                "curv_median_mean": [curv_median_im_mean],
                "curv_median_median": [curv_median_im_median],
                "length_mean": [length_mean],
                "length_median": [length_median],
                "hair_count": [hair_count],
            }
        )

        return im_sumdf

    else:
        logger.warning("Window size is None, returning empty DataFrame")
        return pd.DataFrame()
