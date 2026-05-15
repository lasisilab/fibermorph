"""Unit tests for core.filters module."""

import numpy as np
import pytest
from PIL import Image
from fibermorph.core.filters import filter_curv, filter_curv_clahe


class TestFilterCurv:
    """Tests for filter_curv function."""
    
    def test_filter_curv_basic(self, tmp_path):
        """Test basic filtering of an image."""
        # Create a test image with some lines
        img_path = tmp_path / "test_image.tif"
        test_img = np.ones((100, 100), dtype=np.uint8) * 255
        # Add a dark line
        test_img[50, :] = 50
        Image.fromarray(test_img, mode='L').save(img_path)
        
        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=False)
        
        assert isinstance(filter_img, np.ndarray)
        assert filter_img.shape == (100, 100)
        assert im_name == "test_image"
    
    def test_filter_curv_returns_tuple(self, tmp_path):
        """Test that filter_curv returns a tuple."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (50, 50), color=128)
        test_img.save(img_path)
        
        result = filter_curv(img_path, tmp_path, save_img=False)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_filter_curv_with_save(self, tmp_path):
        """Test filtering with image saving."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (50, 50), color=128)
        test_img.save(img_path)
        
        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=True)
        
        # Check that filtered directory was created
        filtered_dir = tmp_path / "filtered"
        assert filtered_dir.exists()
        
        # Check that image was saved
        saved_image = filtered_dir / "test_image.tiff"
        assert saved_image.exists()
    
    def test_filter_curv_output_type(self, tmp_path):
        """Test that output is float type (from frangi filter)."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (50, 50), color=128)
        test_img.save(img_path)
        
        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=False)
        
        assert filter_img.dtype in [np.float32, np.float64]
    
    def test_filter_curv_preserves_dimensions(self, tmp_path):
        """Test that filtering preserves image dimensions."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (80, 60), color=128)
        test_img.save(img_path)
        
        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=False)
        
        assert filter_img.shape == (60, 80)
    
    def test_filter_curv_with_string_path(self, tmp_path):
        """Test filter_curv with string path."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (50, 50), color=128)
        test_img.save(img_path)
        
        filter_img, im_name = filter_curv(str(img_path), str(tmp_path), save_img=False)
        
        assert isinstance(filter_img, np.ndarray)
        assert im_name == "test_image"
    
    def test_filter_curv_extracts_correct_name(self, tmp_path):
        """Test that correct image name is extracted."""
        img_path = tmp_path / "my_special_image.tif"
        test_img = Image.new("L", (50, 50), color=128)
        test_img.save(img_path)
        
        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=False)

        assert im_name == "my_special_image"


class TestFilterCurvClahe:
    """Tests for filter_curv_clahe (CLAHE + Frangi + masked-ROI Otsu)."""

    def test_returns_tuple(self, tmp_path):
        img_path = tmp_path / "test_image.tif"
        Image.new("L", (80, 80), color=128).save(img_path)
        result = filter_curv_clahe(img_path, tmp_path, save_img=False)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_uint8_binary(self, tmp_path):
        img_path = tmp_path / "test_image.tif"
        Image.new("L", (80, 80), color=128).save(img_path)
        binary, im_name = filter_curv_clahe(img_path, tmp_path, save_img=False)
        assert binary.dtype == np.uint8
        assert set(np.unique(binary)).issubset({0, 255})

    def test_preserves_dimensions(self, tmp_path):
        img_path = tmp_path / "test_image.tif"
        Image.new("L", (120, 90), color=128).save(img_path)
        binary, _ = filter_curv_clahe(img_path, tmp_path, save_img=False)
        assert binary.shape == (90, 120)

    def test_extracts_correct_name(self, tmp_path):
        img_path = tmp_path / "clahe_test.tif"
        Image.new("L", (60, 60), color=128).save(img_path)
        _, im_name = filter_curv_clahe(img_path, tmp_path, save_img=False)
        assert im_name == "clahe_test"

    def test_with_line_image(self, tmp_path):
        img = np.ones((100, 100), dtype=np.uint8) * 200
        img[50, :] = 30
        img_path = tmp_path / "line.tif"
        Image.fromarray(img, mode="L").save(img_path)
        binary, im_name = filter_curv_clahe(img_path, tmp_path, save_img=False)
        assert isinstance(binary, np.ndarray)
        assert im_name == "line"
