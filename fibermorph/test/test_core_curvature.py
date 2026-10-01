"""Unit tests for core.curvature module."""

import numpy as np
import pandas as pd
import pytest
import skimage.measure
from skimage import draw as sk_draw
from fibermorph.core.curvature import (
    taubin_curv,
    subset_gen,
    within_element_func,
    analyze_each_curv,
    analyze_all_curv,
    window_iter,
)


class TestTaubinCurv:
    """Tests for taubin_curv function."""
    
    def test_taubin_curv_straight_line(self):
        """Test curvature calculation for a straight line."""
        # Create coordinates for a straight line
        coords = np.array([[i, 10] for i in range(20)])
        resolution = 1.0
        
        result = taubin_curv(coords, resolution)
        
        # Result may be int (0) or float, both are valid for zero curvature
        assert isinstance(result, (int, float))
        # Straight line should have zero or very low curvature
        assert result < 0.01
    
    def test_taubin_curv_circular_arc(self):
        """Test curvature calculation for a circular arc."""
        # Create coordinates for a circular arc
        theta = np.linspace(0, np.pi/2, 20)
        radius = 10
        coords = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
        resolution = 1.0
        
        result = taubin_curv(coords, resolution)
        
        assert isinstance(result, float)
        # Arc should have non-zero curvature
        assert result > 0
    
    def test_taubin_curv_returns_zero_for_insufficient_points(self):
        """Test with very few points."""
        # Need at least 3 points for SVD
        coords = np.array([[0, 0], [1, 1], [2, 2]])
        resolution = 1.0
        
        result = taubin_curv(coords, resolution)
        
        assert isinstance(result, (int, float))
        assert result >= 0
    
    def test_taubin_curv_with_different_resolution(self):
        """Test curvature with different resolution values."""
        coords = np.array([[i, i*i/10] for i in range(20)])
        resolution1 = 1.0
        resolution2 = 2.0
        
        result1 = taubin_curv(coords, resolution1)
        result2 = taubin_curv(coords, resolution2)
        
        assert isinstance(result1, float)
        assert isinstance(result2, float)
        # Different resolutions should give different curvatures
        assert result1 != result2


class TestSubsetGen:
    """Tests for subset_gen function."""
    
    def test_subset_gen_basic(self):
        """Test basic subset generation."""
        pixel_length = 100
        window_size_px = 20
        label = np.array([[i, i] for i in range(pixel_length)])
        
        subsets = list(subset_gen(pixel_length, window_size_px, label))
        
        assert len(subsets) > 0
        assert all(isinstance(s, np.ndarray) for s in subsets)
        # First subset should be window_size_px long
        assert len(subsets[0]) == window_size_px
    
    def test_subset_gen_window_smaller_than_10(self):
        """Test subset generation with window size < 10."""
        pixel_length = 50
        window_size_px = 5
        label = np.array([[i, i] for i in range(pixel_length)])
        
        subsets = list(subset_gen(pixel_length, window_size_px, label))
        
        # Should use full length
        assert len(subsets) > 0
    
    def test_subset_gen_yields_correct_count(self):
        """Test that subset_gen yields correct number of windows."""
        pixel_length = 100
        window_size_px = 20
        label = np.array([[i, i] for i in range(pixel_length)])
        
        subsets = list(subset_gen(pixel_length, window_size_px, label))
        
        # Should generate (pixel_length - window_size_px + 1) windows
        expected_count = pixel_length - window_size_px + 1
        assert len(subsets) == expected_count
    
    def test_subset_gen_sliding_window(self):
        """Test that windows slide correctly."""
        pixel_length = 30
        window_size_px = 10
        label = np.array([[i, i] for i in range(pixel_length)])
        
        subsets = list(subset_gen(pixel_length, window_size_px, label))
        
        # First window should start at 0
        assert np.array_equal(subsets[0][0], label[0])
        # Second window should start at 1
        assert np.array_equal(subsets[1][0], label[1])


class TestWithinElementFunc:
    """Tests for within_element_func function."""
    
    def test_within_element_func_saves_file(self, tmp_path):
        """Test that within_element_func saves a CSV file."""
        # Create a mock element with label
        class MockElement:
            label = 1
        
        element = MockElement()
        taubin_df = pd.Series([0.1, 0.2, 0.3, 0.4])
        
        result = within_element_func(tmp_path, "test_image", element, taubin_df)
        
        assert result is True
        
        # Check that WithinElement directory was created
        within_elem_dir = tmp_path / "WithinElement"
        assert within_elem_dir.exists()
        
        # Check that CSV was saved
        csv_file = within_elem_dir / "WithinElement_test_image_Label-1.csv"
        assert csv_file.exists()
    
    def test_within_element_func_creates_dataframe(self, tmp_path):
        """Test that function creates proper DataFrame structure."""
        class MockElement:
            label = 2
        
        element = MockElement()
        taubin_df = pd.Series([0.1, 0.2, 0.3])
        
        result = within_element_func(tmp_path, "test", element, taubin_df)
        
        assert result is True
        
        # Read the saved CSV
        csv_file = tmp_path / "WithinElement" / "WithinElement_test_Label-2.csv"
        df = pd.read_csv(csv_file, index_col=0)
        
        assert "curv" in df.columns
        assert "label" in df.columns
        assert len(df) == 3


def _create_line_skeleton(length: int = 120) -> np.ndarray:
    """Create a 2D binary array containing a single horizontal line."""
    canvas = np.zeros((200, 200), dtype=np.uint8)
    start_row = 100
    start_col = 40
    end_col = start_col + length - 1
    rr, cc = sk_draw.line(start_row, start_col, start_row, end_col)
    canvas[rr, cc] = 1
    return canvas


def _create_arc_skeleton(radius: int = 60, num_points: int = 180) -> np.ndarray:
    """Create a 2D binary array containing a quarter-circle arc."""
    size = radius * 2 + 40
    canvas = np.zeros((size, size), dtype=np.uint8)
    center_row = radius + 20
    center_col = radius + 20
    theta_values = np.linspace(0, np.pi / 2, num_points)
    coords = []
    for theta in theta_values:
        row = int(round(center_row - radius * np.sin(theta)))
        col = int(round(center_col + radius * np.cos(theta)))
        coords.append((row, col))
    for (row0, col0), (row1, col1) in zip(coords, coords[1:]):
        rr, cc = sk_draw.line(row0, col0, row1, col1)
        canvas[rr, cc] = 1
    return canvas


class TestAnalyzeAllCurvSynthetic:
    """Integration-style tests for analyze_all_curv using synthetic skeletons."""

    def test_analyze_all_curv_straight_line(self, tmp_path):
        """Synthetic straight line should yield near-zero curvature."""
        skeleton = _create_line_skeleton(length=140)
        result = analyze_all_curv(
            skeleton,
            "synthetic_line",
            tmp_path,
            resolution=1.0,
            window_size=30,
            window_unit="px",
            test=False,
            within_element=False,
        )

        assert not result.empty
        curv_mean = result["curv_mean_mean"].iloc[0]
        assert curv_mean == pytest.approx(0.0, abs=1e-3)
        assert result["hair_count"].iloc[0] == 1

    def test_analyze_all_curv_quarter_arc(self, tmp_path):
        """Synthetic quarter arc should report curvature close to 1/radius."""
        radius = 60
        skeleton = _create_arc_skeleton(radius=radius)
        result = analyze_all_curv(
            skeleton,
            "synthetic_arc",
            tmp_path,
            resolution=1.0,
            window_size=30,
            window_unit="px",
            test=False,
            within_element=False,
        )

        assert not result.empty
        expected_curvature = 1.0 / radius
        curv_mean = result["curv_mean_mean"].iloc[0]
        assert curv_mean == pytest.approx(expected_curvature, rel=0.35)
        assert result["hair_count"].iloc[0] == 1


class TestAnalyzeAllCurv:
    """Tests for analyze_all_curv function."""
    
    def test_analyze_all_curv_simple_skeleton(self, tmp_path):
        """Test analyze_all_curv with simple skeleton."""
        # Create a thicker shape that can be properly skeletonized
        img = np.zeros((100, 100), dtype=np.uint8)
        img[48:52, 30:70] = 1  # Thicker horizontal line
        
        from skimage.morphology import skeletonize
        skel = skeletonize(img.astype(bool))
        
        result = analyze_all_curv(
            img=skel.astype(np.uint8),
            name="test_image",
            output_path=tmp_path,
            resolution=1.0,
            window_size=10,
            window_unit="px",
            test=False,
            within_element=False
        )
        
        assert isinstance(result, pd.DataFrame)
    
    def test_analyze_all_curv_multiple_window_sizes(self, tmp_path):
        """Test with multiple window sizes."""
        # Create a thicker line
        img = np.zeros((100, 100), dtype=np.uint8)
        img[48:52, 20:80] = 1  # Thicker long line
        
        from skimage.morphology import skeletonize
        skel = skeletonize(img.astype(bool))
        
        result = analyze_all_curv(
            img=skel.astype(np.uint8),
            name="test_image",
            output_path=tmp_path,
            resolution=1.0,
            window_size=[10, 20],
            window_unit="px",
            test=False,
            within_element=False
        )
        
        assert isinstance(result, pd.DataFrame)
    
    def test_analyze_all_curv_with_short_element(self, tmp_path):
        """Test with element shorter than window size."""
        # Create a short line
        img = np.zeros((100, 100), dtype=np.uint8)
        img[50, 45:50] = 1  # Very short line
        
        result = analyze_all_curv(
            img=img,
            name="short_image",
            output_path=tmp_path,
            resolution=1.0,
            window_size=10,
            window_unit="px",
            test=False,
            within_element=False
        )
        
        assert isinstance(result, pd.DataFrame)


def _create_two_line_skeleton(long_len: int = 120, short_len: int = 30) -> np.ndarray:
    """Two separate horizontal lines of different lengths."""
    canvas = np.zeros((200, 200), dtype=np.uint8)
    rr, cc = sk_draw.line(60, 20, 60, 20 + long_len - 1)
    canvas[rr, cc] = 1
    rr, cc = sk_draw.line(150, 20, 150, 20 + short_len - 1)
    canvas[rr, cc] = 1
    return canvas


class TestPerHairOutputWhenTestTrue:
    """test=True returns one row per hair (used by the simulated-data validation)."""

    def test_window_mode_returns_per_hair_rows(self, tmp_path):
        result = analyze_all_curv(
            _create_two_line_skeleton(), "two_lines", tmp_path,
            resolution=1.0, window_size=15, window_unit="px",
            test=True, within_element=False,
        )
        assert list(result.columns) == ["curv_mean", "curv_median", "length"]
        assert len(result) == 2
        assert sorted(result["length"].round(0)) == [30.0, 120.0]

    def test_window_mode_summary_when_test_false(self, tmp_path):
        result = analyze_all_curv(
            _create_two_line_skeleton(), "two_lines", tmp_path,
            resolution=1.0, window_size=15, window_unit="px",
            test=False, within_element=False,
        )
        assert list(result.columns) == [
            "ID", "curv_mean_mean", "curv_mean_median", "curv_median_mean",
            "curv_median_median", "length_mean", "length_median", "hair_count",
        ]
        assert result["hair_count"].iloc[0] == 2

    def test_per_hair_arc_curvature_matches_radius(self, tmp_path):
        """What validation_curv reads: curv_median per hair, close to 1/radius."""
        radius = 60
        result = analyze_all_curv(
            _create_arc_skeleton(radius=radius), "arc", tmp_path,
            resolution=1.0, window_size=30, window_unit="px",
            test=True, within_element=False,
        )
        assert len(result) == 1
        assert result["curv_median"].iloc[0] == pytest.approx(1.0 / radius, rel=0.35)


class TestWholeHairMode:
    """window_size=None fits one Taubin circle to each hair (v0.3.1 behavior)."""

    def test_summary_columns_and_values(self, tmp_path):
        radius = 60
        result = analyze_all_curv(
            _create_arc_skeleton(radius=radius), "whole_arc", tmp_path,
            resolution=1.0, window_size=None, window_unit="px",
            test=False, within_element=False,
        )
        assert list(result.columns) == [
            "ID", "curv_mean", "curv_median", "length_mean", "length_median",
            "hair_count",
        ]
        assert result["ID"].iloc[0] == "whole_arc"
        assert result["hair_count"].iloc[0] == 1
        assert result["curv_mean"].iloc[0] == pytest.approx(1.0 / radius, rel=0.1)
        assert result["curv_mean"].iloc[0] == result["curv_median"].iloc[0]

    def test_straight_line_has_zero_curvature(self, tmp_path):
        result = analyze_all_curv(
            _create_line_skeleton(length=140), "whole_line", tmp_path,
            resolution=1.0, window_size=None, window_unit="px",
            test=False, within_element=False,
        )
        assert result["curv_mean"].iloc[0] == pytest.approx(0.0, abs=1e-3)

    def test_test_true_returns_per_hair_curv_and_length(self, tmp_path):
        result = analyze_all_curv(
            _create_two_line_skeleton(), "whole_two", tmp_path,
            resolution=1.0, window_size=None, window_unit="px",
            test=True, within_element=False,
        )
        assert list(result.columns) == ["curv", "length"]
        assert len(result) == 2

    def test_hairs_shorter_than_half_resolution_are_skipped(self, tmp_path):
        """With resolution 100 px/mm the minimum is 50 px: the 30 px hair is dropped."""
        result = analyze_all_curv(
            _create_two_line_skeleton(long_len=120, short_len=30), "whole_min", tmp_path,
            resolution=100.0, window_size=None, window_unit="px",
            test=False, within_element=False,
        )
        assert result["hair_count"].iloc[0] == 1
        assert result["length_mean"].iloc[0] == pytest.approx(1.2)

    def test_writes_per_hair_csv(self, tmp_path):
        analyze_all_curv(
            _create_line_skeleton(length=140), "whole_csv", tmp_path,
            resolution=1.0, window_size=None, window_unit="px",
            test=False, within_element=False,
        )
        saved = pd.read_csv(tmp_path / "analysis" / "ImageSum_whole_csv.csv", index_col=0)
        assert list(saved.columns) == ["curv", "length"]
        assert len(saved) == 1

    def test_no_qualifying_hair_returns_empty_summary(self, tmp_path):
        """An image with no hair above the minimum length must not raise."""
        result = analyze_all_curv(
            np.zeros((50, 50), dtype=np.uint8), "whole_none", tmp_path,
            resolution=100.0, window_size=None, window_unit="px",
            test=False, within_element=False,
        )
        assert result["hair_count"].iloc[0] == 0
        assert np.isnan(result["curv_mean"].iloc[0])

    def test_window_list_may_mix_none_and_sizes(self, tmp_path):
        """A list of window sizes can include None (whole hair)."""
        result = analyze_all_curv(
            _create_line_skeleton(length=140), "mixed", tmp_path,
            resolution=1.0, window_size=[None, 30], window_unit="px",
            test=False, within_element=False,
        )
        assert len(result) == 2
