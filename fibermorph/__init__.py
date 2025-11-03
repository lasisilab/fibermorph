"""fibermorph: A toolkit for analyzing hair fiber morphology."""

import importlib.metadata

__version__ = importlib.metadata.version("fibermorph")

# Import main workflow functions for backward compatibility
from .workflows import raw2gray, curvature, section

# Import main analysis functions
from .analysis.curvature_pipeline import curvature_seq
from .analysis.section_pipeline import section_seq

# Import core functions
from .core.curvature import (
    taubin_curv,
    subset_gen,
    analyze_each_curv,
    analyze_all_curv,
    window_iter,
)
from .core.section import (
    section_props,
    crop_section,
    segment_section,
    save_sections,
)
from .core.filters import filter_curv

# Import processing functions
from .processing.binary import check_bin, binarize_curv, remove_particles
from .processing.morphology import skeletonize, prune, diag
from .processing.geometry import (
    define_structure,
    find_structure,
    pixel_length_correction,
)

# Import I/O functions
from .io.readers import imread
from .io.writers import save_image
from .io.converters import raw_to_gray

# Import utility functions
from .utils.filesystem import make_subdirectory, copy_if_exist, list_images
from .utils.timing import convert, timing

# Import demo module
from .demo import demo

__all__ = [
    # Version
    "__version__",
    # Main workflows
    "raw2gray",
    "curvature",
    "section",
    # Analysis pipelines
    "curvature_seq",
    "section_seq",
    # Core functions
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
    # Processing functions
    "check_bin",
    "binarize_curv",
    "remove_particles",
    "skeletonize",
    "prune",
    "diag",
    "define_structure",
    "find_structure",
    "pixel_length_correction",
    # I/O functions
    "imread",
    "save_image",
    "raw_to_gray",
    # Utility functions
    "make_subdirectory",
    "copy_if_exist",
    "list_images",
    "convert",
    "timing",
    # Demo
    "demo",
]
