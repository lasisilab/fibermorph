"""Hair cross-section shape feature extraction and classification.

Extracts from a binary mask (uint8 numpy array or PNG path):
  - Basic geometric: circularity, solidity, convexity, aspect_ratio, eccentricity
  - Radial distance profile: mean/std/min/max/CV, n_peaks, asymmetry_index
  - Elliptic Fourier Descriptors: 10 harmonics, power spectrum, deviation score
  - Hu moments: 7 log-transformed invariant moments

Classifies into one of 7 shape classes:
  Circular, Elliptical, Flattened, Tear-drop, Triangular, Multi-polar, Irregular

Originally developed for the AFREU hair cross-section dataset (SAM2 pipeline).
"""

import os

import cv2
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.signal import find_peaks
from skimage.measure import label, regionprops

RESOLUTION_MU   = 4.25
N_RADIAL_ANGLES = 360
N_EFD_HARMONICS = 10


def compute_efd(contour_pts: np.ndarray, n_harmonics: int = 10) -> dict:
    """Compute Elliptic Fourier Descriptors using piecewise-linear arc-length parameterization.

    Parameters
    ----------
    contour_pts : np.ndarray, shape (N, 2)  — ordered (x, y) points
    n_harmonics : int

    Returns
    -------
    dict with keys: efd_coeffs, efd_norm, harmonic_power, efd_deviation
    """
    pts = contour_pts.astype(np.float64)
    diffs = pts - np.roll(pts, 1, axis=0)
    seg_lengths = np.maximum(np.linalg.norm(diffs, axis=1), 1e-10)
    T = seg_lengths.sum()
    t_cumul = np.cumsum(seg_lengths)
    t_prev  = t_cumul - seg_lengths
    dx = diffs[:, 0]
    dy = diffs[:, 1]

    efd_coeffs = np.zeros((n_harmonics, 4))
    for n in range(1, n_harmonics + 1):
        two_pi_n_over_T = 2.0 * np.pi * n / T
        factor = T / (2.0 * n ** 2 * np.pi ** 2)
        phi_end   = two_pi_n_over_T * t_cumul
        phi_start = two_pi_n_over_T * t_prev
        cos_diff  = np.cos(phi_end) - np.cos(phi_start)
        sin_diff  = np.sin(phi_end) - np.sin(phi_start)
        dx_per_dt = dx / seg_lengths
        dy_per_dt = dy / seg_lengths
        efd_coeffs[n - 1] = [
            factor * np.sum(dx_per_dt * cos_diff),
            factor * np.sum(dx_per_dt * sin_diff),
            factor * np.sum(dy_per_dt * cos_diff),
            factor * np.sum(dy_per_dt * sin_diff),
        ]

    a1, b1, c1, d1 = efd_coeffs[0]
    theta1 = 0.5 * np.arctan2(
        2.0 * (a1 * b1 + c1 * d1),
        a1 ** 2 - b1 ** 2 + c1 ** 2 - d1 ** 2,
    )
    ct, st = np.cos(theta1), np.sin(theta1)
    size_factor = max(
        np.sqrt((a1 * ct + b1 * st) ** 2 + (c1 * ct + d1 * st) ** 2), 1e-10
    )
    efd_norm = efd_coeffs / size_factor

    harmonic_power = np.linalg.norm(efd_coeffs, axis=1)
    efd_deviation  = harmonic_power[1:].sum() / (harmonic_power[0] + 1e-10)

    return {
        "efd_coeffs":     efd_coeffs,
        "efd_norm":       efd_norm,
        "harmonic_power": harmonic_power,
        "efd_deviation":  efd_deviation,
    }


def compute_radial_profile(
    binary_img: np.ndarray,
    props,
    n_angles: int = 360,
    resolution_mu: float = RESOLUTION_MU,
) -> dict:
    """Cast rays from centroid and find boundary-crossing radius per angle.

    Parameters
    ----------
    binary_img    : 2D uint8 array (values 0 or 255)
    props         : skimage regionprops object
    n_angles      : number of rays
    resolution_mu : µm per pixel

    Returns
    -------
    dict with radial_mean_mu, radial_std_mu, radial_min_mu, radial_max_mu,
         radial_cv, n_radial_peaks, asymmetry_index
    """
    cy, cx = props.centroid
    max_r  = max(2, int(props.major_axis_length * 0.65))
    H, W   = binary_img.shape
    binary_f = (binary_img > 0).astype(np.float32)

    angles = np.linspace(0.0, 2.0 * np.pi, n_angles, endpoint=False)
    r_vals = np.arange(1, max_r + 1, dtype=np.float32)

    sin_a = np.sin(angles)[:, None]
    cos_a = np.cos(angles)[:, None]
    r_    = r_vals[None, :]

    ys = np.clip(cy + r_ * sin_a, 0, H - 1).ravel()
    xs = np.clip(cx + r_ * cos_a, 0, W - 1).ravel()

    vals = map_coordinates(binary_f, [ys, xs], order=0, mode="constant", cval=0.0)
    vals = vals.reshape(n_angles, max_r)

    radial_dists = np.empty(n_angles, dtype=np.float32)
    for i in range(n_angles):
        row   = vals[i]
        zeros = np.where(row == 0)[0]
        if len(zeros) == 0:
            radial_dists[i] = r_vals[-1]
        elif zeros[0] == 0:
            radial_dists[i] = r_vals[0]
        else:
            radial_dists[i] = r_vals[zeros[0] - 1]

    prominence_thresh = float(radial_dists.mean()) * 0.05
    min_sep = max(1, int(10 * n_angles / 360))
    peaks, _ = find_peaks(
        radial_dists.astype(np.float64),
        prominence=prominence_thresh,
        distance=min_sep,
    )

    orient = props.orientation
    proj   = cos_a.ravel() * (-np.sin(orient)) + sin_a.ravel() * np.cos(orient)
    side_A = radial_dists[proj >= 0]
    side_B = radial_dists[proj <  0]
    mean_total = float(radial_dists.mean()) + 1e-10
    if len(side_A) > 0 and len(side_B) > 0:
        asymmetry_index = abs(float(side_A.mean()) - float(side_B.mean())) / mean_total
    else:
        asymmetry_index = 0.0

    rm = resolution_mu
    return {
        "radial_mean_mu":  float(radial_dists.mean()) * rm,
        "radial_std_mu":   float(radial_dists.std())  * rm,
        "radial_min_mu":   float(radial_dists.min())  * rm,
        "radial_max_mu":   float(radial_dists.max())  * rm,
        "radial_cv":       float(radial_dists.std()) / (float(radial_dists.mean()) + 1e-10),
        "n_radial_peaks":  int(len(peaks)),
        "asymmetry_index": float(asymmetry_index),
    }


def extract_features_from_array(
    mask_array: np.ndarray,
    n_angles: int         = N_RADIAL_ANGLES,
    n_harmonics: int      = N_EFD_HARMONICS,
    resolution_mu: float  = RESOLUTION_MU,
    source_name: str      = "",
) -> dict | None:
    """Extract all shape features from a 2D uint8 binary mask array (values 0/255).

    Returns None if the mask is empty or the contour area is less than 100 px².
    """
    img = mask_array
    if img is None or img.max() == 0:
        return None

    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)

    area_px = cv2.contourArea(contour)
    if area_px < 100:
        return None

    perimeter_px = cv2.arcLength(contour, True)
    hull         = cv2.convexHull(contour)
    hull_area_px = cv2.contourArea(hull)
    hull_peri_px = cv2.arcLength(hull, True)

    circularity = 4.0 * np.pi * area_px / (perimeter_px ** 2 + 1e-10)
    solidity    = area_px / (hull_area_px + 1e-10)
    convexity   = hull_peri_px / (perimeter_px + 1e-10)

    M      = cv2.moments(contour)
    hu     = cv2.HuMoments(M).flatten()
    hu_log = np.array([-np.sign(h) * np.log10(abs(h) + 1e-30) for h in hu])

    labeled = label(img > 0)
    rp_list = regionprops(labeled)
    if not rp_list:
        return None
    props = rp_list[0]

    aspect_ratio    = props.major_axis_length / (props.minor_axis_length + 1e-10)
    eccentricity    = props.eccentricity
    orientation_deg = float(np.degrees(props.orientation))

    rad = compute_radial_profile(img, props, n_angles, resolution_mu)
    pts = contour[:, 0, :].astype(np.float64)
    efd = compute_efd(pts, n_harmonics)

    feat: dict = {
        "mask_filename":   source_name,
        "area_mu2":        area_px / (resolution_mu ** 2),
        "perimeter_mu":    perimeter_px / resolution_mu,
        "circularity":     float(circularity),
        "solidity":        float(solidity),
        "convexity":       float(convexity),
        "aspect_ratio":    float(aspect_ratio),
        "eccentricity":    float(eccentricity),
        "orientation_deg": orientation_deg,
    }
    feat.update(rad)

    for i, v in enumerate(hu_log, start=1):
        feat[f"hu{i}"] = float(v)

    norm = efd["efd_norm"]
    for h in range(n_harmonics):
        feat[f"efd_a{h+1}"] = float(norm[h, 0])
        feat[f"efd_b{h+1}"] = float(norm[h, 1])
        feat[f"efd_c{h+1}"] = float(norm[h, 2])
        feat[f"efd_d{h+1}"] = float(norm[h, 3])

    power = efd["harmonic_power"]
    for h in range(n_harmonics):
        feat[f"efd_power_h{h+1}"] = float(power[h])

    feat["efd_deviation"] = float(efd["efd_deviation"])
    return feat


def extract_features(
    mask_path: str,
    n_angles: int        = N_RADIAL_ANGLES,
    n_harmonics: int     = N_EFD_HARMONICS,
    resolution_mu: float = RESOLUTION_MU,
) -> dict | None:
    """Load a mask PNG from disk and extract all shape features. Returns None on failure."""
    img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    return extract_features_from_array(
        img, n_angles, n_harmonics, resolution_mu,
        source_name=os.path.basename(mask_path),
    )


def classify_shape(feat: dict, debug: bool = False) -> str:
    """Rule-based shape classification (ordered priority; first match wins).

    Classes (in priority order):
      Multi-polar, Triangular, Flattened, Irregular, Tear-drop, Circular, Elliptical
    """
    circ  = feat["circularity"]
    solid = feat["solidity"]
    ar    = feat["aspect_ratio"]
    ecc   = feat["eccentricity"]
    n_pk  = feat["n_radial_peaks"]
    asym  = feat["asymmetry_index"]

    if solid < 0.82 and n_pk > 3:
        if debug: print("  → Multi-polar")
        return "Multi-polar"

    if n_pk == 3 and solid < 0.95 and circ < 0.78:
        if debug: print("  → Triangular")
        return "Triangular"

    if ar >= 2.5 or (ar > 2.0 and ecc > 0.88):
        if debug: print("  → Flattened")
        return "Flattened"

    if circ < 0.60:
        if debug: print("  → Irregular")
        return "Irregular"

    if asym > 0.15 and 0.55 <= circ < 0.80 and 1.1 <= ar < 2.0:
        if debug: print("  → Tear-drop")
        return "Tear-drop"

    if circ > 0.85 and ar < 1.3:
        if debug: print("  → Circular")
        return "Circular"

    if circ >= 0.72 and 1.3 <= ar < 2.5:
        if debug: print("  → Elliptical")
        return "Elliptical"

    if debug: print("  → Irregular (default)")
    return "Irregular"
