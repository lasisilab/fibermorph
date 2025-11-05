"""Unit tests for processing.binary module."""

import numpy as np
import pytest
from PIL import Image
import skimage.util
from fibermorph.processing.binary import check_bin, binarize_curv, remove_particles


class TestCheckBin:
    """Tests for check_bin function."""
    
    def test_check_bin_correct_orientation(self):
        """Test check_bin with correctly oriented binary image."""
        # Create binary image with more background (False) than foreground (True)
        img = np.zeros((100, 100), dtype=bool)
        img[40:60, 40:60] = True  # Small foreground region
        
        result = check_bin(img)
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        assert result.shape == (100, 100)
    
    def test_check_bin_inverted_orientation(self):
        """Test check_bin with inverted binary image."""
        # Create binary image with more foreground than background
        img = np.ones((100, 100), dtype=bool)
        img[40:60, 40:60] = False  # Small background region
        
        result = check_bin(img)
        assert isinstance(result, np.ndarray)
        # Should be inverted
        assert np.sum(result) < np.sum(img)
    
    def test_check_bin_with_uint8(self):
        """Test check_bin with uint8 array."""
        img = np.zeros((100, 100), dtype=np.uint8)
        img[40:60, 40:60] = 255
        
        result = check_bin(img)
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
    
    def test_check_bin_returns_more_false_than_true(self):
        """Test that check_bin ensures more background than foreground."""
        img = np.zeros((100, 100), dtype=bool)
        img[10:20, 10:20] = True
        
        result = check_bin(img)
        # Should have more False (background) than True (foreground)
        assert np.sum(~result) > np.sum(result)


class TestBinarizeCurv:
    """Tests for binarize_curv function."""
    
    def test_binarize_curv_basic(self, tmp_path):
        """Test basic binarization."""
        # Create a simple float64 filtered image
        filter_img = np.random.rand(100, 100).astype(np.float64)
        filter_img[40:60, 40:60] = 0.9  # High intensity region
        
        result = binarize_curv(filter_img, "test_image", tmp_path, save_img=False)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        assert result.shape == (100, 100)
    
    def test_binarize_curv_with_save(self, tmp_path):
        """Test binarization with image saving."""
        filter_img = np.random.rand(100, 100).astype(np.float64)
        filter_img[40:60, 40:60] = 0.9
        
        result = binarize_curv(filter_img, "test_image", tmp_path, save_img=True)
        
        # Check that binarized directory was created
        binarized_dir = tmp_path / "binarized"
        assert binarized_dir.exists()
        
        # Check that image was saved
        saved_image = binarized_dir / "test_image.tiff"
        assert saved_image.exists()
    
    def test_binarize_curv_float_input(self, tmp_path):
        """Test that function handles float64 input correctly."""
        filter_img = np.random.rand(50, 50).astype(np.float64)
        
        result = binarize_curv(filter_img, "test", tmp_path, save_img=False)
        assert result.dtype == bool


class TestRemoveParticles:
    """Tests for remove_particles function."""
    
    def test_remove_particles_basic(self, tmp_path):
        """Test basic particle removal."""
        # Create binary image with small and large objects
        img = np.zeros((100, 100), dtype=bool)
        img[10:15, 10:15] = True  # Small object (25 pixels)
        img[40:70, 40:70] = True  # Large object (900 pixels)
        
        result = remove_particles(img, tmp_path, "test", minpixel=100, 
                                 prune=False, save_img=False)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        # Small object should be removed
        assert np.sum(result[10:15, 10:15]) == 0
        # Large object should remain
        assert np.sum(result[40:70, 40:70]) > 0
    
    def test_remove_particles_with_save_clean(self, tmp_path):
        """Test particle removal with saving."""
        img = np.zeros((100, 100), dtype=bool)
        img[40:60, 40:60] = True
        
        result = remove_particles(img, tmp_path, "test", minpixel=10, 
                                 prune=False, save_img=True)
        
        # Check that clean directory was created
        clean_dir = tmp_path / "clean"
        assert clean_dir.exists()
        
        # Check that image was saved
        saved_image = clean_dir / "test.tiff"
        assert saved_image.exists()
    
    def test_remove_particles_with_save_pruned(self, tmp_path):
        """Test particle removal with pruned flag."""
        img = np.zeros((100, 100), dtype=bool)
        img[40:60, 40:60] = True
        
        result = remove_particles(img, tmp_path, "test", minpixel=10, 
                                 prune=True, save_img=True)
        
        # Check that pruned directory was created
        pruned_dir = tmp_path / "pruned"
        assert pruned_dir.exists()
    
    def test_remove_particles_all_removed(self, tmp_path):
        """Test when all particles are below minimum size."""
        img = np.zeros((100, 100), dtype=bool)
        img[10:12, 10:12] = True  # 4 pixels
        img[20:22, 20:22] = True  # 4 pixels
        
        result = remove_particles(img, tmp_path, "test", minpixel=100, 
                                 prune=False, save_img=False)
        
        # All small particles should be removed
        assert np.sum(result) == 0
    
    def test_remove_particles_none_removed(self, tmp_path):
        """Test when no particles are removed."""
        img = np.zeros((100, 100), dtype=bool)
        img[10:60, 10:60] = True  # 2500 pixels
        
        result = remove_particles(img, tmp_path, "test", minpixel=10, 
                                 prune=False, save_img=False)
        
        # Large object should remain
        assert np.sum(result) > 2000
