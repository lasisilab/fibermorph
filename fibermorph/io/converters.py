"""Image conversion functions for fibermorph package."""

import os
import pathlib
from typing import Union
import logging

import rawpy
from PIL import Image

logger = logging.getLogger(__name__)


def raw_to_gray(
    imgfile: Union[str, pathlib.Path], 
    output_directory: Union[str, pathlib.Path]
) -> pathlib.Path:
    """Function to convert raw image file into tiff file.

    Parameters
    ----------
    imgfile : str or pathlib.Path
        Path to raw image file.
    output_directory : str or pathlib.Path
        String with the path where the converted images should be created.

    Returns
    -------
    pathlib.Path
        A pathlib object with the path to the converted image file.
    """
    imgfile = os.path.abspath(imgfile)
    output_directory = pathlib.Path(output_directory)
    basename = os.path.basename(imgfile)
    name = os.path.splitext(basename)[0] + ".tiff"
    output_name = output_directory / name

    try:
        with rawpy.imread(imgfile) as raw:
            rgb = raw.postprocess(use_auto_wb=True)
            im = Image.fromarray(rgb).convert("LA")
            im.save(str(output_name))
        logger.info(
            f"{name} has been successfully converted to a grayscale tiff.\n"
            f"Path is {output_name}\n"
        )
    except Exception as e:
        logger.error(f"Error converting {imgfile}: {e}")
        raise

    return output_name
