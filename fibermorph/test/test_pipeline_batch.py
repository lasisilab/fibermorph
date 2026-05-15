"""Unit tests for pipeline.batch module (metadata parsing and per-sample aggregation)."""

import numpy as np
import pandas as pd
import pytest

from fibermorph.pipeline.batch import _aggregate_per_sample


class TestAggregatePerSample:
    """Tests for the per-sample aggregation logic."""

    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"sample_id": "140025", "region": "A", "image_type": "section",
             "area_mu2": 100.0, "circularity": 0.90, "shape_class": "Circular"},
            {"sample_id": "140025", "region": "A", "image_type": "section",
             "area_mu2": 110.0, "circularity": 0.88, "shape_class": "Circular"},
            {"sample_id": "140025", "region": "A", "image_type": "section",
             "area_mu2": 105.0, "circularity": 0.92, "shape_class": "Elliptical"},
            {"sample_id": "140025", "region": "B", "image_type": "section",
             "area_mu2": 200.0, "circularity": 0.70, "shape_class": "Flattened"},
            {"sample_id": "200001", "region": "A", "image_type": "curvature",
             "curv_mean": 0.5, "curl_index": 1.2, "shape_class": None},
        ])

    def test_returns_dataframe(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        assert isinstance(result, pd.DataFrame)

    def test_number_of_groups(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        # 3 unique (sample_id, region, image_type) combos
        assert len(result) == 3

    def test_mean_columns_exist(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        assert "area_mu2_mean" in result.columns
        assert "circularity_mean" in result.columns

    def test_std_columns_exist(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        assert "area_mu2_std" in result.columns

    def test_n_valid_column_exists(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        assert "n_valid" in result.columns

    def test_mean_values_correct(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        row = result[
            (result["sample_id"] == "140025") &
            (result["region"] == "A") &
            (result["image_type"] == "section")
        ]
        assert len(row) == 1
        expected_mean = (100.0 + 110.0 + 105.0) / 3
        assert abs(row.iloc[0]["area_mu2_mean"] - expected_mean) < 1e-6

    def test_shape_class_mode(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        if "shape_class_mode" in result.columns:
            row = result[
                (result["sample_id"] == "140025") &
                (result["region"] == "A") &
                (result["image_type"] == "section")
            ]
            # "Circular" appears twice vs "Elliptical" once
            assert row.iloc[0]["shape_class_mode"] == "Circular"

    def test_n_valid_counts(self):
        df = self._make_df()
        result = _aggregate_per_sample(df)
        row = result[
            (result["sample_id"] == "140025") &
            (result["region"] == "A") &
            (result["image_type"] == "section")
        ]
        assert row.iloc[0]["n_valid"] == 3

    def test_empty_dataframe_returns_empty(self):
        result = _aggregate_per_sample(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_no_group_keys_returns_empty(self):
        df = pd.DataFrame([{"area_mu2": 100, "circularity": 0.9}])
        result = _aggregate_per_sample(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
