"""Unit tests for utils.metadata module."""

import os
import tempfile

import pytest

from fibermorph.utils.metadata import collect_images


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
