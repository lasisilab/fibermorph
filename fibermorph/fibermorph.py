"""
Backward compatibility module for fibermorph.

DEPRECATED: This module is deprecated. Import from fibermorph directly instead.

All functionality from the original monolithic fibermorph.py file has been
refactored into separate modules under:
- fibermorph.utils: Utility functions (filesystem, timing, logging)
- fibermorph.io: I/O operations (readers, writers, converters)
- fibermorph.processing: Image processing (binary, morphology, geometry)
- fibermorph.core: Core analysis (filters, curvature, section)
- fibermorph.analysis: Analysis pipelines (curvature_pipeline, section_pipeline)
- fibermorph.workflows: Main workflow functions (raw2gray, curvature, section)
- fibermorph.cli: Command-line interface

For backward compatibility, all functions are re-exported from this module.
"""

# Re-export everything from the compatibility module
from .fibermorph_compat import *  # noqa: F401, F403
