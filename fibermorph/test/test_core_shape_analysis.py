"""Unit tests for core.shape_analysis module."""

import numpy as np
import pytest
from skimage import draw as sk_draw

from fibermorph.core.shape_analysis import (
    compute_efd,
    compute_radial_profile,
    extract_features_from_array,
    classify_shape,
)


def _circle_contour(radius: int = 40, n_pts: int = 200) -> np.ndarray:
    """Return (n_pts, 2) contour points for a circle."""
    theta = np.linspace(0, 2 * np.pi, n_pts, endpoint=False)
    cx = radius * np.cos(theta)
    cy = radius * np.sin(theta)
    return np.column_stack([cx, cy])


def _circle_mask(size: int = 120, radius: int = 40) -> np.ndarray:
    """Return a uint8 binary mask with a filled circle."""
    mask = np.zeros((size, size), dtype=np.uint8)
    rr, cc = sk_draw.disk((size // 2, size // 2), radius, shape=mask.shape)
    mask[rr, cc] = 255
    return mask


def _ellipse_mask(size: int = 120, r_row: int = 50, r_col: int = 25) -> np.ndarray:
    """Return a uint8 binary mask with a filled ellipse."""
    mask = np.zeros((size, size), dtype=np.uint8)
    rr, cc = sk_draw.ellipse(size // 2, size // 2, r_row, r_col, shape=mask.shape)
    mask[rr, cc] = 255
    return mask


# ─────────────────────────────────────────────
# compute_efd
# ─────────────────────────────────────────────
class TestComputeEFD:
    def test_returns_array_of_correct_shape(self):
        contour = _circle_contour()
        efd = compute_efd(contour, n_harmonics=10)
        assert isinstance(efd, np.ndarray)
        assert efd.shape == (10, 4)

    def test_different_harmonics(self):
        contour = _circle_contour()
        for n in [5, 10, 20]:
            efd = compute_efd(contour, n_harmonics=n)
            assert efd.shape[0] == n

    def test_circle_has_dominant_first_harmonic(self):
        contour = _circle_contour(radius=40, n_pts=360)
        efd = compute_efd(contour, n_harmonics=10)
        first_mag = np.sqrt(efd[0, 0] ** 2 + efd[0, 1] ** 2 +
                            efd[0, 2] ** 2 + efd[0, 3] ** 2)
        higher_mags = [
            np.sqrt(efd[k, 0] ** 2 + efd[k, 1] ** 2 +
                    efd[k, 2] ** 2 + efd[k, 3] ** 2)
            for k in range(1, 10)
        ]
        assert first_mag > max(higher_mags)

    def test_returns_finite_values(self):
        contour = _circle_contour()
        efd = compute_efd(contour, n_harmonics=10)
        assert np.all(np.isfinite(efd))


# ─────────────────────────────────────────────
# compute_radial_profile
# ─────────────────────────────────────────────
class TestComputeRadialProfile:
    def test_returns_dict_with_expected_keys(self):
        mask = _circle_mask()
        from skimage.measure import regionprops, label
        labeled = label(mask)
        props = regionprops(labeled)[0]
        result = compute_radial_profile(mask, props, n_angles=36, resolution_mu=4.25)
        expected = {
            "radius_mean_mu", "radius_std_mu", "radius_min_mu",
            "radius_max_mu", "radius_cv", "radius_range_mu", "asymmetry_index",
        }
        assert expected.issubset(set(result.keys()))

    def test_circle_has_low_asymmetry(self):
        mask = _circle_mask(radius=40)
        from skimage.measure import regionprops, label
        props = regionprops(label(mask))[0]
        result = compute_radial_profile(mask, props, n_angles=36, resolution_mu=1.0)
        assert result["asymmetry_index"] < 0.2

    def test_ellipse_has_higher_radius_range(self):
        circle_mask = _circle_mask(radius=30)
        ellipse_m   = _ellipse_mask(r_row=50, r_col=20)
        from skimage.measure import regionprops, label
        c_props = regionprops(label(circle_mask))[0]
        e_props = regionprops(label(ellipse_m))[0]
        c_res = compute_radial_profile(circle_mask, c_props, n_angles=36, resolution_mu=1.0)
        e_res = compute_radial_profile(ellipse_m,   e_props, n_angles=36, resolution_mu=1.0)
        assert e_res["radius_range_mu"] > c_res["radius_range_mu"]


# ─────────────────────────────────────────────
# extract_features_from_array
# ─────────────────────────────────────────────
class TestExtractFeaturesFromArray:
    def test_returns_dataframe_with_one_row(self):
        import pandas as pd
        mask = _circle_mask()
        df = extract_features_from_array(mask, "test_img", resolution=4.25, n_harmonics=10)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_contains_geometric_columns(self):
        mask = _circle_mask()
        df = extract_features_from_array(mask, "test_img", resolution=4.25, n_harmonics=10)
        for col in ["area_mu2", "circularity", "eccentricity", "solidity"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_contains_efd_columns(self):
        mask = _circle_mask()
        df = extract_features_from_array(mask, "test_img", resolution=4.25, n_harmonics=10)
        efd_cols = [c for c in df.columns if c.startswith("efd_")]
        assert len(efd_cols) == 40  # 10 harmonics × 4 coefficients

    def test_contains_hu_moment_columns(self):
        mask = _circle_mask()
        df = extract_features_from_array(mask, "test_img", resolution=4.25, n_harmonics=10)
        hu_cols = [c for c in df.columns if c.startswith("hu_")]
        assert len(hu_cols) == 7

    def test_empty_mask_returns_nan_df(self):
        import pandas as pd
        mask = np.zeros((50, 50), dtype=np.uint8)
        df = extract_features_from_array(mask, "empty", resolution=4.25, n_harmonics=10)
        assert isinstance(df, pd.DataFrame)

    def test_circle_has_high_circularity(self):
        mask = _circle_mask(radius=45)
        df = extract_features_from_array(mask, "circle", resolution=1.0, n_harmonics=10)
        assert df.iloc[0]["circularity"] > 0.85


# ─────────────────────────────────────────────
# classify_shape
# ─────────────────────────────────────────────
class TestClassifyShape:
    VALID_CLASSES = {
        "Circular", "Elliptical", "Flattened",
        "Triangular", "Tear-drop", "Multi-polar", "Irregular",
    }

    def _circle_features(self):
        return {
            "circularity": 0.97,
            "eccentricity": 0.1,
            "solidity": 0.98,
            "aspect_ratio": 1.02,
            "convexity": 0.99,
        }

    def _ellipse_features(self):
        return {
            "circularity": 0.75,
            "eccentricity": 0.65,
            "solidity": 0.97,
            "aspect_ratio": 1.8,
            "convexity": 0.97,
        }

    def _flattened_features(self):
        return {
            "circularity": 0.50,
            "eccentricity": 0.90,
            "solidity": 0.96,
            "aspect_ratio": 3.5,
            "convexity": 0.95,
        }

    def test_returns_string(self):
        result = classify_shape(self._circle_features())
        assert isinstance(result, str)

    def test_valid_class_returned(self):
        for feat in [self._circle_features(), self._ellipse_features(), self._flattened_features()]:
            result = classify_shape(feat)
            assert result in self.VALID_CLASSES, f"Unexpected class: {result}"

    def test_circle_classified_as_circular_or_elliptical(self):
        result = classify_shape(self._circle_features())
        assert result in {"Circular", "Elliptical"}

    def test_flattened_classified_correctly(self):
        result = classify_shape(self._flattened_features())
        assert result in {"Flattened", "Elliptical"}
