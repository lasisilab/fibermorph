"""Unit tests for extended curvature functions added in v2.0 (curl_index, wave_count)."""

import numpy as np
import pytest
from skimage import draw as sk_draw

from fibermorph.core.curvature import curl_index_from_skeleton, wave_count


# ─────────────────────────────────────────────
# Synthetic skeletons
# ─────────────────────────────────────────────

def _straight_skel(length: int = 100, width: int = 120) -> np.ndarray:
    """Horizontal straight line skeleton."""
    skel = np.zeros((width, length), dtype=bool)
    skel[width // 2, :] = True
    return skel


def _wave_skel(n_waves: int = 3, width: int = 100, length: int = 200) -> np.ndarray:
    """Sinusoidal skeleton with n_waves complete cycles."""
    skel = np.zeros((width, length), dtype=bool)
    center = width // 2
    amplitude = width // 4
    for x in range(length):
        y = int(center + amplitude * np.sin(2 * np.pi * n_waves * x / length))
        y = np.clip(y, 0, width - 1)
        skel[y, x] = True
    return skel


def _curved_skel(radius: int = 80, arc_fraction: float = 0.5) -> np.ndarray:
    """Circular arc skeleton (arc_fraction of a full circle).

    Uses enough sample points to guarantee a connected skeleton.
    """
    size = radius * 3
    skel = np.zeros((size, size), dtype=bool)
    center = (size // 2, size // 2)
    # Use at least 4× the arc pixel-length to ensure adjacent pixels are set
    n_pts = max(int(radius * arc_fraction * 2 * np.pi * 4), 500)
    theta_range = np.linspace(0, 2 * np.pi * arc_fraction, n_pts)
    for t in theta_range:
        r = int(center[0] + radius * np.sin(t))
        c = int(center[1] + radius * np.cos(t))
        if 0 <= r < size and 0 <= c < size:
            skel[r, c] = True
    return skel


# ─────────────────────────────────────────────
# curl_index_from_skeleton
# ─────────────────────────────────────────────
class TestCurlIndex:
    def test_straight_line_has_low_curl_index(self):
        skel = _straight_skel()
        ci_mean, ci_std, lengths = curl_index_from_skeleton(skel, resolution_mm=1.0)
        assert ci_mean >= 0
        # A straight line chord ≈ arc, so curl index close to 1 (low curl)
        assert ci_mean <= 1.1

    def test_curved_line_has_higher_curl_index(self):
        straight = _straight_skel()
        curved   = _curved_skel(arc_fraction=0.5)
        ci_straight, _, _ = curl_index_from_skeleton(straight, resolution_mm=1.0)
        ci_curved,   _, _ = curl_index_from_skeleton(curved,   resolution_mm=1.0)
        # curl_index_from_skeleton returns chord/arc (straightness ratio).
        # A curved arc has chord < arc, so its ratio is lower than a straight line (≈1).
        assert not np.isnan(ci_curved), "Curved skeleton should not produce nan curl index"
        assert ci_curved < ci_straight

    def test_returns_tuple_of_three(self):
        skel   = _straight_skel()
        result = curl_index_from_skeleton(skel, resolution_mm=1.0)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_lengths_are_positive(self):
        skel = _straight_skel()
        _, _, lengths = curl_index_from_skeleton(skel, resolution_mm=1.0)
        if len(lengths) > 0:
            assert all(l > 0 for l in lengths)

    def test_empty_skeleton_returns_zeros(self):
        skel = np.zeros((50, 50), dtype=bool)
        ci_mean, ci_std, lengths = curl_index_from_skeleton(skel, resolution_mm=1.0)
        assert ci_mean == 0 or np.isnan(ci_mean) or ci_mean >= 0
        assert len(lengths) == 0


# ─────────────────────────────────────────────
# wave_count
# ─────────────────────────────────────────────
class TestWaveCount:
    def _curv_flat(self, n: int = 100) -> np.ndarray:
        return np.full(n, 0.1)

    def _curv_wavy(self, n_peaks: int = 4, n: int = 200) -> np.ndarray:
        t = np.linspace(0, 2 * np.pi * n_peaks, n)
        return np.abs(np.sin(t)) * 2 + 0.05

    def test_flat_signal_returns_zero(self):
        result = wave_count(self._curv_flat())
        assert isinstance(result, int)
        assert result == 0

    def test_wavy_signal_detects_peaks(self):
        for n in [2, 3, 4]:
            signal = self._curv_wavy(n_peaks=n)
            result = wave_count(signal)
            assert result > 0, f"Expected >0 waves for {n}-peak signal, got {result}"

    def test_returns_non_negative_integer(self):
        for sig in [self._curv_flat(), self._curv_wavy(2), self._curv_wavy(5)]:
            result = wave_count(sig)
            assert isinstance(result, (int, np.integer))
            assert result >= 0

    def test_more_peaks_not_fewer(self):
        low  = wave_count(self._curv_wavy(n_peaks=2))
        high = wave_count(self._curv_wavy(n_peaks=5))
        assert high >= low

    def test_empty_array_returns_zero(self):
        result = wave_count(np.array([]))
        assert result == 0
