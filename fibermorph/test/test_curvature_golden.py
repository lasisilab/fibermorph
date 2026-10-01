"""Golden tests: curvature results must equal those of the published method.

The reference CSV files in test_data/curv_golden/ were produced by the
original fibermorph v0.3.1 code (the version behind the published results)
running under scikit-image 0.16.2; see test_data/curv_golden/README.md for
exactly how. These tests run the current ``curvature_seq`` and require the
same numbers, for a window in pixels, a window in mm, and the whole-hair
mode (``window_size=None``), both per hair (``test=True``) and as image
summary (``test=False``). They use the default option
(``extended_curvature=False``); the extended-curvature option is not part of
the v0.3.1 method and is not compared here.

* TestSyntheticImageGolden: offline, uses a small synthetic PNG kept in the
  repository.
* TestDemoImagesGolden: downloads the two lab demo curvature images (about
  6 MB in total, each fetched once per test run) and is skipped when they
  cannot be downloaded. Set FIBERMORPH_DEMO_CURV_DIR to a folder that already
  holds the two TIFF files to use them without downloading.
"""

import os
import pathlib

import numpy as np
import pandas as pd
import pytest

from fibermorph.analysis.curvature_pipeline import curvature_seq

GOLDEN = pathlib.Path(__file__).parent / "test_data" / "curv_golden"
SYNTHETIC_IMAGE = GOLDEN / "synthetic_curv.png"
SYNTHETIC_REFERENCE = GOLDEN / "reference_v031"
DEMO_REFERENCE = GOLDEN / "reference_demo_v031"

RESOLUTION = 132  # pixels per mm, as used for the references

# window text used in the reference file names -> (window_size, window_unit)
WINDOWS = {
    "50px": (50, "px"),
    "none": (None, "px"),
    "0.5mm": (0.5, "mm"),
}

RTOL = 1e-9
ATOL = 1e-12


def _read_reference(directory, stem, window_text, kind):
    path = directory / f"{stem}__window{window_text}__{kind}.csv"
    return pd.read_csv(path, float_precision="round_trip")


def _run(image_path, workdir, window_text, test):
    window_size, window_unit = WINDOWS[window_text]
    return curvature_seq(
        str(image_path),
        str(workdir),
        resolution=RESOLUTION,
        window_size=window_size,
        window_unit=window_unit,
        save_img=False,
        test=test,
        within_element=False,
    )


def _assert_per_hair_equal(actual, expected):
    """Same columns, same number of hairs, same numbers, rows in the same order.

    The row order is the order of the labelled hairs (skimage regionprops), which
    is deterministic and is the order v0.3.1 wrote them in.
    """
    actual = pd.DataFrame(actual).reset_index(drop=True)
    assert list(actual.columns) == list(expected.columns)
    assert len(actual) == len(expected)
    np.testing.assert_allclose(
        actual.to_numpy(float), expected.to_numpy(float), rtol=RTOL, atol=ATOL
    )


def _assert_summary_equal(actual, expected):
    actual = pd.DataFrame(actual).reset_index(drop=True)
    assert list(actual.columns) == list(expected.columns)
    assert len(actual) == len(expected) == 1
    assert actual["ID"].iloc[0] == expected["ID"].iloc[0]
    assert actual["hair_count"].iloc[0] == expected["hair_count"].iloc[0]
    numeric = [c for c in expected.columns if c != "ID"]
    np.testing.assert_allclose(
        actual[numeric].to_numpy(float),
        expected[numeric].to_numpy(float),
        rtol=RTOL,
        atol=ATOL,
    )


@pytest.mark.parametrize("window_text", ["50px", "none", "0.5mm"])
class TestSyntheticImageGolden:
    """Synthetic image: dark arcs of several radii plus near-straight lines."""

    def test_per_hair_rows_match_v031(self, tmp_path, window_text):
        expected = _read_reference(SYNTHETIC_REFERENCE, "synthetic_curv", window_text, "perhair")
        actual = _run(SYNTHETIC_IMAGE, tmp_path, window_text, test=True)
        _assert_per_hair_equal(actual, expected)

    def test_image_summary_matches_v031(self, tmp_path, window_text):
        expected = _read_reference(SYNTHETIC_REFERENCE, "synthetic_curv", window_text, "summary")
        actual = _run(SYNTHETIC_IMAGE, tmp_path, window_text, test=False)
        _assert_summary_equal(actual, expected)


class TestValidationCurvCallPath:
    """fibermorph.demo.demo.validation_curv calls curvature_seq(test=True) and
    reads the per-hair columns ``length`` and ``curv_median``."""

    def test_test_true_returns_per_hair_rows_with_columns_validation_uses(self, tmp_path):
        result = _run(SYNTHETIC_IMAGE, tmp_path, "50px", test=True)

        assert isinstance(result, pd.DataFrame)
        assert {"length", "curv_median"} <= set(result.columns)
        assert "hair_count" not in result.columns  # not the image summary
        assert len(result) > 1  # one row per hair

        # the same operations validation_curv performs on the result
        per_hair = pd.DataFrame(result).sort_values(by=["length"], ignore_index=True)
        per_hair["radius"] = 1 / per_hair["curv_median"]
        assert per_hair["length"].is_monotonic_increasing

    def test_test_false_returns_image_summary(self, tmp_path):
        result = _run(SYNTHETIC_IMAGE, tmp_path, "50px", test=False)
        assert len(result) == 1
        assert "hair_count" in result.columns


# ---------------------------------------------------------------------------
# Online golden test on the lab's demo images
# ---------------------------------------------------------------------------

DEMO_BASE_URL = (
    "https://github.com/tinalasisi/fibermorph_DemoData/raw/master/test_input/curv/"
)
DEMO_IMAGES = {
    "004_demo_curv": "004_demo_curv.tiff",
    "027_demo_nocurv": "027_demo_nocurv.tiff",
}
_TIFF_MAGIC = (b"II*\x00", b"MM\x00*")


def _fetch_demo_image(file_name, dest_dir, base_url=DEMO_BASE_URL):
    """Return a local path to a demo image, downloading it if necessary.

    Uses FIBERMORPH_DEMO_CURV_DIR when that folder already holds the file, and
    a copy already downloaded into dest_dir by an earlier call (so each image
    is fetched once per test run). Skips the calling test if the file cannot
    be downloaded or is not a TIFF.
    """
    local_dir = os.environ.get("FIBERMORPH_DEMO_CURV_DIR")
    if local_dir and (pathlib.Path(local_dir) / file_name).is_file():
        return pathlib.Path(local_dir) / file_name

    path = pathlib.Path(dest_dir) / file_name
    if path.is_file():
        return path

    import requests

    try:
        response = requests.get(base_url + file_name, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        pytest.skip(f"could not download {file_name}: {exc}")
    if not response.content.startswith(_TIFF_MAGIC):
        pytest.skip(f"downloaded {file_name} is not a TIFF file")

    path.write_bytes(response.content)
    return path


@pytest.fixture(scope="module")
def demo_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("demo_curv")


class TestDownloadHelper:
    def test_downloaded_file_is_reused_not_fetched_again(self, tmp_path, monkeypatch):
        import requests

        monkeypatch.delenv("FIBERMORPH_DEMO_CURV_DIR", raising=False)
        calls = []

        class FakeResponse:
            content = b"II*\x00 fake tiff bytes"

            def raise_for_status(self):
                pass

        def fake_get(url, timeout):
            calls.append(url)
            return FakeResponse()

        monkeypatch.setattr(requests, "get", fake_get)

        first = _fetch_demo_image("y.tiff", tmp_path, base_url="http://example.invalid/")
        second = _fetch_demo_image("y.tiff", tmp_path, base_url="http://example.invalid/")

        assert first == second == tmp_path / "y.tiff"
        assert calls == ["http://example.invalid/y.tiff"]  # one download, not two

    def test_unreachable_server_skips(self, tmp_path):
        with pytest.raises(pytest.skip.Exception):
            _fetch_demo_image("none.tiff", tmp_path, base_url="http://127.0.0.1:9/")

    def test_local_folder_is_used_without_download(self, tmp_path, monkeypatch):
        local_dir = tmp_path / "local"
        dest_dir = tmp_path / "dest"
        local_dir.mkdir()
        dest_dir.mkdir()
        (local_dir / "x.tiff").write_bytes(b"II*\x00")
        monkeypatch.setenv("FIBERMORPH_DEMO_CURV_DIR", str(local_dir))
        assert _fetch_demo_image("x.tiff", dest_dir, base_url="http://127.0.0.1:9/") == (
            local_dir / "x.tiff"
        )


@pytest.mark.parametrize("stem", sorted(DEMO_IMAGES))
@pytest.mark.parametrize("window_text", ["50px", "none"])
class TestDemoImagesGolden:
    """Curly (004) and straight (027) demo hair images at 132 px/mm."""

    def test_per_hair_rows_match_v031(self, tmp_path, demo_dir, stem, window_text):
        image = _fetch_demo_image(DEMO_IMAGES[stem], demo_dir)
        expected = _read_reference(DEMO_REFERENCE, stem, window_text, "perhair")
        actual = _run(image, tmp_path, window_text, test=True)
        _assert_per_hair_equal(actual, expected)

    def test_image_summary_matches_v031(self, tmp_path, demo_dir, stem, window_text):
        image = _fetch_demo_image(DEMO_IMAGES[stem], demo_dir)
        expected = _read_reference(DEMO_REFERENCE, stem, window_text, "summary")
        actual = _run(image, tmp_path, window_text, test=False)
        _assert_summary_equal(actual, expected)
