"""Unit tests for pipeline.batch — per-image output with canonical labels.

The batch pipeline no longer aggregates per sample; it emits one row per source
image (with the filename and lenient individual/sample/side labels) and leaves
grouping to downstream analysis.
"""

import os

import numpy as np
import pandas as pd
from PIL import Image
from skimage import draw as sk_draw

from fibermorph.pipeline.batch import run_batch


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

    def test_labels_and_source_file_columns(self, tmp_path):
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
        assert row["individual"] == "Y"
        assert row["sample"] == "5"
        assert row["side"] == "B"
        # no legacy grouping columns
        for legacy in ("sample_id", "region", "replicate"):
            assert legacy not in result.columns

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
