"""fibermorph: A toolkit for analyzing hair fiber morphology."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("fibermorph")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0.dev"

# Always-available utilities (pure Python / lightweight deps only)
from .utils.filesystem import make_subdirectory, copy_if_exist, list_images
from .utils.timing import convert, timing
from .utils.metadata import parse_canonical_name, collect_images

# Core curvature functions (numpy + scipy only — no cv2)
from .core.curvature import (
    taubin_curv,
    subset_gen,
    analyze_each_curv,
    analyze_all_curv,
    window_iter,
    curl_index_from_skeleton,
    wave_count,
)

# Heavier imports wrapped so the package still loads without opencv/scikit-image
try:
    from .workflows import raw2gray, curvature, section, batch
    from .analysis.curvature_pipeline import curvature_seq
    from .analysis.section_pipeline import section_seq
    from .core.section import (
        section_props,
        crop_section,
        segment_section,
        save_sections,
        section_props_extended,
    )
    from .core.shape_analysis import (
        compute_efd,
        compute_radial_profile,
        extract_features_from_array,
        classify_shape,
    )
    from .core.filters import filter_curv, filter_curv_clahe
    from .processing.binary import check_bin, binarize_curv, remove_particles
    from .processing.morphology import skeletonize, prune, diag
    from .processing.geometry import (
        define_structure,
        find_structure,
        pixel_length_correction,
    )
    from .io.readers import imread
    from .io.writers import save_image
    from .io.converters import raw_to_gray
except ImportError:
    pass

# Demo (lightweight; may fail if requests not installed)
try:
    from .demo import demo
except ImportError:
    pass

__all__ = [
    "__version__",
    # Utility functions
    "make_subdirectory",
    "copy_if_exist",
    "list_images",
    "convert",
    "timing",
    "parse_canonical_name",
    "collect_images",
    # Core curvature
    "taubin_curv",
    "subset_gen",
    "analyze_each_curv",
    "analyze_all_curv",
    "window_iter",
    "curl_index_from_skeleton",
    "wave_count",
    # Main workflows
    "raw2gray",
    "curvature",
    "section",
    "batch",
    # Analysis pipelines
    "curvature_seq",
    "section_seq",
    # Core section
    "section_props",
    "crop_section",
    "segment_section",
    "save_sections",
    "section_props_extended",
    # Shape analysis
    "compute_efd",
    "compute_radial_profile",
    "extract_features_from_array",
    "classify_shape",
    # Filters
    "filter_curv",
    "filter_curv_clahe",
    # Processing
    "check_bin",
    "binarize_curv",
    "remove_particles",
    "skeletonize",
    "prune",
    "diag",
    "define_structure",
    "find_structure",
    "pixel_length_correction",
    # I/O
    "imread",
    "save_image",
    "raw_to_gray",
    # Demo
    "demo",
]
