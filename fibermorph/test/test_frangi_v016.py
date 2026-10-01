"""Tests for the frozen scikit-image 0.16.2 Frangi filter (core.frangi_v016).

The reference arrays were produced by the real scikit-image 0.16.2 (see
test_data/frangi_v016/make_frangi_reference.py), so these tests fail if the
installed scikit-image's frangi (whose output differs) is used instead.
"""

import pathlib

import numpy as np
import pytest
from PIL import Image

from fibermorph.core.filters import filter_curv
from fibermorph.core.frangi_v016 import frangi_v016

DATA = pathlib.Path(__file__).parent / "test_data" / "frangi_v016"


@pytest.fixture(scope="module")
def input_uint8():
    return np.load(DATA / "input_uint8.npy")


def _assert_matches(out, ref):
    """Tight match: rtol 1e-9, atol scaled to the reference maximum."""
    assert out.shape == ref.shape
    np.testing.assert_allclose(out, ref, rtol=1e-9, atol=1e-9 * ref.max())


class TestFrangiV016Reference:
    def test_default_settings_uint8(self, input_uint8):
        ref = np.load(DATA / "ref_default.npy")
        _assert_matches(frangi_v016(input_uint8), ref)

    def test_float_input(self, input_uint8):
        ref = np.load(DATA / "ref_float64.npy")
        _assert_matches(frangi_v016(input_uint8 / 255.0), ref)

    def test_white_ridges_and_custom_sigmas(self, input_uint8):
        ref = np.load(DATA / "ref_white_sigmas.npy")
        out = frangi_v016(input_uint8, sigmas=[1, 2, 3.5], black_ridges=False)
        _assert_matches(out, ref)

    def test_reference_is_not_trivial(self):
        ref = np.load(DATA / "ref_default.npy")
        assert ref.max() > 0
        assert np.count_nonzero(ref) > 100

    def test_output_is_float64_same_shape(self, input_uint8):
        out = frangi_v016(input_uint8)
        assert out.dtype == np.float64
        assert out.shape == input_uint8.shape

    def test_rejects_non_2d_input(self):
        with pytest.raises(ValueError):
            frangi_v016(np.zeros((4, 4, 4), dtype=np.uint8))

    def test_rejects_negative_sigma(self, input_uint8):
        with pytest.raises(ValueError):
            frangi_v016(input_uint8, sigmas=[-1, 2])


class TestInstalledHelpers:
    """frangi_v016 uses skimage.util.img_as_float and invert from the installed
    scikit-image. These two helpers must keep the behavior they had in 0.16.2
    (identical arrays in 0.16.2 and 0.26 were checked when this test was written)."""

    def test_img_as_float_of_uint8_is_x_times_one_over_255_float64(self):
        from skimage.util import img_as_float

        x = np.arange(256, dtype=np.uint8)
        out = img_as_float(x)
        assert out.dtype == np.float64
        np.testing.assert_array_equal(out, x * (1.0 / 255))

    def test_img_as_float_leaves_float64_unchanged(self):
        from skimage.util import img_as_float

        x = np.linspace(0.0, 1.0, 101)
        out = img_as_float(x)
        assert out.dtype == np.float64
        np.testing.assert_array_equal(out, x)

    def test_invert_of_uint8_is_255_minus_x(self):
        from skimage.util import invert

        x = np.arange(256, dtype=np.uint8)
        out = invert(x)
        assert out.dtype == np.uint8
        np.testing.assert_array_equal(out, 255 - x)

    def test_invert_of_float64_is_one_minus_x(self):
        from skimage.util import invert

        x = np.linspace(0.0, 1.0, 101)
        np.testing.assert_array_equal(invert(x), 1.0 - x)


class TestFilterCurvUsesFrozenFilter:
    def test_filter_curv_output_equals_frozen_filter(self, input_uint8, tmp_path):
        """filter_curv must return the frozen filter's output for the image it reads."""
        img_path = tmp_path / "ridge_input.png"
        Image.fromarray(input_uint8, mode="L").save(img_path)

        filter_img, im_name = filter_curv(img_path, tmp_path, save_img=False)

        assert im_name == "ridge_input"
        _assert_matches(filter_img, np.load(DATA / "ref_default.npy"))
