"""Unit tests for utils.metadata module."""

import os
import tempfile

import pytest

from fibermorph.utils.metadata import parse_canonical_name, collect_images


class TestParseCanonicalName:
    """Tests for the lenient canonical Individual_Sample_Side parser."""

    def test_full_convention(self):
        result = parse_canonical_name("Y_5_B.tif")
        assert result == {"individual": "Y", "sample": "5", "side": "B"}

    def test_strips_path_and_extension(self):
        result = parse_canonical_name("/some/path/P_3_A.tiff")
        assert result["individual"] == "P"
        assert result["sample"] == "3"
        assert result["side"] == "A"

    def test_extra_tokens_are_dropped(self):
        # trailing acquisition info after Side is ignored
        result = parse_canonical_name("Y_5_B_12.5mag.tif")
        assert result == {"individual": "Y", "sample": "5", "side": "B"}

    def test_missing_side(self):
        result = parse_canonical_name("Y_5.tif")
        assert result == {"individual": "Y", "sample": "5", "side": ""}

    def test_missing_sample_and_side(self):
        result = parse_canonical_name("Y.tif")
        assert result == {"individual": "Y", "sample": "", "side": ""}

    def test_non_conforming_name_still_parses(self):
        # never raises; whatever precedes the first underscore is the individual
        result = parse_canonical_name("randomname.tif")
        assert result["individual"] == "randomname"
        assert result["sample"] == ""
        assert result["side"] == ""

    def test_always_returns_three_keys(self):
        result = parse_canonical_name("anything.tif")
        assert set(result) == {"individual", "sample", "side"}


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
