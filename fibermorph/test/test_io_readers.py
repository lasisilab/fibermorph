"""Unit tests for io.readers module."""

import numpy as np
import pytest
from PIL import Image
from fibermorph.io.readers import imread


class TestImread:
    """Tests for imread function."""
    
    def test_imread_basic_image(self, tmp_path):
        """Test reading a basic grayscale image."""
        # Create a test image
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (100, 100), color=128)
        test_img.save(img_path)
        
        # Read the image
        img, name = imread(img_path)
        
        assert isinstance(img, np.ndarray)
        assert img.dtype == np.uint8
        assert img.shape == (100, 100)
        assert name == "test_image"
    
    def test_imread_returns_correct_name(self, tmp_path):
        """Test that imread returns correct image name."""
        img_path = tmp_path / "my_image.tiff"
        test_img = Image.new("L", (50, 50), color=100)
        test_img.save(img_path)
        
        img, name = imread(img_path)
        assert name == "my_image"
    
    def test_imread_with_string_path(self, tmp_path):
        """Test imread with string path."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (100, 100), color=128)
        test_img.save(img_path)
        
        img, name = imread(str(img_path))
        assert isinstance(img, np.ndarray)
    
    def test_imread_converts_to_grayscale(self, tmp_path):
        """Test that imread converts color images to grayscale."""
        # Create an RGB image
        img_path = tmp_path / "color_image.tif"
        test_img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        test_img.save(img_path)
        
        # Read and check it's converted to grayscale
        img, name = imread(img_path)
        assert len(img.shape) == 2  # 2D array (grayscale)
        assert img.dtype == np.uint8
    
    def test_imread_with_skimage(self, tmp_path):
        """Test imread with use_skimage parameter."""
        img_path = tmp_path / "test_image.tif"
        test_img = Image.new("L", (100, 100), color=128)
        test_img.save(img_path)
        
        img, name = imread(img_path, use_skimage=True)
        assert isinstance(img, np.ndarray)
        assert img.dtype == np.uint8
    
    def test_imread_different_intensities(self, tmp_path):
        """Test imread with different intensity values."""
        img_path = tmp_path / "test_image.tif"
        # Create image with specific intensity
        test_img = Image.new("L", (10, 10), color=200)
        test_img.save(img_path)
        
        img, name = imread(img_path)
        # All pixels should be approximately 200
        assert np.mean(img) > 190
        assert np.mean(img) < 210
    
    def test_imread_tiff_extension(self, tmp_path):
        """Test imread with .tiff extension."""
        img_path = tmp_path / "test_image.tiff"
        test_img = Image.new("L", (50, 50), color=100)
        test_img.save(img_path)
        
        img, name = imread(img_path)
        assert isinstance(img, np.ndarray)
        assert name == "test_image"
