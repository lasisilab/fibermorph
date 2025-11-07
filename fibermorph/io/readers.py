"""Image reading functions for fibermorph package."""

import pathlib
from typing import Tuple, Union
import logging

import numpy as np
import skimage
import skimage.io
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def imread(
    input_file: Union[str, pathlib.Path], use_skimage: bool = False
) -> Tuple[np.ndarray, str]:
    """Reads in image as grayscale array.

    Parameters
    ----------
    input_file : str or pathlib.Path
        String with path to input file.
    use_skimage : bool, optional
        Whether to use skimage for reading. Default is False.

    Returns
    -------
    img : np.ndarray
        A grayscale array based on the input image (uint8).
    im_name : str
        A string with the image name.
        
    Raises
    ------
    UnidentifiedImageError
        If the file is not a valid image file.
    FileNotFoundError
        If the file does not exist.
    """
    input_path = pathlib.Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Image file not found: {input_path}")
    
    if not input_path.is_file():
        raise ValueError(f"Path is not a file: {input_path}")
    
    try:
        if use_skimage:
            try:
                img_float = skimage.io.imread(input_file, as_gray=True)
                img = skimage.img_as_ubyte(img_float)
            except ValueError as e:
                logger.warning(f"skimage failed to read {input_file}, falling back to PIL: {e}")
                img = np.array(Image.open(str(input_path)).convert("L"))
        else:
            img = np.array(Image.open(str(input_path)).convert("L"))
    except UnidentifiedImageError as e:
        logger.error(f"Cannot identify image file: {input_path}")
        raise UnidentifiedImageError(
            f"Cannot identify image file '{input_path.name}'. "
            f"Please ensure the file is a valid TIFF image."
        ) from e
    except Exception as e:
        logger.error(f"Error reading image file {input_path}: {e}")
        raise
    
    im_name = input_path.stem
    return img, im_name
