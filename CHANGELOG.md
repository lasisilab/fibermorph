# Changelog

All notable changes to fibermorph will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

> These changes refine the (not-yet-published) 2.0.0 line. The current PyPI
> release is 1.0.1; 2.0.0 lives on the `fibermorph-dev` branch and has not been
> tagged. At release time these entries can be folded into 2.0.0 or tagged a
> new version.

### Added
- **Resolution in either direction.** GUI and CLI now accept resolution as
  pixels-per-unit *or* unit-per-pixel and convert internally — GUI unit selector
  (px/µm ↔ µm/px, px/mm ↔ mm/px), CLI `--resolution_mu_units {px_per_um,um_per_px}`
  and `--resolution_mm_units {px_per_mm,mm_per_px}`. Prevents the
  µm/px-vs-px/µm mix-up that silently corrupted calibrated measurements.
  (`fibermorph.utils.units`)
- **Per-fragment curvature in the GUI.** The Curvature view reports each detected
  fiber fragment's length and mean/median curvature (one row per fragment), a
  per-image summary, and per-sample + pooled distribution histograms (shared
  x-axis for cross-sample comparison).
- **Run Local.** `fibermorph-gui` runs the same GUI on your own machine with the
  upload cap raised to 5 GB and a "Folder on disk" input that reads images
  straight from a directory (no upload). A Run Local view documents this and
  shows whether you are running hosted or local.
- **Lasisi Lab GUI design system** (`fibermorph.gui.styles`): a left sidebar
  console (brand lockup, grouped nav with SVG glyphs, status footer), per-view
  headers, at-a-glance metric cards, and brand-colored charts.
- Help text for the Taubin window and CLAHE controls in the GUI.

### Changed
- **GUI is now a sidebar console** with four views — **Cross-Section**,
  **Curvature**, **Run Local**, **Run Remote** — replacing the previous top tab
  bar (there is no "Submit & Monitor" or "Results" tab).
- **"Run at scale" → "Run Remote".** It builds a downloadable SBATCH script with
  generic placeholders; it does not submit or monitor jobs and no longer bakes in
  personal account/partition/path defaults.
- **Curvature output refocused.** Fragment-level length + mean/median curvature
  are the primary output; the v2 extended metrics (curl index, wave count) moved
  behind an off-by-default "extended (experimental)" toggle.
- **Per-image analysis only.** Filename parsing and per-sample grouping removed;
  each result row records only its `source_file`.
- `fibermorph-gui` seeds an empty Streamlit credentials file on first run
  (non-destructive) so it does not stall on Streamlit's one-time email prompt.

### Removed
- **Curvature diameter metric** (`diameter_mean_mu`, `diameter_cv`) and its
  medial-axis distance-map computation — a v2 fork addition that is not yet
  validated. The medial-axis skeleton used by the curl-index path is unchanged.
- **Per-sample batch aggregation** (`hair_analysis_per_sample.csv`); the batch
  pipeline now emits a single per-image table.

### Fixed
- **Section resolution unit mislabel** (`µm/px` where the code needs `px/µm`) in
  the GUI and docstrings — the cause of "empty mask" segmentation failures on
  correctly-focused images.
- US spelling throughout the GUI (analyze, fiber, color).

## [2.0.0] - 2026-05-14

### Breaking Changes
- Section analysis output now includes EFD (40 coefficients), Hu moments (7), radial profile (7 metrics), and `shape_class` columns when `--extended-features` is used
- Curvature output includes `curl_index`, `wave_count`, `diameter_mean_mu`, `curv_std`, `curv_cv`, `curv_iqr` columns when `--extended-curvature` is used

### Added
- **SAM2 segmentation** (optional GPU): `--use-sam2` flag; falls back to watershed automatically when SAM2 is unavailable
  - Install: `pip install git+https://github.com/facebookresearch/segment-anything-2`
  - Checkpoint: place `sam2.1_hiera_tiny.pt` in `fibermorph/checkpoints/`
- **Extended section features**: EFD (40 coefficients), Hu moments (7), radial distance profile (7 metrics + asymmetry index), shape classification into 7 morphotypes (`--extended-features`)
- **CLAHE preprocessing** for curvature: `--use-clahe` flag improves results on images with uneven illumination
- **Extended curvature metrics**: curl index (chord/arc ratio), wave count (peak detection), diameter statistics from medial axis (`--extended-curvature`)
- **Multi-factor candidate scoring** for cross-section segmentation: center-bias + circularity + solidity + darkness
- **Batch pipeline**: `fibermorph.workflows.batch()` produces `hair_analysis_per_image.csv` and `hair_analysis_per_sample.csv`
- **Filename metadata parsing**: `{SAMPLEID}_{REGION}_{REPLICATE}` convention via `fibermorph.utils.metadata.parse_metadata()`
- **5-tab Streamlit GUI**: Quick Test, Segmentation Preview, Batch (Cluster), Submit & Monitor, Results
- **18 publication-ready visualization figures** via `fibermorph.gui.visualizations`
- **SLURM SBATCH script generation** in the GUI Batch tab (calls `fibermorph` CLI)
- **GPU Docker target**: two-stage CPU + GPU build (`docker build --target cpu` or `--target gpu`)
- `opencv-python-headless` as a core dependency (required for headless server and container environments)
- `seaborn` as an optional dependency (included in `[viz]` and `[gui]` extras)

### Kept from v1
- `raw2gray` RAW-to-grayscale conversion pipeline (unchanged)
- Demo data download (`--demo_real_curv`, `--demo_real_section`)
- `within_element` per-hair curvature CSV (`--within_element`)
- Multi-window sweep: `--window_size` accepts a list of values
- Taubin circle fitting core (`taubin_curv`)
- `pixel_length_correction` (√2 diagonal arc-length correction)
- Timestamped output directories
- `--save_image` intermediate image saving
- All existing CLI flags (backward compatible; new flags are additive and default to off)

## [1.0.1] - 2025-11-06

### Fixed
- **Python support**: Corrected version constraint to 3.10-3.12 (removed 3.13 support due to dependency compatibility issues)
- Simplified dependency specifications (removed conditional Python 3.13 versions)
- Updated CI to test only Python 3.10, 3.11, 3.12
- Updated documentation to clarify Python 3.13 is not yet supported

## [1.0.0] - 2025-11-06

### 🎉 Major Release: fibermorph 1.0 with GUI

This is a major release introducing an interactive graphical user interface and several breaking changes.

### Added
- **Streamlit GUI**: Interactive web-based interface for easy analysis
  - Upload TIFF images or download from URLs
  - Real-time parameter configuration
  - Interactive results viewing
  - Download results as CSV and ZIP
  - Launch with `fibermorph-gui` command
- **Streamlit Cloud deployment support**
  - `streamlit_app.py` entry point
  - `requirements.txt` for cloud deployment
  - `.streamlit/config.toml` for app configuration
  - `packages.txt` for system dependencies
  - Deployment guide in `STREAMLIT_DEPLOYMENT.md`
- **GUI launcher module** (`fibermorph/gui/launcher.py`) for proper Streamlit integration
- **Demo data download** capability in GUI
- `.python-version` file specifying Python 3.11

### Changed
- **BREAKING**: Minimum Python version raised from 3.9 to 3.10
  - Required for Streamlit compatibility
  - Supported versions: 3.10, 3.11, 3.12, 3.13
- **Package description** updated to emphasize interactive nature
- **README** restructured to highlight GUI as primary interface
  - GUI installation and usage now featured first
  - CLI documentation moved to "Advanced Users" section
  - Added quick start guide for GUI
  - Updated installation instructions
- **Dependency updates**:
  - Added `streamlit >= 1.28.0` as optional dependency
  - Updated `poetry.lock` with GUI dependencies
- **Optional extras** consolidated:
  - `[gui]`: Streamlit interface
  - `[raw]`: RAW image conversion
  - `[viz]`: Visualization helpers

### Fixed
- `fibermorph-gui` command now properly launches through Streamlit CLI
  - No more ScriptRunContext warnings
  - Consistent behavior with `streamlit run`
- Streamlit config file compatibility (removed conflicting CORS option)

### Technical
- Merged `feature/streamlit-gui` branch into main
- Merged `feature/dependency-trim` branch (dependency optimization)
- All 115 tests passing
- Full test coverage maintained

### Migration Guide

**For Python 3.9 users:**
- Python 3.9 is no longer supported
- Please upgrade to Python 3.10+ to use fibermorph 1.0
- Previous versions (0.3.x) remain available for Python 3.9

**For existing users:**
- CLI functionality remains unchanged
- All existing scripts will continue to work
- GUI is optional - install with `pip install "fibermorph[gui]"`

### Deployment

- Package published to PyPI as `fibermorph==1.0.0`
- Streamlit Cloud deployment ready
- Documentation available at [STREAMLIT_DEPLOYMENT.md](STREAMLIT_DEPLOYMENT.md)

---

## [0.3.13] - 2024

### Fixed
- Updated repository URLs to lasisilab/fibermorph
- Corrected package metadata

## [0.3.12] - 2024

### Changed
- Updated README to reflect Python 3.13 support

## [0.3.9-0.3.11] - 2024

### Added
- Python 3.13 compatibility through conditional dependencies

## [0.3.7-0.3.8] - 2024

### Fixed
- PyPI publish workflow metadata version compatibility
- Pinned poetry-core<1.9 for metadata compatibility

---

[1.0.0]: https://github.com/lasisilab/fibermorph/compare/v0.3.13...v1.0.0
[0.3.13]: https://github.com/lasisilab/fibermorph/releases/tag/v0.3.13
