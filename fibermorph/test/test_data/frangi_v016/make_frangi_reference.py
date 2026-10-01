"""Generate the reference data for fibermorph/test/test_frangi_v016.py.

Run this with scikit-image 0.16.2 (the version used by the published fibermorph
v0.3.1 method), NOT with the version installed for fibermorph itself:

    arch -x86_64 <paper-era env>/bin/python make_frangi_reference.py

The paper-era environment used for the committed files was Python 3.8.20,
scikit-image 0.16.2, numpy 1.18.5, scipy 1.4.1. The script refuses to run with
any other scikit-image version.

It writes, next to this script:
    input_uint8.npy          deterministic 8-bit test image (64 x 96)
    ref_default.npy          skimage.filters.frangi(input_uint8)
    ref_float64.npy          skimage.filters.frangi(input_uint8 / 255.0)
    ref_white_sigmas.npy     skimage.filters.frangi(input_uint8, sigmas=[1, 2, 3.5],
                                                    black_ridges=False)
"""
import os

import numpy as np
import skimage
import skimage.filters

HERE = os.path.dirname(os.path.abspath(__file__))


def make_input():
    """Light background with dark ridges: a curved arc cut by the border, a
    straight diagonal line, a short thick segment, and mild noise."""
    rows, cols = np.mgrid[0:64, 0:96].astype(float)
    darkness = np.zeros((64, 96))

    # arc of a circle centered near the left border, radius 30
    dist_circle = np.abs(np.hypot(rows - 30.0, cols - 8.0) - 30.0)
    darkness += 170.0 * np.exp(-(dist_circle ** 2) / (2 * 1.5 ** 2))

    # near-straight diagonal line (distance from the line x - 2y + 10 = 0)
    dist_line = np.abs(cols - 2.0 * rows + 10.0) / np.sqrt(5.0)
    darkness += 150.0 * np.exp(-(dist_line ** 2) / (2 * 1.2 ** 2))

    # short, thicker segment touching the bottom border
    dist_seg = np.abs(cols - 80.0)
    darkness += np.where(rows > 40, 120.0 * np.exp(-(dist_seg ** 2) / (2 * 2.5 ** 2)), 0.0)

    rng = np.random.RandomState(20201117)
    img = 215.0 - darkness + rng.normal(0.0, 3.0, size=darkness.shape)
    return np.clip(np.round(img), 0, 255).astype(np.uint8)


def main():
    if skimage.__version__ != "0.16.2":
        raise SystemExit(f"Needs scikit-image 0.16.2, found {skimage.__version__}")

    img = make_input()
    np.save(os.path.join(HERE, "input_uint8.npy"), img)
    np.save(os.path.join(HERE, "ref_default.npy"), skimage.filters.frangi(img))
    np.save(os.path.join(HERE, "ref_float64.npy"), skimage.filters.frangi(img / 255.0))
    np.save(
        os.path.join(HERE, "ref_white_sigmas.npy"),
        skimage.filters.frangi(img, sigmas=[1, 2, 3.5], black_ridges=False),
    )
    print("scikit-image", skimage.__version__, "numpy", np.__version__)
    print("input", img.shape, img.dtype, "min/max", img.min(), img.max())


if __name__ == "__main__":
    main()
