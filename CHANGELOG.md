# Changelog

All notable changes to fibermorph will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
