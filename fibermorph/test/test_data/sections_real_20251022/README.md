# Real fiber cross-section test scans (2025-10-22 batch)

Two representative scans from the lab's cross-section imaging batch, kept here to
verify segmentation and measurement on real data (not synthetic fixtures).

## Calibration

- **Resolution: 0.18 µm/pixel.**
- In fibermorph, `resolution_mu` is **pixels per µm**, so use
  **`resolution_mu = 1 / 0.18 ≈ 5.556`** (not the 4.25 default, which is
  Abhiraj's AFREU value and does not apply to these `12.5mag` scans).
- Scale-free metrics (eccentricity, solidity, circularity, aspect ratio, shape
  class) are calibration-independent; only the µm/µm² columns depend on it.

## What these files are

- Source: `.../YemkoPryor_Hub/Hair Weights/Microscope_Images/20251022/`
- Originals: 3648 × 5472, **RGB, uint8, ~60 MB each** (uncompressed 20 MP TIFF).
- Here: converted to **grayscale + zlib-compressed TIFF, ~10 MB each**.
  - Pixel dimensions are **unchanged**, so the 0.18 µm/pixel calibration is
    preserved exactly — these are shrunk in file size only, not resampled.
  - fibermorph reads grayscale anyway (`cv2.imread(..., IMREAD_GRAYSCALE)`), so
    dropping the redundant RGB channels is lossless for this pipeline.
- `.tif` extension is required — `utils.filesystem.list_images` only accepts
  `.tif`/`.tiff`.

## Why shrink at all

60 MB × a full batch is slow to upload to the Streamlit app and wasteful to
process. Grayscale + compression removes ~6× the bytes with **no** effect on
pixels or calibration. (If even smaller files are needed, the images can be
downsampled — but that scales the resolution: a 2× downsample makes it
0.36 µm/pixel, i.e. `resolution_mu ≈ 2.78`.)

## How to run

Point the standalone runner at this folder (currently in the session scratchpad):

```
python run_sections.py <this_folder> <output_folder> --resolution-mu 5.556
```

Outputs a `section_measurements.csv`, a QC overlay per image, and (with
`--compress`) grayscale copies.
