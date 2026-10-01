"""Unit tests for analysis.curvature_pipeline (extended curvature)."""

import os

import numpy as np
import pytest
from PIL import Image
from skimage import draw as sk_draw


def _make_curv_tiff(tmp_path, fname: str = "test_curv.tiff",
                    size: int = 200, amplitude: int = 30) -> str:
    """Create a synthetic curvature TIFF with a wavy dark line on bright background."""
    img = np.ones((size, size), dtype=np.uint8) * 230
    for x in range(size):
        y = int(size // 2 + amplitude * np.sin(2 * np.pi * 3 * x / size))
        y = np.clip(y, 2, size - 3)
        img[y - 2:y + 2, x] = 20
    path = os.path.join(str(tmp_path), fname)
    Image.fromarray(img, mode="L").save(path)
    return path


class TestCurvatureSeq:
    """Tests for curvature_seq (standard and extended output)."""

    def test_returns_dataframe(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        result = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
            extended_curvature=False,
        )
        import pandas as pd
        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_curvature_columns(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        df = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
            extended_curvature=False,
        )
        if df is not None and not df.empty:
            assert any(c in df.columns for c in ["curv_mean", "mean", "median"])

    def test_extended_curvature_adds_curl_index(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        df = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
            extended_curvature=True,
        )
        if df is not None and not df.empty:
            assert "curl_index" in df.columns, "Extended curvature must include curl_index"

    def test_extended_curvature_adds_wave_count(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        df = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
            extended_curvature=True,
        )
        if df is not None and not df.empty:
            assert "wave_count" in df.columns, "Extended curvature must include wave_count"

    def test_no_crash_on_blank_image(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        blank = np.ones((100, 100), dtype=np.uint8) * 200
        img_path = os.path.join(str(tmp_path), "blank.tiff")
        Image.fromarray(blank, mode="L").save(img_path)
        import pandas as pd
        result = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
            extended_curvature=False,
        )
        assert result is None or isinstance(result, pd.DataFrame)


class TestRemovedOptions:
    """CLAHE preprocessing is no longer an option anywhere in the API."""

    @pytest.mark.parametrize("dotted", [
        "fibermorph.analysis.curvature_pipeline.curvature_seq",
        "fibermorph.workflows.curvature",
        "fibermorph.workflows.batch",
        "fibermorph.pipeline.batch.run_batch",
    ])
    def test_functions_have_no_clahe_parameter(self, dotted):
        import importlib
        import inspect
        module_name, func_name = dotted.rsplit(".", 1)
        func = getattr(importlib.import_module(module_name), func_name)
        assert "use_clahe" not in inspect.signature(func).parameters

    def test_curvature_seq_rejects_use_clahe(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        with pytest.raises(TypeError):
            curvature_seq(
                img_path, str(tmp_path),
                resolution=132, window_size=None, window_unit="px",
                save_img=False, test=False, within_element=False,
                use_clahe=True,
            )

    def test_filter_curv_clahe_is_gone(self):
        import fibermorph
        import fibermorph.core.filters as filters
        assert not hasattr(filters, "filter_curv_clahe")
        assert not hasattr(fibermorph, "filter_curv_clahe")
        assert "filter_curv_clahe" not in fibermorph.__all__
