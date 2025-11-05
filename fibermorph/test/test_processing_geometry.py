"""Unit tests for processing.geometry module."""

import numpy as np
import pytest
import skimage.measure
from fibermorph.processing.geometry import define_structure, find_structure, pixel_length_correction


class TestDefineStructure:
    """Tests for define_structure function."""
    
    def test_define_structure_mid(self):
        """Test defining mid-point structures."""
        result = define_structure("mid")
        
        assert isinstance(result, list)
        assert len(result) == 8  # Should return 8 mid-point structures
        assert all(isinstance(s, np.ndarray) for s in result)
        assert all(s.shape == (3, 3) for s in result)
    
    def test_define_structure_diag(self):
        """Test defining diagonal structures."""
        result = define_structure("diag")
        
        assert isinstance(result, list)
        assert len(result) == 2  # Should return 2 diagonal structures
        assert all(isinstance(s, np.ndarray) for s in result)
        assert all(s.shape == (3, 3) for s in result)
    
    def test_define_structure_invalid(self):
        """Test with invalid structure type."""
        with pytest.raises(TypeError):
            define_structure("invalid")
    
    def test_define_structure_mid_values(self):
        """Test that mid structures have correct values."""
        result = define_structure("mid")
        
        # Each structure should have exactly 3 ones (the pattern)
        for structure in result:
            assert np.sum(structure) == 3
            assert structure.dtype == np.uint8
    
    def test_define_structure_diag_values(self):
        """Test that diagonal structures have correct values."""
        result = define_structure("diag")
        
        # Each structure should have exactly 3 ones (the pattern)
        for structure in result:
            assert np.sum(structure) == 3
            assert structure.dtype == np.uint8


class TestFindStructure:
    """Tests for find_structure function."""
    
    def test_find_structure_mid_simple(self):
        """Test finding mid-point structures in skeleton."""
        # Create a simple skeleton with a mid-point pattern
        skeleton = np.zeros((10, 10), dtype=bool)
        skeleton[4:7, 4:7] = False
        skeleton[5, 4:7] = True  # Horizontal line
        
        labels, num_labels = find_structure(skeleton, "mid")
        
        assert isinstance(labels, np.ndarray)
        assert isinstance(num_labels, int)
        assert num_labels >= 0
    
    def test_find_structure_diag_simple(self):
        """Test finding diagonal structures in skeleton."""
        # Create a simple skeleton with diagonal pattern
        skeleton = np.zeros((10, 10), dtype=bool)
        skeleton[3, 3] = True
        skeleton[4, 4] = True
        skeleton[5, 5] = True
        
        labels, num_labels = find_structure(skeleton, "diag")
        
        assert isinstance(labels, np.ndarray)
        assert isinstance(num_labels, int)
        assert num_labels >= 0
    
    def test_find_structure_with_few_points(self):
        """Test with skeleton that has some points."""
        skeleton = np.zeros((10, 10), dtype=bool)
        # Add a small pattern
        skeleton[5, 5:8] = True
        
        labels, num_labels = find_structure(skeleton, "mid")
        
        assert isinstance(num_labels, int)
        assert labels.shape == skeleton.shape
    
    def test_find_structure_returns_correct_shape(self):
        """Test that returned labels have same shape as input."""
        skeleton = np.zeros((20, 30), dtype=bool)
        skeleton[10, 10:13] = True
        
        labels, num_labels = find_structure(skeleton, "mid")
        
        assert labels.shape == skeleton.shape


class TestPixelLengthCorrection:
    """Tests for pixel_length_correction function."""
    
    def test_pixel_length_correction_straight_line(self):
        """Test correction for a straight horizontal line."""
        # Create a thicker line that forms a skeleton properly
        img = np.zeros((20, 20), dtype=bool)
        # Create a thicker shape that can be skeletonized
        img[9:12, 5:15] = True
        
        # Skeletonize it
        from skimage.morphology import skeletonize
        skel = skeletonize(img)
        
        # Get region properties
        labeled = skimage.measure.label(skel)
        props = skimage.measure.regionprops(labeled)
        
        if len(props) > 0:
            element = props[0]
            result = pixel_length_correction(element)
            
            assert isinstance(result, float)
            assert result > 0
    
    def test_pixel_length_correction_diagonal_line(self):
        """Test correction for a diagonal line."""
        # Create a thicker diagonal shape that can be skeletonized
        img = np.zeros((20, 20), dtype=bool)
        for i in range(10):
            img[5+i:7+i, 5+i:7+i] = True
        
        from skimage.morphology import skeletonize
        skel = skeletonize(img)
        
        labeled = skimage.measure.label(skel)
        props = skimage.measure.regionprops(labeled)
        
        if len(props) > 0:
            element = props[0]
            result = pixel_length_correction(element)
            
            assert isinstance(result, float)
            assert result > 0
    
    def test_pixel_length_correction_returns_float(self):
        """Test that function returns a float."""
        # Create a shape that can be properly analyzed
        img = np.zeros((20, 20), dtype=bool)
        img[8:12, 5:15] = True
        
        from skimage.morphology import skeletonize
        skel = skeletonize(img)
        
        labeled = skimage.measure.label(skel)
        props = skimage.measure.regionprops(labeled)
        
        if len(props) > 0:
            element = props[0]
            result = pixel_length_correction(element)
            
            assert isinstance(result, float)
    
    def test_pixel_length_correction_small_shape(self):
        """Test correction for a small shape."""
        # Create a small cross shape for testing
        img = np.zeros((15, 15), dtype=bool)
        img[7, 5:10] = True
        img[5:10, 7] = True
        
        from skimage.morphology import skeletonize
        skel = skeletonize(img)
        
        labeled = skimage.measure.label(skel)
        props = skimage.measure.regionprops(labeled)
        
        if len(props) > 0:
            element = props[0]
            result = pixel_length_correction(element)
            
            assert isinstance(result, float)
            assert result > 0
    
    def test_pixel_length_correction_complex_shape(self):
        """Test correction for a more complex shape."""
        # Create an L-shaped pattern
        img = np.zeros((15, 15), dtype=bool)
        img[5, 5:10] = True  # Horizontal part
        img[5:10, 5] = True  # Vertical part
        
        labeled = skimage.measure.label(img)
        props = skimage.measure.regionprops(labeled)
        
        if len(props) > 0:
            element = props[0]
            result = pixel_length_correction(element)
            
            assert isinstance(result, float)
            assert result > 0
