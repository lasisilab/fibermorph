"""Unit tests for io.writers module."""

import numpy as np
import pytest
from PIL import Image
from fibermorph.io.writers import save_image


class TestSaveImage:
    """Tests for save_image function."""
    
    def test_save_image_basic(self, tmp_path):
        """Test basic image saving."""
        img = np.ones((50, 50), dtype=np.uint8) * 128
        
        result = save_image(img, tmp_path, "test_image")
        
        assert result.exists()
        assert result.name == "test_image.tiff"
        assert result.parent == tmp_path
    
    def test_save_image_with_suffix(self, tmp_path):
        """Test image saving with suffix."""
        img = np.ones((50, 50), dtype=np.uint8) * 128
        
        result = save_image(img, tmp_path, "test_image", suffix="processed")
        
        assert result.exists()
        assert result.name == "test_image_processed.tiff"
    
    def test_save_image_boolean_array(self, tmp_path):
        """Test saving boolean array."""
        img = np.zeros((50, 50), dtype=bool)
        img[20:30, 20:30] = True
        
        result = save_image(img, tmp_path, "bool_image")
        
        assert result.exists()
        # Verify image was converted and saved
        saved_img = np.array(Image.open(result))
        assert saved_img.dtype == np.uint8
    
    def test_save_image_uint8_array(self, tmp_path):
        """Test saving uint8 array."""
        img = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
        
        result = save_image(img, tmp_path, "uint8_image")
        
        assert result.exists()
        saved_img = np.array(Image.open(result))
        assert saved_img.shape == img.shape
    
    def test_save_image_with_string_path(self, tmp_path):
        """Test save_image with string path."""
        img = np.ones((50, 50), dtype=np.uint8) * 100
        
        result = save_image(img, str(tmp_path), "test_image")
        
        assert result.exists()
        assert isinstance(result, type(tmp_path))  # Should be pathlib.Path
    
    def test_save_image_returns_pathlib_path(self, tmp_path):
        """Test that function returns pathlib.Path."""
        img = np.ones((50, 50), dtype=np.uint8) * 100
        
        result = save_image(img, tmp_path, "test")
        
        from pathlib import Path
        assert isinstance(result, Path)
    
    def test_save_image_different_sizes(self, tmp_path):
        """Test saving images of different sizes."""
        img1 = np.ones((100, 100), dtype=np.uint8) * 50
        img2 = np.ones((200, 150), dtype=np.uint8) * 150
        
        result1 = save_image(img1, tmp_path, "small")
        result2 = save_image(img2, tmp_path, "large")
        
        assert result1.exists()
        assert result2.exists()
        
        # Verify sizes are preserved
        saved1 = Image.open(result1)
        saved2 = Image.open(result2)
        assert saved1.size == (100, 100)
        assert saved2.size == (150, 200)  # PIL uses (width, height)
