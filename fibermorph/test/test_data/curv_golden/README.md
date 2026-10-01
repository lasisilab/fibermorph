# Golden curvature references (original fibermorph v0.3.1)

The CSV files here hold the curvature output of the **original published
fibermorph method** (git tag `v0.3.1`, commit `c5aa520`, 21 Nov 2020). The tests
in `fibermorph/test/test_curvature_golden.py` run the current code on the same
images and require the same numbers (relative tolerance 1e-9). They guard against
the curvature results drifting again, for example because a newer scikit-image
changes `frangi()`.

## Contents

| Path | What it is |
|---|---|
| `synthetic_curv.png` | 1000 x 1000 8-bit synthetic image: dark arcs of several radii, a near-straight bowed line, a straight line, and one short arc. About 400 KB. |
| `make_synthetic_curv_image.py` | Draws `synthetic_curv.png` (numpy + Pillow only). |
| `reference_v031/` | v0.3.1 output for `synthetic_curv.png`: windows `50px`, `none` (whole hair) and `0.5mm`. |
| `reference_demo_v031/` | v0.3.1 output for the two lab demo images `004_demo_curv.tiff` (curly) and `027_demo_nocurv.tiff` (straight): windows `50px` and `none`. The TIFFs are **not** committed. |
| `make_curv_reference.py` | Produces the CSV files by running the unmodified v0.3.1 code. |

File names: `<image>__window<setting>__perhair.csv` (one row per hair, from
`curvature_seq(..., test=True)`) and `<image>__window<setting>__summary.csv`
(one row per image, from `test=False`). `<setting>` is `50px`, `none` or `0.5mm`.
Resolution is 132 px/mm in all cases. Columns:

* window sizes, per hair: `curv_mean, curv_median, length`
* window sizes, summary: `ID, curv_mean_mean, curv_mean_median, curv_median_mean, curv_median_median, length_mean, length_median, hair_count`
* whole hair (`none`), per hair: `curv, length`
* whole hair (`none`), summary: `ID, curv_mean, curv_median, length_mean, length_median, hair_count`

## How the references were made

Environment (scikit-image and scipy are the versions pinned by v0.3.1's
`environment.yml`; the rest are the closest builds that install on current
hardware, run as x86_64 under Rosetta):

* Python 3.8.20
* scikit-image 0.16.2
* numpy 1.18.5
* scipy 1.4.1
* pandas 1.0.5
* Pillow 7.2.0

(`environment.yml` of v0.3.1 pins Python 3.6.10, numpy 1.18.1, pandas 1.0.1 and
Pillow 7.0.0. The current code, on Python 3.12, numpy 2.5, scipy 1.18,
pandas 2.3 and scikit-image 0.26, reproduces these files to about 1e-14
relative, so the small differences in numpy, pandas and Pillow versions do not
matter.)

1. Export the two v0.3.1 source files (the tag must exist locally; run
   `git fetch --tags` if it does not):

   ```
   mkdir -p /tmp/fibermorph_v031
   git show v0.3.1:fibermorph/fibermorph.py > /tmp/fibermorph_v031/fibermorph.py
   git show v0.3.1:fibermorph/_version.py   > /tmp/fibermorph_v031/_version.py
   ```

2. Run the script with the paper-era Python, from this directory:

   ```
   # synthetic image
   python make_curv_reference.py --v031-dir /tmp/fibermorph_v031 \
       --image synthetic_curv.png --out-dir reference_v031 \
       --windows 50px,none,0.5mm

   # lab demo images (download them first, see below)
   python make_curv_reference.py --v031-dir /tmp/fibermorph_v031 \
       --image 004_demo_curv.tiff --out-dir reference_demo_v031 --windows 50px,none
   python make_curv_reference.py --v031-dir /tmp/fibermorph_v031 \
       --image 027_demo_nocurv.tiff --out-dir reference_demo_v031 --windows 50px,none
   ```

   On Apple silicon prefix the Python command with `arch -x86_64`. The script
   loads v0.3.1's `fibermorph.py` unmodified (stubbing only the unused `rawpy`
   and `demo` imports) and calls its `curvature_seq` with `test=True` and
   `test=False`. It refuses to run unless scikit-image is 0.16.2.

The PNG was checked to decode to identical pixels under the paper-era
environment (Pillow 7.2.0) and a current one (Pillow 12.3.0); sha256 of the
decoded array: `2d1a7e9a6d452654f1b439dd281f0c8ad9b763923146e85e89fed81c09992cec`.

## Demo images

`004_demo_curv.tiff` and `027_demo_nocurv.tiff` come from the lab's public demo
data: `https://github.com/tinalasisi/fibermorph_DemoData/raw/master/test_input/curv/`.
The online tests download them when they run (about 6 MB in total, each image
once per test run) and skip if the download fails. To run without downloading,
put the two files in a folder and set `FIBERMORPH_DEMO_CURV_DIR` to that folder.

## Notes

* `curvature_seq` has a single path, the v0.3.1 method, so the references
  cover everything it can produce; there are no analysis options to vary.
* A hair counts for a window setting only if its skeleton is longer than the
  window (px) or 0.5 (mm), and for the whole-hair mode only if longer than
  0.5 x resolution pixels; this is why the number of rows differs between
  settings for the same image.
* If the references must be regenerated (they should not change), review the
  diff: any change means the analysis, not the references, moved.
