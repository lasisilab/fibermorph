"""Filename metadata parsing and image collection utilities."""

from __future__ import annotations

import os

TIFF_EXTENSIONS = {".tif", ".tiff"}
RAW_EXTENSIONS  = {".nef", ".cr2", ".arw", ".dng", ".orf", ".rw2"}
IMAGE_EXTENSIONS = TIFF_EXTENSIONS | {".png", ".jpg", ".jpeg"}

# Canonical naming convention enforced on the user:
#     Individual_Sample_Side.ext      e.g.  Y_5_B.tif
# where Individual is the between-individual unit, Sample is a within-individual
# replicate, and Side is A/B for the two mirrored faces of one physical section.
CANONICAL_CONVENTION = "Individual_Sample_Side  (e.g. Y_5_B.tif)"


def parse_canonical_name(filename: str) -> dict:
    """Split a canonically-named file into individual / sample / side labels.

    Lenient by design: the fields are read positionally from an underscore split,
    missing trailing fields come back empty, and any tokens after the third are
    ignored. No grouping or inference is performed — the labels are attached as
    columns purely so the user can group them downstream.

        Y_5_B_12.5mag.tif -> {individual:'Y', sample:'5', side:'B'}
        Y_5.tif           -> {individual:'Y', sample:'5', side:''}
        Y.tif             -> {individual:'Y', sample:'',  side:''}
        anything.tif      -> {individual:'anything', sample:'', side:''}
    """
    stem  = os.path.splitext(os.path.basename(filename))[0]
    parts = stem.split("_")
    return {
        "individual": parts[0] if len(parts) >= 1 else "",
        "sample":     parts[1] if len(parts) >= 2 else "",
        "side":       parts[2] if len(parts) >= 3 else "",
    }


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
