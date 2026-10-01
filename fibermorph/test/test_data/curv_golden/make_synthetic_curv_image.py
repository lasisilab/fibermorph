"""Draw the synthetic curvature image used by the golden tests.

Writes synthetic_curv.png next to this script: a 1000 x 1000 8-bit grayscale
image with dark hair-like ridges on a light, slightly noisy background. It has
dark arcs of several radii, a near-straight line, and one short arc that ends
up shorter than the whole-hair minimum length. The PNG itself is the committed
fixture; this script documents how it was drawn and needs only numpy and
Pillow:

    python make_synthetic_curv_image.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 1000


def arc_darkness(rows, cols, center_r, center_c, radius, start_deg, end_deg, sigma, peak):
    """Gaussian-profile dark ridge along a circular arc (angles in degrees)."""
    dr = rows - center_r
    dc = cols - center_c
    dist = np.abs(np.hypot(dr, dc) - radius)
    ang = np.degrees(np.arctan2(dr, dc)) % 360.0
    start, end = start_deg % 360.0, end_deg % 360.0
    if start <= end:
        inside = (ang >= start) & (ang <= end)
    else:
        inside = (ang >= start) | (ang <= end)
    return np.where(inside, peak * np.exp(-(dist ** 2) / (2 * sigma ** 2)), 0.0)


def line_darkness(rows, cols, r0, c0, r1, c1, sigma, peak):
    """Gaussian-profile dark ridge along a straight segment."""
    vr, vc = r1 - r0, c1 - c0
    length_sq = vr * vr + vc * vc
    t = np.clip(((rows - r0) * vr + (cols - c0) * vc) / length_sq, 0.0, 1.0)
    dist = np.hypot(rows - (r0 + t * vr), cols - (c0 + t * vc))
    return peak * np.exp(-(dist ** 2) / (2 * sigma ** 2))


def make_image():
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    dark = np.zeros((SIZE, SIZE))

    # (center_row, center_col, radius_px, start_deg, end_deg)
    arcs = [
        (250, 250, 100, 20, 300),    # tight curl, radius 100 px
        (250, 700, 160, 200, 340),   # radius 160 px
        (780, 300, 260, 250, 330),   # gentle arc, radius 260 px
        (900, 800, 60, 100, 170),    # short arc (about 63 px of skeleton)
    ]
    for cr, cc, rad, a0, a1 in arcs:
        dark = np.maximum(dark, arc_darkness(rows, cols, cr, cc, rad, a0, a1, 2.2, 170.0))

    # near-straight line with a very slight bow (very large radius)
    dark = np.maximum(dark, arc_darkness(rows, cols, 5600, 500, 4800, 266, 274, 2.2, 170.0))
    # straight line
    dark = np.maximum(dark, line_darkness(rows, cols, 560, 600, 600, 960, 2.2, 170.0))

    rng = np.random.RandomState(31)
    img = 228.0 - dark + rng.normal(0.0, 1.5, size=dark.shape)
    return np.clip(np.round(img), 0, 255).astype(np.uint8)


if __name__ == "__main__":
    Image.fromarray(make_image(), mode="L").save(
        os.path.join(HERE, "synthetic_curv.png"), optimize=True
    )
