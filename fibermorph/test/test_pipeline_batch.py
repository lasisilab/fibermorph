"""Unit tests for pipeline.batch — per-image output with canonical labels.

The batch pipeline no longer aggregates per sample; it emits one row per source
image (carrying the source filename) and leaves all grouping to downstream
analysis.
"""

import os
import pathlib
import shutil

import numpy as np
import pandas as pd
import pytest
from PIL import Image
from skimage import draw as sk_draw

from fibermorph.pipeline.batch import run_batch

GOLDEN = pathlib.Path(__file__).parent / "test_data" / "curv_golden"


def _make_section_tiff(path: str, size: int = 200, radius: int = 40) -> None:
    """A dark disk on a bright field — segments with the classical watershed."""
    img = np.ones((size, size), dtype=np.uint8) * 220
    rr, cc = sk_draw.disk((size // 2, size // 2), radius, shape=img.shape)
    img[rr, cc] = 30
    Image.fromarray(img, mode="L").save(path)


class TestRunBatchPerImage:
    def test_per_image_only_no_per_sample(self, tmp_path):
        sec_dir = tmp_path / "sections"
        out_dir = tmp_path / "out"
        sec_dir.mkdir()
        out_dir.mkdir()
        # canonical names: Individual_Sample_Side
        _make_section_tiff(str(sec_dir / "Y_5_A.tiff"))
        _make_section_tiff(str(sec_dir / "Y_5_B.tiff"))

        result = run_batch(
            section_dir=str(sec_dir), curv_dir=None, output_dir=str(out_dir),
            resolution_mu=4.25, min_diam=10, max_diam=300,
            use_sam2=False, extended_features=False,
        )

        # returns a single per-image DataFrame (not a tuple)
        assert isinstance(result, pd.DataFrame)
        assert not isinstance(result, tuple)
        assert len(result) == 2

        # per-image CSV written; per-sample CSV must NOT exist
        assert (out_dir / "hair_analysis_per_image.csv").exists()
        assert not (out_dir / "hair_analysis_per_sample.csv").exists()

    def test_source_file_recorded_no_grouping_columns(self, tmp_path):
        sec_dir = tmp_path / "sections"
        out_dir = tmp_path / "out"
        sec_dir.mkdir()
        out_dir.mkdir()
        _make_section_tiff(str(sec_dir / "Y_5_B.tiff"))

        result = run_batch(
            section_dir=str(sec_dir), curv_dir=None, output_dir=str(out_dir),
            resolution_mu=4.25, min_diam=10, max_diam=300,
            use_sam2=False, extended_features=False,
        )
        row = result.iloc[0]
        assert row["source_file"] == "Y_5_B.tiff"
        # the app does not parse filenames into grouping columns
        for col in ("individual", "sample", "side", "sample_id", "region", "replicate"):
            assert col not in result.columns

    def test_empty_input_returns_empty_dataframe(self, tmp_path):
        sec_dir = tmp_path / "sections"
        out_dir = tmp_path / "out"
        sec_dir.mkdir()
        out_dir.mkdir()
        result = run_batch(
            section_dir=str(sec_dir), curv_dir=None, output_dir=str(out_dir),
            use_sam2=False, extended_features=False,
        )
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestBatchCurvatureUsesPublishedMethod:
    """Batch curvature output equals the published (v0.3.1) numbers.

    The reference summary in test_data/curv_golden/ was produced by the
    original fibermorph v0.3.1 code (see the README there); batch adds only
    the image_type and source_file labels.
    """

    @staticmethod
    def _curv_dir(tmp_path):
        curv_dir = tmp_path / "curvature"
        curv_dir.mkdir()
        shutil.copy(GOLDEN / "synthetic_curv.png", curv_dir / "synthetic_curv.png")
        return curv_dir

    @staticmethod
    def _expected():
        return pd.read_csv(
            GOLDEN / "reference_v031" / "synthetic_curv__window50px__summary.csv",
            float_precision="round_trip",
        )

    @classmethod
    def _assert_published_row(cls, row):
        expected = cls._expected().iloc[0]
        assert row["image_type"] == "curvature"
        assert row["source_file"] == "synthetic_curv.png"
        assert row["ID"] == expected["ID"]
        for col in expected.index.drop("ID"):
            assert row[col] == pytest.approx(expected[col], rel=1e-9)

    def test_run_batch_curvature_matches_published_method(self, tmp_path):
        out_dir = tmp_path / "out"
        result = run_batch(
            section_dir=None, curv_dir=str(self._curv_dir(tmp_path)),
            output_dir=str(out_dir), resolution_mm=132, window_size=50,
            window_unit="px",
        )
        assert len(result) == 1
        self._assert_published_row(result.iloc[0])
        # only the published summary columns (plus the two labels)
        assert set(result.columns) == set(self._expected().columns) | {
            "image_type", "source_file"}

    def test_workflows_batch_curvature_writes_published_columns(self, tmp_path):
        from fibermorph.workflows import batch

        assert batch(None, str(self._curv_dir(tmp_path)), str(tmp_path / "out"),
                     resolution_mm=132, window_size=50, window_unit="px")
        (csv,) = (tmp_path / "out").glob("*fibermorph_batch/hair_analysis_per_image.csv")
        written = pd.read_csv(csv)
        assert len(written) == 1
        self._assert_published_row(written.iloc[0])
        for removed in ("curl_index", "curl_index_std", "wave_count",
                        "wave_count_per_mm", "length_total"):
            assert removed not in written.columns
