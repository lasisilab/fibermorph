"""Image writing functions for fibermorph package."""

import pathlib
from typing import Union
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def save_image(
    img: np.ndarray, 
    output_path: Union[str, pathlib.Path], 
    name: str, 
    suffix: str = ""
) -> pathlib.Path:
    """Save image to disk.

    Parameters
    ----------
    img : np.ndarray
        Image array to save.
    output_path : str or pathlib.Path
        Directory where image should be saved.
    name : str
        Base name for the image file.
    suffix : str, optional
        Suffix to append to the filename before extension.

    Returns
    -------
    pathlib.Path
        Path to the saved image file.
    """
    output_path = pathlib.Path(output_path)
    if suffix:
        filename = f"{name}_{suffix}.tiff"
    else:
        filename = f"{name}.tiff"
    
    full_path = output_path / filename
    
    # Convert to PIL Image and save
    if img.dtype == bool:
        img = img.astype(np.uint8) * 255
    
    Image.fromarray(img).save(str(full_path))
    logger.debug(f"Saved image to {full_path}")
    
    return full_path
