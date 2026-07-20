# Fibermorph Manuscript Analysis

Reproducible analysis notebooks and data for the hair cross-section morphology manuscript.

## Quick start

```bash
pip install "fibermorph[analysis]"
pip install notebook jupyterlab scipy scikit-learn
cd manuscript/analysis
jupyter lab
```

## Structure

```
manuscript/
  data/                         ← analysis-ready CSVs (no images required)
    shape_analysis_results.csv  ← 1,737 × 82, primary results
    shape_summary.csv           ← per-class summary
    outliers.csv                ← Mahalanobis outlier flags
    mirror_validation.csv       ← A/B mirror pair ranks
    hair_morphology_guided.csv  ← morphometrics + SAM2 confidence
  analysis/
    00_pipeline_overview.ipynb  ← yield, IoU distribution, ranking formula
    01_shape_features.ipynb     ← 82-feature space, class frequencies
    02_pca_morphospace.ipynb    ← scree, loadings, scatter, within/between spread
    03_outlier_analysis.ipynb   ← Mahalanobis distance, outlier PCA plot
    04_mirror_validation.ipynb  ← NN rank histogram, compression ratio
    05_shape_classification.ipynb ← KW tests, feature distributions by class
  _quarto.yml                   ← Quarto website configuration
  index.qmd                     ← landing page
  methods.qmd                   ← full Methods section with formulae
```

## Build the website locally

```bash
# Install Quarto: https://quarto.org/docs/get-started/
quarto render manuscript/
open manuscript/_site/index.html
```

The site is also deployed automatically to GitHub Pages on every push to `main`
that touches files under `manuscript/`.

## Mask ranking formula

The composite score used to select the best SAM2 candidate mask per image:

```
score = 0.40 × IoU_confidence + 0.35 × solidity + 0.25 × centrality
centrality = 1 − (dist_from_image_centre / max_possible_dist)
Acceptance filter: 30 µm ≤ major_axis_length ≤ 150 µm
```

See [`methods.qmd`](methods.qmd) for full documentation with equations.
