"""Unit tests for analysis.curvature_pipeline."""

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
    """Tests for curvature_seq."""

    def test_returns_dataframe(self, tmp_path):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        result = curvature_seq(
            img_path, str(tmp_path),
            resolution=132, window_size=None, window_unit="px",
            save_img=False, test=False, within_element=False,
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
        )
        if df is not None and not df.empty:
            assert any(c in df.columns for c in ["curv_mean", "mean", "median"])

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
        )
        assert result is None or isinstance(result, pd.DataFrame)


REMOVED_PARAMETERS = ("use_clahe", "extended_curvature")


class TestRemovedOptions:
    """CLAHE preprocessing and extended curvature are no longer options."""

    @pytest.mark.parametrize("dotted", [
        "fibermorph.analysis.curvature_pipeline.curvature_seq",
        "fibermorph.workflows.curvature",
        "fibermorph.workflows.batch",
        "fibermorph.pipeline.batch.run_batch",
    ])
    def test_functions_have_no_removed_parameters(self, dotted):
        import importlib
        import inspect
        module_name, func_name = dotted.rsplit(".", 1)
        func = getattr(importlib.import_module(module_name), func_name)
        parameters = inspect.signature(func).parameters
        for name in REMOVED_PARAMETERS:
            assert name not in parameters

    @pytest.mark.parametrize("name", REMOVED_PARAMETERS)
    def test_curvature_seq_rejects_removed_parameters(self, tmp_path, name):
        from fibermorph.analysis.curvature_pipeline import curvature_seq
        img_path = _make_curv_tiff(tmp_path)
        with pytest.raises(TypeError):
            curvature_seq(
                img_path, str(tmp_path),
                resolution=132, window_size=None, window_unit="px",
                save_img=False, test=False, within_element=False,
                **{name: True},
            )

    @pytest.mark.parametrize("module_name, func_name", [
        ("fibermorph.core.filters", "filter_curv_clahe"),
        ("fibermorph.core.curvature", "curl_index_from_skeleton"),
        ("fibermorph.core.curvature", "wave_count"),
        ("fibermorph.core.curvature", "pixel_length_correction_coords"),
    ])
    def test_removed_functions_are_gone(self, module_name, func_name):
        import importlib
        import fibermorph
        assert not hasattr(importlib.import_module(module_name), func_name)
        assert not hasattr(fibermorph, func_name)
        assert func_name not in fibermorph.__all__
