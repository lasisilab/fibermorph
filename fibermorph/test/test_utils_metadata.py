"""Unit tests for utils.metadata module."""

import os
import tempfile

import pytest

from fibermorph.utils.metadata import parse_metadata, collect_images


class TestParseMetadata:
    """Tests for parse_metadata filename parser."""

    def test_standard_format(self):
        result = parse_metadata("140025_A_3.tiff")
        assert result["sample_id"] == "140025"
        assert result["region"] == "A"
        assert result["replicate"] == "3"

    def test_standard_format_case_insensitive_region(self):
        result = parse_metadata("140025_b_1.tiff")
        assert result["region"] == "B"

    def test_standard_format_strip_extension(self):
        result = parse_metadata("/some/path/200001_C_2.tif")
        assert result["sample_id"] == "200001"
        assert result["region"] == "C"
        assert result["replicate"] == "2"

    def test_p_prefix_format(self):
        result = parse_metadata("P1200851.tiff")
        assert result["sample_id"] == "P1200851"
        assert result["region"] == ""
        assert result["replicate"] == ""

    def test_p_prefix_case_insensitive(self):
        result = parse_metadata("p9876543.tif")
        assert result["sample_id"].lower().startswith("p")

    def test_unknown_format_uses_stem(self):
        result = parse_metadata("random_image_name.tiff")
        assert result["sample_id"] == "random_image_name"
        assert result["region"] == ""
        assert result["replicate"] == ""

    def test_returns_dict_with_required_keys(self):
        result = parse_metadata("anything.tif")
        assert "sample_id" in result
        assert "region" in result
        assert "replicate" in result

    def test_standard_multi_digit_replicate(self):
        result = parse_metadata("100000_A_10.tiff")
        assert result["replicate"] == "10"


class TestCollectImages:
    """Tests for collect_images directory scanner."""

    def test_finds_tiff_files(self, tmp_path):
        (tmp_path / "a.tiff").write_bytes(b"")
        (tmp_path / "b.tif").write_bytes(b"")
        (tmp_path / "c.txt").write_bytes(b"")
        paths = collect_images(str(tmp_path))
        names = [os.path.basename(p) for p in paths]
        assert "a.tiff" in names
        assert "b.tif" in names
        assert "c.txt" not in names

    def test_returns_sorted_list(self, tmp_path):
        for name in ["z.tiff", "a.tiff", "m.tiff"]:
            (tmp_path / name).write_bytes(b"")
        paths = collect_images(str(tmp_path))
        names = [os.path.basename(p) for p in paths]
        assert names == sorted(names)

    def test_empty_directory(self, tmp_path):
        paths = collect_images(str(tmp_path))
        assert paths == []

    def test_custom_extensions(self, tmp_path):
        (tmp_path / "a.png").write_bytes(b"")
        (tmp_path / "b.tiff").write_bytes(b"")
        paths = collect_images(str(tmp_path), extensions={".png"})
        names = [os.path.basename(p) for p in paths]
        assert "a.png" in names
        assert "b.tiff" not in names

    def test_returns_full_paths(self, tmp_path):
        (tmp_path / "img.tiff").write_bytes(b"")
        paths = collect_images(str(tmp_path))
        assert len(paths) == 1
        assert os.path.isabs(paths[0])
