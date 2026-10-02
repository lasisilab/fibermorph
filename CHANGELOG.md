# Changelog

All notable changes to fibermorph will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

> These changes refine the (not-yet-published) 2.0.0 line. The current PyPI
> release is 1.0.1; 2.0.0 lives on the `fibermorph-dev` branch and has not been
> tagged. At release time these entries can be folded into 2.0.0 or tagged a
> new version.

### Breaking Changes
- **`fibermorph-gui` now starts in hosted mode; local mode requires `--local`.**
  Before, every `fibermorph-gui` launch silently enabled local mode: it set
  `FIBERMORPH_LOCAL=1`, showed a "Folder on disk" input that reads folders on the
  machine running the app, and raised the upload cap to 5 GB. Now plain
  `fibermorph-gui` starts hosted mode: uploads only, a 500 MB upload cap
  (`--server.maxUploadSize 500`), no folder input, and `FIBERMORPH_LOCAL` is left
  unset. To run on your own machine as before, use
  `fibermorph-gui --local` (or set `FIBERMORPH_LOCAL=1` in the environment), which
  also now listens on `localhost` only (`--server.address localhost`). Servers and
  containers that start the app with `fibermorph-gui` (for example the repository's
  Dockerfile) therefore now get hosted mode instead of exposing server folders to
  every visitor. Hosted mode passes no address or port, so settings such as the
  Dockerfile's `STREAMLIT_SERVER_PORT=7860` and `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
  still apply. A container started with `FIBERMORPH_LOCAL=1` now listens on
  `localhost` only and needs `--server.address 0.0.0.0` on the command to be
  reachable.
- **Hosted visitors can no longer set the SAM2 checkpoint.** In hosted mode
  (plain `fibermorph-gui`) the Cross-Section view has no "SAM2 checkpoint path"
  box: the server always uses the file named by `SAM2_CHECKPOINT`, and
  its path is not shown in any view (the Run Remote view's checkpoint box now
  starts empty). fibermorph does not ship a SAM2 checkpoint, so a host that
  wants SAM2 segmentation must download one, set `SAM2_CHECKPOINT` to it on a
  machine with a GPU, and restart the app after changing it. Local mode (`--local`) is unchanged. Details are in
  **Security** below.
- **How the launcher's server options interact with Streamlit's settings.**
  `--server.maxUploadSize` (500 MB hosted, 5000 MB local) is passed on the command
  line, so it overrides `.streamlit/config.toml`; it is not passed when the
  `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` environment variable is set, so a host can set
  its own cap that way. In local mode `--server.address localhost` is always passed
  and overrides `STREAMLIT_SERVER_ADDRESS` and `config.toml`, so folder input is
  never opened to other machines by accident; pass `--server.address <address>` to
  `fibermorph-gui` to change it, and the startup notice then warns that the app is
  reachable from other machines. An empty `--server.address=` counts as changing
  it: Streamlit then listens on every interface, and the notice says so.
- **Curvature has one method: CLAHE preprocessing and extended curvature are
  removed.** `--use-clahe` and `--extended-curvature` now stop with an error
  (exit status 2), the `use_clahe` / `extended_curvature` parameters are gone,
  the `curl_index`, `curl_index_std`, `wave_count`, `wave_count_per_mm` and
  `length_total` columns of the `curvature_seq` / batch output are gone (the
  GUI's own "Total Length (mm)" column stays), and `run_batch` /
  `workflows.batch` curvature output now uses the original method instead of
  the medial-axis path. The old batch values varied from run to run and cannot
  be reproduced exactly, so batch curvature results made before this change
  should be re-run. SBATCH scripts made earlier by the GUI's Run Remote view
  (which turned extended curvature on by default) contain
  `--extended-curvature` and must have it deleted. Details are in **Removed**
  below.
- **A zero, negative or absurdly long `--window_size` now stops with an error.**
  With `--window_unit px`, a zero or negative `--window_size` used to run: the
  log said `less than 10 pixels, using full length` and every hair was measured
  over its whole length. It now exits with code 2 and a usage message before any
  analysis starts, whichever module is chosen. Use a window of 10 pixels or more,
  or `--window_size none` (or leave the option out) to fit whole hairs. A script
  that writes such a value, for example one downloaded earlier from the Run
  Remote view with a "Taubin window (px)" of 0 or less (the view now refuses
  such values), needs a positive window. A window
  longer than 1,000,000,000 pixels (for `mm`, after conversion with
  `--resolution_mm`) is refused in the same way: no image has a hair that long.
  Such a window used to run and measure nothing (`hair_count` 0), or end in a
  traceback when it was extremely long.
- **A negative `--minsize` now stops with an error.**
  `fibermorph --section --minsize -5` used to run, the negative value acting
  as a lower bound of 0. It now exits with code 2 and a usage message before
  any image is read, whichever module is chosen. Use `--minsize 0` or a
  positive number. A script that writes a negative minimum, for example one
  downloaded earlier from the Run Remote view with a "Min diameter (µm)" below
  0 (the view now refuses that), needs a value of 0 or more.

### Added
- **Extra command-line arguments to `fibermorph-gui` reach Streamlit.** They are
  passed through to `streamlit run` after the launcher's own options, so they can
  override them (e.g. `fibermorph-gui --local --server.port 8600`). Before, every
  extra argument was silently ignored.
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
- **Run Local.** `fibermorph-gui --local` runs the same GUI on your own machine
  with the upload cap raised to 5 GB and a "Folder on disk" input that reads images
  straight from a directory (no upload). A Run Local view documents this and
  shows whether you are running hosted or local.
- `fibermorph.gui.inputs`: `save_uploads()`, `display_name()`, `safe_extension()`
  and `restore_names()` for saving uploaded files under generated names and
  putting the uploaded name back into error messages, plus `format_upload_cap()`
  for showing the upload cap as "500 MB" or "5 GB" (all usable and testable
  without running Streamlit).
- `fibermorph-gui --help` documents `--local`; the launcher prints which mode it
  is starting in.
- **Lasisi Lab GUI design system** (`fibermorph.gui.styles`): a left sidebar
  console (brand lockup, grouped nav with SVG glyphs, status footer), per-view
  headers, at-a-glance metric cards, and brand-colored charts.
- Help text for the Taubin window control in the GUI.
- **Golden curvature tests** (`fibermorph/test/test_curvature_golden.py`) that
  compare per-hair and summary curvature against output of the original v0.3.1
  code (scikit-image 0.16.2) for a window in px, a window in mm and the
  whole-hair mode. They run offline on a small synthetic image; a second set
  downloads the two lab demo curvature images (about 6 MB, fetched once per
  test run) and is skipped if the download fails (or reads them from
  `FIBERMORPH_DEMO_CURV_DIR`). The references and the script that made them are
  in `fibermorph/test/test_data/curv_golden/`.

### Changed
- **The upload cap shown in the GUI is the cap Streamlit enforces.** The sidebar
  status and the Run Local view used to say "500 MB" (hosted) or "5 GB" (local)
  whatever cap was set. They now read Streamlit's `server.maxUploadSize`, so a
  host that sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE`, `--server.maxUploadSize` or
  `config.toml` sees the same number in the app as in the file uploader. With no
  setting, the text is the same as before (500 MB hosted, 5 GB local).
- **GUI is now a sidebar console** with four views — **Cross-Section**,
  **Curvature**, **Run Local**, **Run Remote** — replacing the previous top tab
  bar (there is no "Submit & Monitor" or "Results" tab).
- **"Run at scale" → "Run Remote".** It builds a downloadable SBATCH script with
  generic placeholders; it does not submit or monitor jobs and no longer bakes in
  personal account/partition/path defaults.
- **Curvature output refocused.** Fragment-level length + mean/median curvature
  are the primary output.
- **Per-image analysis only.** Filename parsing and per-sample grouping removed;
  each result row records only its `source_file`.
- `fibermorph-gui` seeds an empty Streamlit credentials file on first run
  (non-destructive) so it does not stall on Streamlit's one-time email prompt.

### Removed
- **Curvature diameter metric** (`diameter_mean_mu`, `diameter_cv`) and its
  medial-axis distance-map computation — a v2 fork addition that is not yet
  validated.
- **CLAHE preprocessing and extended curvature metrics for curvature.**
  Curvature analysis now has exactly one method, the published fibermorph
  method (v0.3.1): Frangi ridge filter (the scikit-image 0.16.2 version) ->
  binarize -> remove particles -> skeletonize -> prune -> Taubin circle fits.
  Neither option was part of it.
  - What was removed: `filter_curv_clahe` (CLAHE, then the installed
    scikit-image Frangi filter, then an Otsu threshold computed only on the
    middle 70% of the image, ignoring the top and bottom 15%); the medial-axis
    skeleton path; `curl_index_from_skeleton`, `wave_count` and their helper
    `pixel_length_correction_coords`; the output columns `curl_index`,
    `curl_index_std`, `wave_count`, `wave_count_per_mm` and `length_total`;
    the `use_clahe` and `extended_curvature` parameters of `curvature_seq`,
    `workflows.curvature`, `workflows.batch` and `run_batch`; the CLI flags
    `--use-clahe` and `--extended-curvature`. In the GUI: the "CLAHE
    preprocessing" toggle (Curvature and Run Remote views), the "Show extended
    (experimental) metrics" toggle with the Curl Index, Wave Count and
    Waves/mm columns of the Curvature summary, and the Run Remote "Extended
    curvature metrics" switch. The GUI's per-image "Total Length (mm)"
    (`length_total` in the downloaded CSV) stays: the app sums the fragment
    lengths itself and it never came from the removed pipeline column.
  - Why: neither option was validated against the published method. CLAHE
    used the installed scikit-image's Frangi filter, so its output changed with
    the scikit-image version, and it ignored the top and bottom 15% of the
    image. The extended path replaced `skeletonize` with `medial_axis`, which
    breaks ties at random, so repeated runs on the same image could differ.
  - Scripts that still use the flags: `--use-clahe` and `--extended-curvature`
    remain accepted by the parser but are hidden from `--help`. A command that
    includes either stops before doing any work with exit status 2 and a
    message saying the option was removed because it is not part of the
    published curvature method. SBATCH scripts generated earlier by the GUI's
    Run Remote view usually contain `--extended-curvature` (its switch was on
    by default); delete the flag from them. Python code that passes
    `use_clahe=` or `extended_curvature=` gets a `TypeError`, and importing a
    removed function fails.
  - Batch curvature output changes: `run_batch` and `workflows.batch`
    defaulted `extended_curvature` to `True`, as did the Run Remote switch, so
    batch curvature (the curvature rows of `hair_analysis_per_image.csv`) came
    from the medial-axis skeleton and carried the five extra columns. It now
    uses the original method: the extra columns are gone and the values change
    to the published ones. The old batch values were not reproducible, because
    `medial_axis` breaks ties at random: on the synthetic test image (50 px
    window, 132 px/mm) `curv_mean_mean` came out between about 0.80 and 0.82
    from one run to the next, and is now 0.8024 on every run, the v0.3.1
    value. Batch curvature results produced before this change cannot be
    reproduced exactly and should be re-run. `workflows.curvature`,
    `curvature_seq` and the command line defaulted to off, so their default
    results are unchanged.
- **Per-sample batch aggregation** (`hair_analysis_per_sample.csv`); the batch
  pipeline now emits a single per-image table.

### Fixed
- **Curvature now reproduces the original published method (v0.3.1) whichever
  scikit-image is installed.** The ridge-detection
  step called `skimage.filters.frangi`, whose output changed after scikit-image
  0.16.2 (default `gamma` 15 → computed from the image, and changes to the
  Hessian computation), so the same fibermorph code gave different curvature on
  different scikit-image versions. Example: on the straight-hair demo image
  (`027_demo_nocurv`, 50 px window, 132 px/mm) mean curvature is 0.0526 mm⁻¹
  with scikit-image 0.16.2 but 0.173 mm⁻¹ with 0.26 (3.3×); on the curly demo
  image (`004_demo_curv`) mean curvature changes by 1.1%, median curvature by
  3.4% and length by 2.9%. `filter_curv` now uses
  `fibermorph.core.frangi_v016.frangi_v016`, a copy of the 0.16.2 filter
  (BSD-3-Clause, scikit-image copyright and license kept in the file), which
  matches scikit-image 0.16.2 to about 1e-16. **Curvature values differ from
  those produced by 0.3.x and 1.0.x releases or by the unreleased 2.0.0 code on newer
  scikit-image** (they now agree with the original published values).
  This now holds for every entry point, including `run_batch`,
  `workflows.batch` and the GUI: the two options that did not reproduce
  v0.3.1 (CLAHE and extended curvature) are removed, see **Removed**.
- **Whole-hair curvature mode and per-hair `test` output restored.** The
  refactor first released in 0.3.7 dropped two behaviors of the original `window_iter`
  (`fibermorph.core.curvature`): (1) with `window_size=None` (the CLI default
  when `--window_size` is omitted) it returned an empty table instead of fitting
  one circle to each hair; it now again fits one Taubin circle per hair, keeps
  hairs longer than 0.5 × resolution pixels, and returns `ID, curv_mean,
  curv_median, length_mean, length_median, hair_count`; (2) with `test=True` it
  returned the image summary instead of one row per hair (`curv_mean,
  curv_median, length`, or `curv, length` for whole hair), which broke the
  simulated-data validation (`fibermorph.demo.demo.validation_curv` /
  `dummy_curv`) that reads `length` and `curv_median` per hair. Whole-hair mode
  on an image with no hair above the minimum length returns `hair_count` 0 and
  NaN means rather than raising an error.
- **Section resolution unit mislabel** (`µm/px` where the code needs `px/µm`) in
  the GUI and docstrings — the cause of "empty mask" segmentation failures on
  correctly-focused images.
- US spelling throughout the GUI (analyze, fiber, color).
- **Uploads with the same filename were all measured as the last one.** The GUI
  saved each upload to a temporary path named after the uploaded file, so two
  uploads with the same name overwrote each other and both result rows measured
  the second file, even though the on-screen warning said each file is measured
  separately. Uploads are now saved under distinct generated names, and each is
  measured on its own; `source_file` (and the `ID` / `mask_filename` columns of
  cross-section results, the mask previews, the curvature tables and the error
  messages shown for a file) still show the uploaded filename.
- **`fibermorph --curvature --window_size` no longer crashes.** The values were
  read as text (the same bug is in the original v0.3.1 command line), so
  `--window_unit mm` failed with `TypeError: can't multiply sequence by non-int
  of type 'float'`, and `--window_size 50.0` with `--window_unit px` failed with
  `ValueError: invalid literal for int()`; only whole numbers of pixels such as
  `50` worked, by accident. `--window_size` is now read as numbers: one or more
  values (a sweep such as `--window_size 25 50 100`), or `none` for the whole
  hair, which is also the default when the option is left out. With
  `--window_unit px` each value must be a whole number (`50` and `50.0` both
  give 50); with `mm` it can be any number greater than 0 (`0.5`). A
  non-numeric or non-finite value, a fraction of a pixel with `px`, or `none`
  repeated or combined with numbers is reported as a usage error (exit code 2)
  instead of a traceback; zero, negative and over-long windows (more than
  1,000,000,000 pixels, the largest accepted) are covered under
  **Breaking Changes**. A window shorter than 10 pixels (for `mm`, after
  conversion with `--resolution_mm`) is not used as given: each hair is
  measured over its whole length in one window, a warning is logged, and the
  output is still named after the window you asked for (`..._WindowSize-0.001mm`).
  The values are checked whichever module is run. Output file names are
  unchanged (`..._WindowSize-50px`, `..._WindowSize-0.5mm`).
  `fibermorph.cli.main` and `parse_args` now accept an optional list of
  arguments (default: the command line).
- **Out-of-range numbers on the command line now give a usage message instead of
  a traceback.** These all ended in a traceback or an empty result: `--jobs 0`
  (joblib: `n_jobs == 0 in Parallel has no meaning`); `--resolution_mm` or
  `--resolution_mu` of 0, a negative number, `nan` or `inf` (`Resolution must be
  greater than 0.`, `cannot convert float NaN to integer`, or `OverflowError`; a
  zero or negative `--resolution_mm` also stopped `--section` and `--raw2gray`
  runs, which do not use it; a `nan` or `inf` `--resolution_mu` with
  `--section` ended in `KeyError: "None of ['ID'] are in the columns"` or in
  exit code 0 with a table that has no rows); `--maxsize 0`; and a `--minsize`
  larger than `--maxsize` (no section can match). They now exit with code 2
  before any image is read, whichever module is chosen, and the message names
  the option. The rules:
  `--jobs` must not be 0 (`-1` for every CPU still works), and a `--jobs` larger
  than the machine's CPU count is reduced to that count with a message (a huge
  value used to crash joblib with `OverflowError` or start thousands of worker
  processes); `--resolution_mm` and
  `--resolution_mu` must be finite and greater than 0, also after conversion
  from `mm_per_px` or `um_per_px`; `--minsize` must be 0 or more, `--maxsize`
  greater than 0, and `--minsize` no larger than `--maxsize`. A negative
  `--minsize`, which used to run as if it were 0, is refused too (see
  **Breaking Changes**). Not covered: a `--section` run whose limits are valid
  but match no section (for example `--minsize 400 --maxsize 500` on images
  with thinner hairs, or an absurdly large `--resolution_mu`) still ends in the
  same `KeyError`; that comes from the section workflow, which is not changed
  here.

### Security
- **Hosted visitors can no longer choose the SAM2 checkpoint path.** In the
  Cross-Section view's settings, the "SAM2 checkpoint path" text box is now shown
  only in local mode. In hosted mode the server's own checkpoint (the file named
  by `SAM2_CHECKPOINT`) is always used, and a caption says whether a
  checkpoint file was found (and that SAM2 also needs a GPU on the server), without
  showing the server path. Before, any visitor could type a path and the server
  would try to load that file as a model. The server's
  checkpoint path is not shown in any hosted view: the Run Remote view's
  "SAM2 checkpoint path" box, which only fills in the generated SBATCH script text
  and is never loaded by the server, now starts empty in hosted mode (in local mode
  it is still pre-filled), and the script uses `YOUR_SAM2_CHECKPOINT` there if the
  box is left blank. The first SAM2 model the server loads is kept for the life of
  the process, so restart the app after changing `SAM2_CHECKPOINT` or replacing the
  checkpoint file.
- **Uploaded filenames are no longer used to build paths on the server.** The
  GUI wrote each upload to `<temp dir>/<uploaded filename>`, so a crafted name
  (an absolute path, `..` segments, Windows `\` separators) could write outside the
  temporary directory. Uploads are now written as `upload_0001.<ext>`,
  `upload_0002.<ext>`, ... directly inside the temporary directory (the original
  extension is kept only if it is tif, tiff, png, jpg or jpeg); the uploaded
  filename is used only as a display label, reduced to its last path component.

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
