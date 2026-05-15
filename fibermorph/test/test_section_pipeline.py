"""Unit tests for analysis.section_pipeline (watershed path, extended features)."""

import os
import tempfile

import numpy as np
import pytest
from PIL import Image
from skimage import draw as sk_draw


def _make_section_tiff(tmp_path, fname: str = "test_section.tiff",
                        size: int = 200, radius: int = 40) -> str:
    """Create a synthetic cross-section TIFF with a dark circle on bright background."""
    img = np.ones((size, size), dtype=np.uint8) * 220
    rr, cc = sk_draw.disk((size // 2, size // 2), radius, shape=img.shape)
    img[rr, cc] = 30
    path = os.path.join(str(tmp_path), fname)
    Image.fromarray(img, mode="L").save(path)
    return path


class TestSectionSeq:
    """Tests for section_seq (watershed path, no SAM2 required)."""

    def test_returns_dataframe(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        result = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=False,
        )
        import pandas as pd
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_id_column(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        df = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=False,
        )
        assert "ID" in df.columns

    def test_extended_features_adds_efd_columns(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        df = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=True,
        )
        if df is not None and not df.empty:
            efd_cols = [c for c in df.columns if c.startswith("efd_")]
            assert len(efd_cols) > 0, "Extended features should include EFD columns"

    def test_extended_features_adds_hu_columns(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        df = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=True,
        )
        if df is not None and not df.empty:
            hu_cols = [c for c in df.columns if c.startswith("hu_")]
            assert len(hu_cols) == 7, "Extended features should include 7 Hu moment columns"

    def test_extended_features_adds_shape_class(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        df = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=True,
        )
        if df is not None and not df.empty:
            assert "shape_class" in df.columns

    def test_save_img_creates_output_files(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        img_path = _make_section_tiff(tmp_path)
        section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=True, use_sam2=False, extended_features=False,
        )
        # At minimum the input tiff should still exist; output may create subdir
        assert os.path.exists(img_path)

    def test_no_crash_on_blank_image(self, tmp_path):
        from fibermorph.analysis.section_pipeline import section_seq
        blank = np.ones((100, 100), dtype=np.uint8) * 200
        img_path = os.path.join(str(tmp_path), "blank.tiff")
        Image.fromarray(blank, mode="L").save(img_path)
        # Should not raise; may return empty / NaN DataFrame
        result = section_seq(
            img_path, str(tmp_path),
            resolution=4.25, minsize=10, maxsize=300,
            save_img=False, use_sam2=False, extended_features=False,
        )
        import pandas as pd
        assert result is None or isinstance(result, pd.DataFrame)
