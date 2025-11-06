[![Test](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml/badge.svg)](https://github.com/lasisilab/fibermorph/actions/workflows/test.yaml) [![PyPI version](https://img.shields.io/pypi/v/fibermorph.svg)](https://pypi.org/project/fibermorph/)


# fibermorph

**Interactive toolkit for analyzing hair fiber morphology**

fibermorph provides powerful image analysis tools for studying hair curvature and cross-sections, with both an intuitive **graphical interface** and a command-line interface for advanced users.

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

This opens an interactive web interface where you can:
- 📤 **Upload images**: Single or multiple TIFF files, or provide a URL to download
- 🔬 **Choose analysis type**: Curvature or Section analysis  
- ⚙️ **Configure parameters**: Adjust settings with interactive controls
- 💾 **Download results**: Get CSV summary data and ZIP file with all analysis outputs

**✨ Try it online**: [https://fibermorph.streamlit.app/](https://fibermorph.streamlit.app/)

## 📦 Installation

### Recommended: Conda + GUI

```bash
# Create environment (Python 3.10-3.13 supported)
conda create -n fibermorph_env python=3.11
conda activate fibermorph_env

# Install with GUI
pip install "fibermorph[gui]"
```

### Alternative: pip with virtual environment

```bash
# Create virtual environment
python3.11 -m venv fibermorph_env

# Activate the environment
# On macOS/Linux:
source fibermorph_env/bin/activate
# On Windows:
fibermorph_env\Scripts\activate

# Install fibermorph with GUI
pip install "fibermorph[gui]"
```

**Supported Python versions:** 3.10, 3.11, 3.12, 3.13. We recommend Python 3.11 for the best compatibility.

### Optional extras

```bash
pip install "fibermorph[raw]"    # enable RAW image conversion via rawpy
pip install "fibermorph[viz]"    # install matplotlib-based visualization helpers
pip install "fibermorph[gui]"    # install Streamlit GUI (recommended!)
```

Extras can be combined, e.g. `pip install "fibermorph[raw,viz,gui]"`.

## 🖥️ Command Line Interface (Advanced Users)

For automation, scripting, and batch processing, fibermorph provides a powerful CLI:

### Quick test with demo data

```bash
fibermorph --demo_real_curv --output_directory ~/fibermorph_demo_curv
fibermorph --demo_real_section --output_directory ~/fibermorph_demo_section
```

### Analyze your own data

**Curvature analysis:**
```bash
fibermorph --curvature \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --resolution_mm 132 \
  --jobs 2
```

**Section analysis:**
```bash
fibermorph --section \
  --input_directory /path/to/images \
  --output_directory /path/to/results \
  --minsize 30 \
  --maxsize 180 \
  --resolution_mu 4.25 \
  --jobs 2
```

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
