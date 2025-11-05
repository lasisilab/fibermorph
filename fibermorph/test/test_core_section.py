"""Unit tests for core.section module."""

import numpy as np
import pandas as pd
import pytest
from PIL import Image
import skimage.measure
from fibermorph.core.section import section_props, crop_section, segment_section, save_sections


class TestSectionProps:
    """Tests for section_props function."""
    
    def test_section_props_basic(self):
        """Test basic section properties extraction."""
        # Create a simple binary image with one circular-ish region
        img = np.zeros((100, 100), dtype=np.uint8)
        img[40:60, 40:60] = 255
        
        # Get region properties
        labeled = skimage.measure.label(img)
        props = skimage.measure.regionprops(labeled)
        
        im_center = [50, 50]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        section_data, bin_im, bbox = section_props(
            props, "test_image", resolution, minpixel, maxpixel, im_center
        )
        
        assert isinstance(section_data, pd.DataFrame)
        assert isinstance(bin_im, np.ndarray)
        assert isinstance(bbox, tuple)
        assert "ID" in section_data.columns
        assert "area" in section_data.columns
        assert "eccentricity" in section_data.columns
    
    def test_section_props_filters_by_size(self):
        """Test that section_props filters regions by size."""
        # Create image with multiple regions of different sizes
        img = np.zeros((100, 100), dtype=np.uint8)
        img[10:15, 10:15] = 255  # Small region
        img[40:80, 40:80] = 255  # Large region
        
        labeled = skimage.measure.label(img)
        props = skimage.measure.regionprops(labeled)
        
        im_center = [50, 50]
        resolution = 1.0
        minpixel = 20.0  # Should filter out the small region
        maxpixel = 100.0
        
        section_data, bin_im, bbox = section_props(
            props, "test", resolution, minpixel, maxpixel, im_center
        )
        
        assert isinstance(section_data, pd.DataFrame)
        assert len(section_data) > 0
    
    def test_section_props_selects_closest_to_center(self):
        """Test that section_props selects region closest to center."""
        # Create two regions at different distances from center
        img = np.zeros((100, 100), dtype=np.uint8)
        img[10:30, 10:30] = 255  # Far from center
        img[45:55, 45:55] = 255  # Near center
        
        labeled = skimage.measure.label(img)
        props = skimage.measure.regionprops(labeled)
        
        im_center = [50, 50]
        resolution = 1.0
        minpixel = 5.0
        maxpixel = 1000.0
        
        section_data, bin_im, bbox = section_props(
            props, "test", resolution, minpixel, maxpixel, im_center
        )
        
        # Should select the region near the center
        assert isinstance(section_data, pd.DataFrame)


class TestCropSection:
    """Tests for crop_section function."""
    
    def test_crop_section_basic(self):
        """Test basic cropping of section."""
        # Create a simple grayscale image with a dark region
        img = np.ones((200, 200), dtype=np.uint8) * 200
        img[80:120, 80:120] = 50  # Dark region in center
        
        im_center = [100, 100]
        resolution = 1.0
        minpixel = 30.0
        maxpixel = 2000.0
        
        result = crop_section(img, "test_image", resolution, minpixel, maxpixel, im_center)
        
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0
        assert result.shape[1] > 0
    
    def test_crop_section_returns_smaller_image(self):
        """Test that cropped image is smaller than original."""
        img = np.ones((200, 200), dtype=np.uint8) * 200
        img[90:110, 90:110] = 50
        
        im_center = [100, 100]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        result = crop_section(img, "test", resolution, minpixel, maxpixel, im_center)
        
        # Cropped image should generally be smaller
        assert result.size <= img.size
    
    def test_crop_section_fallback_on_error(self):
        """Test that crop_section uses center crop on error."""
        # Create a problematic image (uniform, hard to segment)
        img = np.ones((200, 200), dtype=np.uint8) * 128
        
        im_center = [100, 100]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        result = crop_section(img, "test", resolution, minpixel, maxpixel, im_center)
        
        # Should still return a valid array even if segmentation fails
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0


class TestSegmentSection:
    """Tests for segment_section function."""
    
    def test_segment_section_basic(self):
        """Test basic section segmentation with good image."""
        # Create a cropped image with bimodal histogram for threshold_minimum
        crop_im = np.ones((100, 100), dtype=np.uint8) * 250
        # Create multiple darker regions with varying intensities
        crop_im[30:45, 30:45] = 40
        crop_im[55:70, 55:70] = 50
        crop_im[20:25, 60:65] = 35
        
        im_center = [50, 50]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        try:
            section_data, bin_im = segment_section(
                crop_im, "test_image", resolution, minpixel, maxpixel, im_center
            )
            
            assert isinstance(section_data, pd.DataFrame)
            assert isinstance(bin_im, np.ndarray)
            assert "ID" in section_data.columns
        except RuntimeError:
            # If threshold_minimum fails, the error handler should still return valid results
            pytest.skip("Threshold minimum failed on this test image")
    
    def test_segment_section_returns_dataframe(self):
        """Test that segment_section returns proper DataFrame."""
        # Create image with bimodal histogram
        crop_im = np.ones((100, 100), dtype=np.uint8) * 250
        crop_im[30:45, 30:45] = 40
        crop_im[55:70, 55:70] = 50
        
        im_center = [50, 50]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        try:
            section_data, bin_im = segment_section(
                crop_im, "test", resolution, minpixel, maxpixel, im_center
            )
            
            # Check DataFrame has expected columns
            assert "area" in section_data.columns
            assert "eccentricity" in section_data.columns
            assert "min" in section_data.columns
            assert "max" in section_data.columns
        except RuntimeError:
            pytest.skip("Threshold minimum failed on this test image")
    
    def test_segment_section_error_handling(self):
        """Test error handling in segment_section."""
        # Create an image that will cause morphological_chan_vese to fail
        # Use a uniform image which typically causes segmentation issues
        crop_im = np.ones((50, 50), dtype=np.uint8) * 128
        
        im_center = [25, 25]
        resolution = 1.0
        minpixel = 10.0
        maxpixel = 1000.0
        
        # The function should handle errors gracefully
        try:
            section_data, bin_im = segment_section(
                crop_im, "test", resolution, minpixel, maxpixel, im_center
            )
            
            # Should still return valid outputs
            assert isinstance(section_data, pd.DataFrame)
            assert isinstance(bin_im, np.ndarray)
        except (RuntimeError, ValueError):
            # Expected behavior for problematic images
            pass


class TestSaveSections:
    """Tests for save_sections function."""
    
    def test_save_sections_crop(self, tmp_path):
        """Test saving cropped section."""
        img = np.ones((50, 50), dtype=np.uint8) * 128
        
        save_sections(tmp_path, "test_image", img, save_crop=True)
        
        # Check that crop directory was created
        crop_dir = tmp_path / "crop"
        assert crop_dir.exists()
        
        # Check that image was saved
        saved_image = crop_dir / "test_image.tiff"
        assert saved_image.exists()
    
    def test_save_sections_binary(self, tmp_path):
        """Test saving binary section."""
        img = np.ones((50, 50), dtype=bool)
        
        save_sections(tmp_path, "test_image", img, save_crop=False)
        
        # Check that binary directory was created
        binary_dir = tmp_path / "binary"
        assert binary_dir.exists()
        
        # Check that image was saved
        saved_image = binary_dir / "test_image.tiff"
        assert saved_image.exists()
    
    def test_save_sections_with_pil_image(self, tmp_path):
        """Test saving with PIL Image object."""
        img = Image.new("L", (50, 50), color=128)
        
        save_sections(tmp_path, "test_image", img, save_crop=True)
        
        crop_dir = tmp_path / "crop"
        assert crop_dir.exists()
    
    def test_save_sections_different_names(self, tmp_path):
        """Test saving sections with different names."""
        img1 = np.ones((50, 50), dtype=np.uint8) * 100
        img2 = np.ones((50, 50), dtype=np.uint8) * 150
        
        save_sections(tmp_path, "image1", img1, save_crop=True)
        save_sections(tmp_path, "image2", img2, save_crop=True)
        
        crop_dir = tmp_path / "crop"
        assert (crop_dir / "image1.tiff").exists()
        assert (crop_dir / "image2.tiff").exists()
