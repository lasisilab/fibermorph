"""Unit tests for resolution unit conversion (utils.units)."""

import math

import pytest

from fibermorph.utils.units import px_per_unit, resolution_to_px_per_unit


class TestPxPerUnit:
    def test_pass_through_when_already_px_per_unit(self):
        assert px_per_unit(5.556, per_pixel=False) == 5.556

    def test_inverts_when_per_pixel(self):
        # 0.18 µm/pixel -> 1/0.18 ≈ 5.556 px/µm
        assert math.isclose(px_per_unit(0.18, per_pixel=True), 1 / 0.18)

    def test_round_trip(self):
        px = px_per_unit(4.25, per_pixel=False)
        assert math.isclose(px_per_unit(1 / px, per_pixel=True), px)

    @pytest.mark.parametrize("bad", [0, -1, -0.5])
    def test_rejects_non_positive(self, bad):
        with pytest.raises(ValueError):
            px_per_unit(bad, per_pixel=False)


class TestResolutionToPxPerUnit:
    def test_section_tokens(self):
        assert resolution_to_px_per_unit(5.556, "px_per_um") == 5.556
        assert math.isclose(resolution_to_px_per_unit(0.18, "um_per_px"), 1 / 0.18)

    def test_curvature_tokens(self):
        assert resolution_to_px_per_unit(132.0, "px_per_mm") == 132.0
        assert math.isclose(resolution_to_px_per_unit(1 / 132.0, "mm_per_px"), 132.0)

    def test_gui_display_labels(self):
        assert resolution_to_px_per_unit(5.556, "px/µm") == 5.556
        assert math.isclose(resolution_to_px_per_unit(0.18, "µm/px"), 1 / 0.18)
        assert resolution_to_px_per_unit(132.0, "px/mm") == 132.0
        assert math.isclose(resolution_to_px_per_unit(0.01, "mm/px"), 100.0)

    def test_unknown_units_raise(self):
        with pytest.raises(ValueError):
            resolution_to_px_per_unit(1.0, "furlongs")
