"""Unit tests for utils.filesystem module."""

import os
import pathlib
import tempfile
import shutil
import pytest
from fibermorph.utils.filesystem import make_subdirectory, copy_if_exist, list_images


class TestMakeSubdirectory:
    """Tests for make_subdirectory function."""
    
    def test_make_subdirectory_creates_new_directory(self, tmp_path):
        """Test creating a new subdirectory."""
        result = make_subdirectory(tmp_path, "test_dir")
        assert result.exists()
        assert result.is_dir()
        assert result.name == "test_dir"
    
    def test_make_subdirectory_returns_pathlib_path(self, tmp_path):
        """Test that result is a pathlib.Path object."""
        result = make_subdirectory(tmp_path, "test_dir")
        assert isinstance(result, pathlib.Path)
    
    def test_make_subdirectory_with_existing_directory(self, tmp_path):
        """Test with already existing directory."""
        # Create directory first
        test_dir = tmp_path / "existing_dir"
        test_dir.mkdir()
        
        # Call function on existing directory
        result = make_subdirectory(tmp_path, "existing_dir")
        assert result.exists()
        assert result == test_dir
    
    def test_make_subdirectory_with_string_path(self, tmp_path):
        """Test with string path instead of pathlib.Path."""
        result = make_subdirectory(str(tmp_path), "test_dir")
        assert result.exists()
        assert isinstance(result, pathlib.Path)
    
    def test_make_subdirectory_with_nested_path(self, tmp_path):
        """Test creating nested subdirectories."""
        result = make_subdirectory(tmp_path, "level1/level2")
        assert result.exists()
        assert result.is_dir()


class TestCopyIfExist:
    """Tests for copy_if_exist function."""
    
    def test_copy_if_exist_with_existing_file(self, tmp_path):
        """Test copying an existing file."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        
        # Create destination directory
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        # Copy file
        result = copy_if_exist(source_file, dest_dir)
        assert result is True
        assert (dest_dir / "source.txt").exists()
        assert (dest_dir / "source.txt").read_text() == "test content"
    
    def test_copy_if_exist_with_nonexistent_file(self, tmp_path):
        """Test copying a non-existent file."""
        source_file = tmp_path / "nonexistent.txt"
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        result = copy_if_exist(source_file, dest_dir)
        assert result is False
        assert not (dest_dir / "nonexistent.txt").exists()
    
    def test_copy_if_exist_with_string_paths(self, tmp_path):
        """Test with string paths instead of pathlib.Path."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        result = copy_if_exist(str(source_file), str(dest_dir))
        assert result is True
        assert (dest_dir / "source.txt").exists()


def _make_tiff(path):
    """Write a minimal valid TIFF image (list_images verifies files with PIL)."""
    from PIL import Image
    Image.new("L", (4, 4)).save(path, format="TIFF")


class TestListImages:
    """Tests for list_images function."""

    def test_list_images_with_tif_files(self, tmp_path):
        """Test listing .tif files."""
        # Create test files
        _make_tiff(tmp_path / "image1.tif")
        _make_tiff(tmp_path / "image2.tif")
        (tmp_path / "other.txt").touch()

        result = list_images(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".tif" for p in result)

    def test_list_images_with_tiff_files(self, tmp_path):
        """Test listing .tiff files."""
        # Create test files
        _make_tiff(tmp_path / "image1.tiff")
        _make_tiff(tmp_path / "image2.tiff")

        result = list_images(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".tiff" for p in result)

    def test_list_images_with_mixed_extensions(self, tmp_path):
        """Test listing both .tif and .tiff files."""
        # Create test files
        _make_tiff(tmp_path / "image1.tif")
        _make_tiff(tmp_path / "image2.tiff")
        (tmp_path / "image3.jpg").touch()

        result = list_images(tmp_path)
        assert len(result) == 2
        assert all(p.suffix in [".tif", ".tiff"] for p in result)

    def test_list_images_with_nested_directories(self, tmp_path):
        """Test listing images in nested directories."""
        # Create nested structure
        nested_dir = tmp_path / "subdir"
        nested_dir.mkdir()
        _make_tiff(tmp_path / "image1.tif")
        _make_tiff(nested_dir / "image2.tif")

        result = list_images(tmp_path)
        assert len(result) == 2

    def test_list_images_with_empty_directory(self, tmp_path):
        """Test listing images in empty directory."""
        result = list_images(tmp_path)
        assert len(result) == 0
        assert isinstance(result, list)

    def test_list_images_skips_invalid_image_files(self, tmp_path):
        """Files with a .tif extension that are not real images are excluded."""
        _make_tiff(tmp_path / "valid.tif")
        (tmp_path / "corrupt.tif").write_bytes(b"not a real tiff")
        (tmp_path / "empty.tif").touch()
        (tmp_path / "._appledouble.tif").write_bytes(b"\x00\x05\x16\x07")

        result = list_images(tmp_path)
        assert [p.name for p in result] == ["valid.tif"]

    def test_list_images_sorted(self, tmp_path):
        """Test that results are sorted."""
        # Create files in non-alphabetical order
        _make_tiff(tmp_path / "c.tif")
        _make_tiff(tmp_path / "a.tif")
        _make_tiff(tmp_path / "b.tif")

        result = list_images(tmp_path)
        names = [p.name for p in result]
        assert names == sorted(names)

    def test_list_images_with_string_path(self, tmp_path):
        """Test with string path instead of pathlib.Path."""
        _make_tiff(tmp_path / "image1.tif")

        result = list_images(str(tmp_path))
        assert len(result) == 1
        assert isinstance(result[0], pathlib.Path)
