"""Make golden curvature references with the ORIGINAL fibermorph v0.3.1 code.

This script runs the curvature analysis of the published method (git tag
v0.3.1, November 2020) and saves its output as CSV files. The tests in
fibermorph/test/test_curvature_golden.py compare the current fibermorph code
against these files. Run it inside the paper-era Python environment, NOT the
environment fibermorph is developed in:

    Python 3.8.20, scikit-image 0.16.2, numpy 1.18.5, scipy 1.4.1,
    pandas 1.0.5, Pillow 7.2.0   (the versions pinned by v0.3.1)

The script loads fibermorph.py and _version.py of the v0.3.1 tag unmodified
and calls v0.3.1's ``curvature_seq`` twice per window setting: once with
test=True (one row per hair) and once with test=False (image summary), at
132 px/mm. Export the two files from the repository first (the tag must
exist locally; run ``git fetch --tags`` if it does not):

    mkdir -p /tmp/fibermorph_v031
    git show v0.3.1:fibermorph/fibermorph.py > /tmp/fibermorph_v031/fibermorph.py
    git show v0.3.1:fibermorph/_version.py   > /tmp/fibermorph_v031/_version.py

Then, with the paper-era Python (on Apple silicon: ``arch -x86_64 <env>/bin/python``):

    python make_curv_reference.py --v031-dir /tmp/fibermorph_v031 \
        --image synthetic_curv.png --out-dir reference_v031 \
        --windows 50px,none,0.5mm

``--windows`` is a comma-separated list; ``50px`` is a 50 pixel window,
``0.5mm`` a 0.5 mm window (converted with the resolution), ``none`` the
whole-hair mode. Output files are named
``<image stem>__window<setting>__perhair.csv`` and ``...__summary.csv``;
``<setting>`` is the window text as given (``50px``, ``none``, ``0.5mm``).
"""
import argparse
import importlib.util
import os
import sys
import tempfile
import types

import numpy as np
import pandas as pd
import skimage

RESOLUTION = 132  # pixels per mm


def load_v031(src_dir):
    """Import fibermorph.py from src_dir (with _version.py beside it). rawpy
    (RAW images) and demo (demo-data download code) are not used by
    curvature_seq, so they are stubbed."""
    sys.modules.setdefault("rawpy", types.ModuleType("rawpy"))
    sys.modules.setdefault("demo", types.ModuleType("demo"))
    spec = importlib.util.spec_from_file_location(
        "fibermorph_v031", os.path.join(src_dir, "fibermorph.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_window(text):
    """'50px' -> (50, 'px'); '0.5mm' -> (0.5, 'mm'); 'none' -> (None, 'px')."""
    if text == "none":
        return None, "px"
    if text.endswith("px"):
        return int(text[:-2]), "px"
    if text.endswith("mm"):
        return float(text[:-2]), "mm"
    raise ValueError("window must look like 50px, 0.5mm or none, got " + repr(text))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--v031-dir", required=True,
                        help="folder holding fibermorph.py and _version.py from tag v0.3.1")
    parser.add_argument("--image", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--windows", default="50px,none,0.5mm")
    args = parser.parse_args()

    if skimage.__version__ != "0.16.2":
        raise SystemExit("Needs scikit-image 0.16.2, found " + skimage.__version__)

    os.makedirs(args.out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.image))[0]
    fm = load_v031(args.v031_dir)

    for text in args.windows.split(","):
        window, unit = parse_window(text)
        for test, kind in ((True, "perhair"), (False, "summary")):
            with tempfile.TemporaryDirectory() as work_dir:
                df = fm.curvature_seq(
                    args.image, work_dir, RESOLUTION, window, unit,
                    False, test, False,
                )
            out = os.path.join(
                args.out_dir, "{}__window{}__{}.csv".format(stem, text, kind)
            )
            pd.DataFrame(df).to_csv(out, index=False)
            print("wrote", out, "(%d rows)" % len(df))

    print("python", sys.version.split()[0], "| scikit-image", skimage.__version__,
          "| numpy", np.__version__, "| pandas", pd.__version__)


if __name__ == "__main__":
    main()
