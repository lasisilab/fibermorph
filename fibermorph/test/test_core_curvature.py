"""Unit tests for core.curvature module."""

import numpy as np
import pandas as pd
import pytest
import skimage.measure
from fibermorph.core.curvature import (
    taubin_curv, subset_gen, within_element_func, 
    analyze_each_curv, analyze_all_curv, window_iter
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
