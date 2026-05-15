"""Filename metadata parsing and image collection utilities."""

from __future__ import annotations

import os
import re

# Standard naming convention: SAMPLEID_REGION_REPLICATE.tiff
_STANDARD_RE = re.compile(r"^(\d+)_([A-Za-z]+)_(\d+)", re.IGNORECASE)
# P-prefix variant (e.g. P1200851.tiff — no region/replicate)
_P_PREFIX_RE = re.compile(r"^(P\d+)", re.IGNORECASE)

TIFF_EXTENSIONS = {".tif", ".tiff"}
RAW_EXTENSIONS  = {".nef", ".cr2", ".arw", ".dng", ".orf", ".rw2"}
IMAGE_EXTENSIONS = TIFF_EXTENSIONS | {".png", ".jpg", ".jpeg"}


def parse_metadata(filename: str) -> dict:
    """Parse sample_id, region, and replicate from a filename.

    Naming conventions
    ------------------
    Standard : 140025_A_3.tiff  ->  {sample_id:'140025', region:'A', replicate:'3'}
    P-prefix : P1200851.tiff    ->  {sample_id:'P1200851', region:'', replicate:''}
    Unknown  : anything.tiff    ->  {sample_id:stem, region:'', replicate:''}
    """
    stem = os.path.splitext(os.path.basename(filename))[0]

    m = _STANDARD_RE.match(stem)
    if m:
        return {"sample_id": m.group(1), "region": m.group(2).upper(),
                "replicate": m.group(3)}

    m = _P_PREFIX_RE.match(stem)
    if m:
        return {"sample_id": m.group(1), "region": "", "replicate": ""}

    return {"sample_id": stem, "region": "", "replicate": ""}


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
