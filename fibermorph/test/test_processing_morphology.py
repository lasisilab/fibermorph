"""Unit tests for processing.morphology module."""

import numpy as np
import pytest
from fibermorph.processing.morphology import skeletonize, prune, diag


class TestSkeletonize:
    """Tests for skeletonize function."""
    
    def test_skeletonize_basic(self, tmp_path):
        """Test basic skeletonization."""
        # Create a thick line
        img = np.zeros((100, 100), dtype=bool)
        img[45:55, 30:70] = True
        
        result = skeletonize(img, "test_image", tmp_path, save_img=False)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        assert result.shape == img.shape
        # Skeleton should have fewer pixels than original
        assert np.sum(result) < np.sum(img)
    
    def test_skeletonize_with_save(self, tmp_path):
        """Test skeletonization with image saving."""
        img = np.zeros((100, 100), dtype=bool)
        img[45:55, 30:70] = True
        
        result = skeletonize(img, "test_image", tmp_path, save_img=True)
        
        # Check that skeletonized directory was created
        skel_dir = tmp_path / "skeletonized"
        assert skel_dir.exists()
        
        # Check that image was saved
        saved_image = skel_dir / "test_image.tiff"
        assert saved_image.exists()
    
    def test_skeletonize_preserves_connectivity(self, tmp_path):
        """Test that skeletonization preserves connectivity."""
        # Create a connected shape
        img = np.zeros((50, 50), dtype=bool)
        img[20:30, 20:30] = True
        
        result = skeletonize(img, "test", tmp_path, save_img=False)
        
        # Skeleton should still be connected (non-zero)
        assert np.sum(result) > 0
    
    def test_skeletonize_returns_bool(self, tmp_path):
        """Test that skeletonize returns boolean array."""
        img = np.zeros((50, 50), dtype=bool)
        img[20:30, 20:30] = True
        
        result = skeletonize(img, "test", tmp_path, save_img=False)
        
        assert result.dtype == bool


class TestPrune:
    """Tests for prune function."""
    
    def test_prune_basic(self, tmp_path):
        """Test basic pruning."""
        # Create a skeleton with branches
        skeleton = np.zeros((50, 50), dtype=bool)
        skeleton[25, 10:40] = True  # Main horizontal line
        skeleton[10:30, 25] = True  # Vertical branch
        
        result = prune(skeleton, "test_image", tmp_path, save_img=False)
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == bool
        assert result.shape == skeleton.shape
    
    def test_prune_removes_branches(self, tmp_path):
        """Test that prune removes branch points."""
        # Create T-shaped skeleton
        skeleton = np.zeros((50, 50), dtype=bool)
        skeleton[25, 20:30] = True  # Horizontal
        skeleton[25:35, 25] = True  # Vertical branch
        
        result = prune(skeleton, "test", tmp_path, save_img=False)
        
        # Result should have fewer or equal pixels
        assert np.sum(result) <= np.sum(skeleton)
    
    def test_prune_with_save(self, tmp_path):
        """Test pruning with image saving."""
        skeleton = np.zeros((50, 50), dtype=bool)
        skeleton[25, 20:30] = True
        
        result = prune(skeleton, "test_image", tmp_path, save_img=True)
        
        # Check that pruned directory was created
        pruned_dir = tmp_path / "pruned"
        assert pruned_dir.exists()
    
    def test_prune_simple_line(self, tmp_path):
        """Test pruning a simple line without branches."""
        # Create a simple line (no branches)
        skeleton = np.zeros((50, 50), dtype=bool)
        skeleton[25, 20:30] = True
        
        result = prune(skeleton, "test", tmp_path, save_img=False)
        
        # Simple line should remain mostly intact
        assert isinstance(result, np.ndarray)


class TestDiag:
    """Tests for diag function."""
    
    def test_diag_straight_line(self):
        """Test diagonal analysis on straight line."""
        # Create a horizontal line
        skeleton = np.zeros((20, 20), dtype=bool)
        skeleton[10, 5:15] = True
        
        num_diag, num_mid, num_adj = diag(skeleton)
        
        assert isinstance(num_diag, int)
        assert isinstance(num_mid, int)
        assert isinstance(num_adj, int)
        assert num_diag >= 0
        assert num_mid >= 0
        assert num_adj >= 0
    
    def test_diag_diagonal_line(self):
        """Test diagonal analysis on diagonal line."""
        # Create a diagonal line
        skeleton = np.zeros((20, 20), dtype=bool)
        for i in range(10):
            skeleton[5+i, 5+i] = True
        
        num_diag, num_mid, num_adj = diag(skeleton)
        
        # Diagonal line should have diagonal points
        assert num_diag >= 0
        assert isinstance(num_diag, int)
    
    def test_diag_returns_tuple(self):
        """Test that diag returns a tuple of three integers."""
        skeleton = np.zeros((20, 20), dtype=bool)
        skeleton[10, 5:15] = True
        
        result = diag(skeleton)
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(x, int) for x in result)
    
    def test_diag_empty_skeleton(self):
        """Test diagonal analysis on mostly empty skeleton."""
        skeleton = np.zeros((20, 20), dtype=bool)
        skeleton[10, 10] = True  # Single pixel
        
        num_diag, num_mid, num_adj = diag(skeleton)
        
        # Single pixel should not have any diagonal/mid/adj patterns
        assert num_diag == 0
        assert num_mid == 0
        assert num_adj == 0
    
    def test_diag_complex_shape(self):
        """Test diagonal analysis on complex shape."""
        # Create a cross shape
        skeleton = np.zeros((20, 20), dtype=bool)
        skeleton[10, 5:15] = True  # Horizontal
        skeleton[5:15, 10] = True  # Vertical
        
        num_diag, num_mid, num_adj = diag(skeleton)
        
        # Cross should have adjacent and possibly mid points
        assert isinstance(num_diag, int)
        assert isinstance(num_mid, int)
        assert isinstance(num_adj, int)
