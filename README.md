---
title: fibermorph
emoji: 🧬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
python_version: 3.11
fullWidth: true
pinned: false
short_description: Interactive toolkit for analyzing hair fiber morphology
---

[![Test](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml/badge.svg)](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml) [![PyPI version](https://img.shields.io/pypi/v/fibermorph.svg)](https://pypi.org/project/fibermorph/)


# fibermorph

**Interactive toolkit for analyzing hair fiber morphology**

fibermorph provides powerful image analysis tools for studying hair curvature and cross-sections, with both an intuitive **graphical interface** and a command-line interface for advanced users.

### What's new in v2.0
- **SAM2 GPU segmentation** for cross-sections (optional; falls back to watershed on CPU)
- **EFD + Hu moments + radial profile + shape classification** for cross-sections (`--extended-features`)
- **Curl index, wave count, fiber diameter** from medial-axis skeleton (`--extended-curvature`)
- **CLAHE preprocessing** for curvature images with uneven illumination (`--use-clahe`)
- **5-tab Streamlit GUI**: Quick Test, Segmentation Preview, Batch (Cluster), Submit & Monitor, Results
- **SLURM SBATCH script generation** directly from the GUI
- **Batch pipeline** with per-sample aggregation (`hair_analysis_per_image.csv` + `hair_analysis_per_sample.csv`)
- **18 publication-ready visualization figures**
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

The 5-tab interface provides:
- **Quick Test**: upload images and run analysis immediately (no SLURM needed)
- **Segmentation**: review input/mask/overlay for cross-section images
- **Batch (Cluster)**: configure settings and generate an SBATCH script
- **Submit & Monitor**: submit the script and watch live job status
- **Results**: load CSVs and explore 18 publication-ready figures

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
- `--use-clahe` — CLAHE contrast enhancement before Frangi ridge filter
- `--extended-curvature` — adds `curl_index`, `wave_count`, `diameter_mean_mu`, `curv_std`, `curv_cv`, `curv_iqr` columns

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
To calculate curvature from grayscale TIFF images of hair fibers, the flag `--curvature` is used with the following flags in addition to input and output directories:
```
--resolution_mm       	Integer. Number of pixels per mm for
						curvature analysis.
						Default is 132.
--window_size  [ ...] 	Float or integer or None. Desired size for
						window of measurement
						for curvature analysis in pixels or mm (given
						the flag --window_unit). If nothing is entered, the default
						is None and the entire hair will be used to for the curve fitting."
--window_unit {px,mm}	String. Unit of measurement for window of
						measurement for curvature
                      	analysis. Can be 'px' (pixels) or 'mm'. Default is 'px'.
-W, --within_element  	Boolean. Default is False. Will create
						an additional directory with
                      	spreadsheets of raw curvature measurements for each hair if the
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
To calculate cross-sectional properties from grayscale TIFF images of hair fibers, the flag `--section` is used with the following flags:
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
