"""Cross-section analysis functions for fibermorph package."""

import pathlib
from typing import Tuple, Union
import logging

import numpy as np
import pandas as pd
import scipy.spatial.distance
import skimage
import skimage.filters
import skimage.io
import skimage.measure
import skimage.segmentation
import skimage.util
from PIL import Image

logger = logging.getLogger(__name__)


def section_props(
    props: list,
    im_name: str,
    resolution: float,
    minpixel: float,
    maxpixel: float,
    im_center: list
) -> Tuple[pd.DataFrame, np.ndarray, tuple]:
    """Extract section properties from region props.

    Parameters
    ----------
    props : list
        List of region properties from skimage.
    im_name : str
        Image name.
    resolution : float
        Number of pixels per micron.
    minpixel : float
        Minimum pixel size for sections.
    maxpixel : float
        Maximum pixel size for sections.
    im_center : list
        Center coordinates of the image.

    Returns
    -------
    section_data : pd.DataFrame
        DataFrame with section measurements.
    bin_im : np.ndarray
        Binary image of the section.
    bbox : tuple
        Bounding box of the section.
    """
    props_df = [
        [
            region.label,
            region.centroid,
            scipy.spatial.distance.euclidean(im_center, region.centroid),
            region.filled_area,
            region.minor_axis_length,
            region.major_axis_length,
            region.eccentricity,
            region.filled_image,
            region.bbox,
        ]
        for region in props
        if region.minor_axis_length >= minpixel and region.major_axis_length <= maxpixel
    ]
    props_df = pd.DataFrame(
        props_df,
        columns=[
            "label",
            "centroid",
            "distance",
            "area",
            "min",
            "max",
            "eccentricity",
            "image",
            "bbox",
        ],
    )

    section_id = props_df["distance"].astype(float).idxmin()

    section = props_df.iloc[section_id]

    area_mu = section["area"] / np.square(resolution)
    min_diam = section["min"] / resolution
    max_diam = section["max"] / resolution
    eccentricity = section["eccentricity"]

    section_data = pd.DataFrame(
        {
            "ID": [im_name],
            "area": [area_mu],
            "eccentricity": [eccentricity],
            "min": [min_diam],
            "max": [max_diam],
        }
    )

    bin_im = section["image"]
    bbox = section["bbox"]

    return section_data, bin_im, bbox


def crop_section(
    img: np.ndarray,
    im_name: str,
    resolution: float,
    minpixel: float,
    maxpixel: float,
    im_center: list
) -> np.ndarray:
    """Crop section from image.

    Parameters
    ----------
    img : np.ndarray
        Input image array.
    im_name : str
        Image name.
    resolution : float
        Number of pixels per micron.
    minpixel : float
        Minimum pixel size for sections.
    maxpixel : float
        Maximum pixel size for sections.
    im_center : list
        Center coordinates of the image.

    Returns
    -------
    np.ndarray
        Cropped image array.
    """
    try:
        # binarize
        thresh = skimage.filters.threshold_minimum(img)
        bin_img = skimage.segmentation.clear_border(img < thresh)
        # label the image
        label_im, num_elem = skimage.measure.label(
            bin_img, connectivity=2, return_num=True
        )

        props = skimage.measure.regionprops(label_image=label_im, intensity_image=img)

        section_data, bin_im, bbox = section_props(
            props, im_name, resolution, minpixel, maxpixel, im_center
        )

        pad = 100
        minr = bbox[0] - pad
        minc = bbox[1] - pad
        maxr = bbox[2] + pad
        maxc = bbox[3] + pad
        bbox_pad = [minc, minr, maxc, maxr]
        crop_im = np.asarray(Image.fromarray(img).crop(bbox_pad))

    except Exception as e:
        logger.warning(f"Error cropping section for {im_name}, using center crop: {e}")
        minr = int(im_center[0] / 2)
        minc = int(im_center[1] / 2)
        maxr = int(im_center[0] * 1.5)
        maxc = int(im_center[1] * 1.5)

        bbox_pad = [minc, minr, maxc, maxr]
        crop_im = np.asarray(Image.fromarray(img).crop(bbox_pad))

    return crop_im


def segment_section(
    crop_im: np.ndarray,
    im_name: str,
    resolution: float,
    minpixel: float,
    maxpixel: float,
    im_center: list
) -> Tuple[pd.DataFrame, np.ndarray]:
    """Segment section using morphological active contours.

    Parameters
    ----------
    crop_im : np.ndarray
        Cropped image array.
    im_name : str
        Image name.
    resolution : float
        Number of pixels per micron.
    minpixel : float
        Minimum pixel size for sections.
    maxpixel : float
        Maximum pixel size for sections.
    im_center : list
        Center coordinates of the image.

    Returns
    -------
    section_data : pd.DataFrame
        DataFrame with section measurements.
    bin_im : np.ndarray
        Binary image of the section.
    """
    try:
        thresh = skimage.filters.threshold_minimum(crop_im)
        bin_ls_set = crop_im < thresh

        seg_im = skimage.segmentation.morphological_chan_vese(
            np.asarray(crop_im), 40, init_level_set=bin_ls_set, smoothing=4
        )

        seg_im_inv = np.asarray(seg_im != 0)

        crop_label_im, num_elem = skimage.measure.label(
            seg_im_inv, connectivity=2, return_num=True
        )

        crop_props = skimage.measure.regionprops(
            label_image=crop_label_im, intensity_image=np.asarray(crop_im)
        )

        section_data, bin_im, bbox = section_props(
            crop_props, im_name, resolution, minpixel, maxpixel, im_center
        )

    except Exception as e:
        logger.error(f"Error segmenting section for {im_name}: {e}")
        section_data = pd.DataFrame(
            {
                "ID": [np.nan],
                "area": [np.nan],
                "eccentricity": [np.nan],
                "min": [np.nan],
                "max": [np.nan],
            }
        )
        thresh = skimage.filters.threshold_minimum(crop_im)
        bin_im = crop_im < thresh

    return section_data, bin_im


def save_sections(
    output_path: Union[str, pathlib.Path],
    im_name: str,
    im: Union[np.ndarray, Image.Image],
    save_crop: bool = False
) -> None:
    """Save section images.

    Parameters
    ----------
    output_path : str or pathlib.Path
        Output directory path.
    im_name : str
        Image name.
    im : np.ndarray or PIL.Image
        Image to save.
    save_crop : bool
        Whether this is a cropped image or binary image.
    """
    from ..utils.filesystem import make_subdirectory
    
    if save_crop:
        crop_path = make_subdirectory(output_path, "crop")
        savename = pathlib.Path(crop_path) / f"{im_name}.tiff"
        try:
            skimage.io.imsave(str(savename), im)
        except AttributeError:
            im.save(savename)
        logger.debug(f"Saved crop to {savename}")
    else:
        binary_path = make_subdirectory(output_path, "binary")
        savename = pathlib.Path(binary_path) / f"{im_name}.tiff"
        im = Image.fromarray(im)
        im.save(savename)
        logger.debug(f"Saved binary to {savename}")
