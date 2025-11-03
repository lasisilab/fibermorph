"""
Backward compatibility shim for fibermorph.fibermorph module.

This module provides backward compatibility for code that imports from
fibermorph.fibermorph directly. All functionality has been refactored into
separate modules.

Deprecated: Import from fibermorph directly instead.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "Importing from fibermorph.fibermorph is deprecated. "
    "Import from fibermorph directly instead. "
    "For example: 'from fibermorph import imread' instead of "
    "'from fibermorph.fibermorph import imread'",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public functions from the main package
from fibermorph import (
    # Version
    __version__,
    # Main workflows
    raw2gray,
    curvature,
    section,
    # Analysis pipelines
    curvature_seq,
    section_seq,
    # Core functions
    taubin_curv,
    subset_gen,
    analyze_each_curv,
    analyze_all_curv,
    window_iter,
    section_props,
    crop_section,
    segment_section,
    save_sections,
    filter_curv,
    # Processing functions
    check_bin,
    binarize_curv,
    remove_particles,
    skeletonize,
    prune,
    diag,
    define_structure,
    find_structure,
    pixel_length_correction,
    # I/O functions
    imread,
    save_image,
    raw_to_gray,
    # Utility functions
    make_subdirectory,
    copy_if_exist,
    list_images,
    convert,
    timing,
    # Demo
    demo,
)

# Import CLI functions
from .cli import parse_args, main

# Import parallel processing
from .analysis.parallel import tqdm_joblib

# For any code that might reference these directly
__all__ = [
    "__version__",
    "raw2gray",
    "curvature",
    "section",
    "curvature_seq",
    "section_seq",
    "taubin_curv",
    "subset_gen",
    "analyze_each_curv",
    "analyze_all_curv",
    "window_iter",
    "section_props",
    "crop_section",
    "segment_section",
    "save_sections",
    "filter_curv",
    "check_bin",
    "binarize_curv",
    "remove_particles",
    "skeletonize",
    "prune",
    "diag",
    "define_structure",
    "find_structure",
    "pixel_length_correction",
    "imread",
    "save_image",
    "raw_to_gray",
    "make_subdirectory",
    "copy_if_exist",
    "list_images",
    "convert",
    "timing",
    "demo",
    "parse_args",
    "main",
    "tqdm_joblib",
]
