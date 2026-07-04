"""Image collection utilities."""

from __future__ import annotations

import os

TIFF_EXTENSIONS = {".tif", ".tiff"}
RAW_EXTENSIONS  = {".nef", ".cr2", ".arw", ".dng", ".orf", ".rw2"}
IMAGE_EXTENSIONS = TIFF_EXTENSIONS | {".png", ".jpg", ".jpeg"}


def collect_images(directory: str, extensions: set | None = None) -> list[str]:
    """Return sorted list of image paths in a directory matching given extensions.

    Defaults to TIFF, PNG, and RAW extensions.
    """
    if extensions is None:
        extensions = IMAGE_EXTENSIONS | RAW_EXTENSIONS
    paths = []
    for fname in sorted(os.listdir(directory)):
        if os.path.splitext(fname)[1].lower() in extensions:
            paths.append(os.path.join(directory, fname))
    return paths
