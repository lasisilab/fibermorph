"""Filesystem utility functions for fibermorph package."""

import os
import pathlib
import shutil
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


def make_subdirectory(directory: Union[str, pathlib.Path], append_name: str = "") -> pathlib.Path:
    """Makes subdirectories.

    Parameters
    ----------
    directory : str or pathlib.Path
        A string with the path of directory where subdirectories should be created.
    append_name : str
        A string to be appended to the directory path (name of the subdirectory created).

    Returns
    -------
    pathlib.Path
        A pathlib object for the subdirectory created.
    """
    # Define the path of the directory within which this function will make a subdirectory.
    directory = pathlib.Path(directory)
    # The name of the subdirectory.
    append_name = str(append_name)
    # Define the output path by the initial directory and join (i.e. "+") the appropriate text.
    output_path = pathlib.Path(directory).joinpath(str(append_name))

    # Use pathlib to see if the output path exists, if it is there it returns True
    if not pathlib.Path(output_path).exists():
        # Log status
        logger.info(
            f"This output path doesn't exist:\n            {output_path} \n Creating..."
        )

        # Use pathlib to create the folder.
        pathlib.Path.mkdir(output_path, parents=True, exist_ok=True)

        # Log status to let you know that the folder has been created
        logger.info("Output path has been created")
    else:
        # This will print exactly what you tell it, including the space.
        logger.info(f"Output path already exists:\n               {output_path}")
    
    return output_path


def copy_if_exist(file: Union[str, pathlib.Path], directory: Union[str, pathlib.Path]) -> bool:
    """Copies files to destination directory.

    Parameters
    ----------
    file : str or pathlib.Path
        Path for file to be copied.
    directory : str or pathlib.Path
        Path for destination directory.

    Returns
    -------
    bool
        True or false depending on whether copying was successful.
    """
    path = pathlib.Path(file)
    destination = directory

    if os.path.isfile(path):
        shutil.copy(path, destination)
        logger.debug(f"File {path} has been copied")
        return True
    else:
        logger.debug(f"File {path} does not exist")
        return False


def list_images(directory: Union[str, pathlib.Path]) -> List[pathlib.Path]:
    """Generates a list of all .tif and/or .tiff files in a directory.

    Parameters
    ----------
    directory : str or pathlib.Path
        The directory in which the function will recursively search for .tif and .tiff files.

    Returns
    -------
    List[pathlib.Path]
        A list of pathlib objects with the paths to the image files.
    """
    exts = [".tif", ".tiff"]
    mainpath = pathlib.Path(directory)
    file_list = [p for p in pathlib.Path(mainpath).rglob("*") if p.suffix in exts]

    list.sort(file_list)  # sort the files
    logger.debug(f"Found {len(file_list)} image files")

    return file_list
