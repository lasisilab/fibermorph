[![Test](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml/badge.svg)](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml) [![PyPI version](https://img.shields.io/pypi/v/fibermorph.svg)](https://pypi.org/project/fibermorph/)


# fibermorph

**Interactive toolkit for analyzing fiber morphology**

fibermorph provides powerful image analysis tools for studying fiber curvature and cross-sections, with both an intuitive **graphical interface** and a command-line interface for advanced users.

### What's new in v2.0
- **Streamlit GUI** with a sidebar console: **Cross-Section**, **Curvature**, **Run Local**, and **Run Remote** views
- **Per-fragment curvature** in the GUI — each fiber fragment's length and curvature, plus per-image summaries and distribution histograms
- **Flexible resolution units** — enter px/µm or µm/px (px/mm or mm/px) in the GUI or CLI and it converts for you
- **Run locally for large images** — `fibermorph-gui` raises the upload cap and adds a "Folder on disk" input (read images straight from disk)
- **SAM2 GPU segmentation** for cross-sections (optional; falls back to watershed on CPU), with extended shape features (`--extended-features`)
- **CLAHE preprocessing** for curvature images with uneven illumination (`--use-clahe`)
- **SBATCH script generation** from the GUI's Run Remote view (build & download — you submit it yourself)
- **GPU Docker target** for container deployment with SAM2

## 🚀 Quick Start with the GUI (Recommended)

The easiest way to use fibermorph is through the interactive web interface:

```bash
# Create a conda environment with Python 3.11
conda create -n fibermorph_env python=3.11
conda activate fibermorph_env

# Install fibermorph with the GUI
pip install "fibermorph[gui]"

# Launch the interactive GUI
fibermorph-gui
```

The sidebar console has four views:
- **Cross-Section**: upload images, segment (SAM2 / watershed) and measure cross-section shape — results and mask previews appear inline
- **Curvature**: measure per-fragment length and curvature, with per-image summaries and distribution charts
- **Run Local**: how to run this same GUI on your own machine (no upload limit; read images straight from a folder)
- **Run Remote**: build a downloadable SBATCH script to run the CLI on an HPC cluster (it does not submit jobs for you)

> The hosted app is upload-only (500 MB per file). To analyze larger images, run it locally — see **Run locally from source** below.

## 📦 Installation

### Recommended: Conda + GUI

```bash
# Create environment (Python 3.10-3.12 supported)
conda create -n fibermorph_env python=3.11
conda activate fibermorph_env

# Install with GUI
pip install "fibermorph[gui]"
```

### Alternative: pip with virtual environment

```bash
python3.11 -m venv fibermorph_env
source fibermorph_env/bin/activate   # macOS/Linux
# fibermorph_env\Scripts\activate    # Windows
pip install "fibermorph[gui]"
```

**Supported Python versions:** 3.10, 3.11, 3.12. Python 3.11 is recommended.

### Optional extras

```bash
pip install "fibermorph[raw]"        # RAW image conversion (rawpy)
pip install "fibermorph[viz]"        # matplotlib + seaborn visualization helpers
pip install "fibermorph[gui]"        # Streamlit GUI (recommended)
pip install "fibermorph[raw,gui]"    # combine extras
```

### SAM2 GPU segmentation (optional)

SAM2 is not on PyPI and must be installed separately. It is only required if you use `--use-sam2`.

```bash
pip install git+https://github.com/facebookresearch/segment-anything-2

# Download a checkpoint (tiny model is fastest):
mkdir -p fibermorph/checkpoints
wget -O fibermorph/checkpoints/sam2.1_hiera_tiny.pt \
  https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
```

Without SAM2, fibermorph automatically falls back to the watershed segmentation path — no crash, no manual intervention required.

## 💻 Run locally from source

The published PyPI package can lag behind the latest code. To run the **current**
code — including everything in the GUI's **Run Local** view — install the repo
itself in editable mode:

```bash
git clone https://github.com/lasisilab/fibermorph.git
cd fibermorph
python3.12 -m venv .venv && source .venv/bin/activate   # Python 3.10–3.12
pip install -e '.[gui]'        # editable install of this working copy
fibermorph-gui                 # opens the local GUI at http://localhost:8501
```

Launched this way, the GUI runs on your own machine with the upload cap raised to
**5 GB** and a **"Folder on disk"** input on the Cross-Section and Curvature views,
so you can analyze images that are too large to upload to the hosted app. (On a
machine's first-ever Streamlit run it may briefly ask for an email — the launcher
skips that for you.)

The CLI works from the same checkout too: `fibermorph --help`.

## 🐳 Docker

### CPU-only (default)

```bash
docker build --target cpu -t fibermorph:cpu .
docker run -p 7860:7860 fibermorph:cpu
# Open http://localhost:7860 in your browser
```

### GPU (SAM2 + CUDA)

```bash
docker build --target gpu -t fibermorph:gpu .
docker run --gpus all -p 7860:7860 fibermorph:gpu
```

## 🖥️ Command Line Interface

### Quick test with demo data

```bash
fibermorph --demo_real_curv    --output_directory ~/fibermorph_demo_curv
fibermorph --demo_real_section --output_directory ~/fibermorph_demo_section
```

### Curvature analysis

```bash
# Basic (same as v1):
fibermorph --curvature \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --resolution_mm 132 \
  --jobs 4

# With new v2 options:
fibermorph --curvature \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --resolution_mm 132 \
  --use-clahe \
  --extended-curvature \
  --jobs 4
```

New curvature flags:
- `--use-clahe` — CLAHE contrast enhancement before the Frangi ridge filter
- `--extended-curvature` — adds `curl_index`, `curl_index_std`, `wave_count`, `wave_count_per_mm`, and `length_total` columns (experimental — from the v2 fork; validate before relying on them)
- `--resolution_mm_units {px_per_mm,mm_per_px}` — interpret `--resolution_mm` as pixels-per-mm (default) or mm-per-pixel

### Section analysis

```bash
# Basic (same as v1):
fibermorph --section \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --resolution_mu 4.25 \
  --minsize 20 --maxsize 150 \
  --jobs 4

# With SAM2 GPU segmentation and extended features:
fibermorph --section \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --resolution_mu 4.25 \
  --use-sam2 --sam2-checkpoint fibermorph/checkpoints/sam2.1_hiera_tiny.pt \
  --extended-features \
  --jobs 4
```

New section flags:
- `--use-sam2` — enable SAM2 segmentation (requires GPU + SAM2 installed; falls back to watershed automatically)
- `--sam2-checkpoint PATH` — path to SAM2 `.pt` weights file
- `--sam2-cfg PATH` — path to SAM2 model config YAML (optional; uses bundled default)
- `--extended-features` — adds EFD (40 coefficients), Hu moments (7), radial profile (7 metrics), `shape_class`
- `--resolution_mu_units {px_per_um,um_per_px}` — interpret `--resolution_mu` as pixels-per-micron (default) or microns-per-pixel (e.g. a 0.18 scale)

## Install the package

1. After having activated your new virtual environment, you can simply run `pip install fibermorph`.
	You can find the latest release [here](https://github.com/lasisilab/fibermorph/) on this GitHub page and on the [fibermorph PyPI page](https://pypi.org/project/fibermorph/).
2. You have successfully installed fibermorph.
	The package is now ready for use. Enter `fibermorph -h` or `fibermorph --help` to see all the flags. You can keep reading to try out the demos and read instructions on the various modules within the package.

## Demo data
Before using this on any of your own data, it's recommended that you test that you test whether fibermorph is working properly on your machine. There are a few `demo` modules you can use to check whether fibermorph is running correctly.

### Testing with real data
You can test both the curvature and section modules with real data that is downloaded automatically when you run the `--demo_real` modules.

In both cases, all you need to do is specify a folder path where the images and results can be created with `---output_directory` or `-o`. This folder can be existing, but you can also establish a new folder by including it in the new path.

Both modules will download the demo data into a new folder `tmpdata` within the path you gave. Then, fibermorph will run the curvature or section analysis, and the results  will be saved in a new folder `results_cache` at this same location. It is recommended that you specify a path with a new folder name to keep everything organized.

#### Testing curvature analysis
`  --demo_real_curv`

This flag will run  a demo of fibermorph curvature analysis with real data. You will need to provide a folder for the demo data to be downloaded.

To run the demo, you will input something like:
`fibermorph --demo_real_curv --output_directory /Users/<UserName>/<ExistingPath>/<NewFolderName`

#### Testing section analysis
`  --demo_real_section`

This flag will run  a demo of fibermorph section analysis with real data. You will need to provide a folder for the demo data to be downloaded.

To run the demo, you will input something like:
`fibermorph --demo_real_section --output_directory /Users/<UserName>/<ExistingPath>/<NewFolderName`

### Curvature
To calculate curvature from grayscale TIFF images of fibers, the flag `--curvature` is used with the following flags in addition to input and output directories:
```
--resolution_mm       	Integer. Number of pixels per mm for
						curvature analysis.
						Default is 132.
--window_size  [ ...] 	Float or integer or None. Desired size for
						window of measurement
						for curvature analysis in pixels or mm (given
						the flag --window_unit). If nothing is entered, the default
						is None and the entire fiber will be used to for the curve fitting."
--window_unit {px,mm}	String. Unit of measurement for window of
						measurement for curvature
                      	analysis. Can be 'px' (pixels) or 'mm'. Default is 'px'.
-W, --within_element  	Boolean. Default is False. Will create
						an additional directory with
                      	spreadsheets of raw curvature measurements for each fiber if the
                      	--within_element flag is included.
-s, --save_image      	Default is False. Will save intermediate
						curvature/section processing images if
						--save_image flag is included.

```

So, to run a curvature analysis, you would enter e.g.
```
fibermorph --curvature --input_directory /Users/<UserName>/<ImageFolderPath> --output_directory /Users/<UserName>/<ExistingPath>/ --window_size 0.5 --window_unit mm --resolution_mm 132 --save_image --within_element --jobs 2
```

### Section
To calculate cross-sectional properties from grayscale TIFF images of fibers, the flag `--section` is used with the following flags:
```
--resolution_mu       Float. Number of pixels per micron for section analysis. Default is 4.25.
--minsize             Integer. Minimum diameter in microns for sections. Default is 20.
--maxsize             Integer. Maximum diameter in microns for sections. Default is 150.

```

An example command would be:
```
fibermorph --section --input_directory /Users/<UserName>/<ImageFolderPath> --output_directory /Users/<UserName>/<ExistingPath>/ --minsize 20 --maxsize 150 --resolution_mu 4.25 --jobs 2
```


### Converting raw images to grayscale TIFF
This package features an additional auxiliary module to convert raw images to grayscale TIFF files if necessary: `--raw2gray`

In addition to the input and output directories, the module needs the user to specify what file extension it should be looking for.

```
--file_extension      Optional. String. Extension of input files to use in input_directory when
                      using raw2gray function. Default is .RW2.

```

A user could enter, for example:
```
fibermorph --raw2gray --input_directory /Users/<UserName>/<ImageFolderPath> --output_directory /Users/<UserName>/<ExistingPath>/<NewFolderName> --file_extension .RW2 --jobs 4
```
