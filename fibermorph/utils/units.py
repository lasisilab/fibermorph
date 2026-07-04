"""Resolution unit handling.

Internally fibermorph works in *pixels per unit*: pixels per µm for section
analysis, pixels per mm for curvature. Microscopes and scale bars, however,
often report the reciprocal (µm/pixel, mm/pixel). Entering one where the other
is expected silently corrupts every calibrated measurement — the same
µm/px-vs-px/µm mix-up that produced empty masks before.

These helpers convert any accepted entry to the pixels-per-unit value the
pipeline expects, so the GUI and CLI can offer both directions and never have
to bake the direction into a (mislabellable) field name again.
"""

# Unit tokens whose value is <unit> per pixel (reciprocal — must be inverted).
_PER_PIXEL_UNITS = {"um_per_px", "mm_per_px", "µm/px", "um/px", "mm/px"}
# Unit tokens whose value is already pixels per <unit> (pass through).
_PER_UNIT_UNITS = {"px_per_um", "px_per_mm", "px/µm", "px/um", "px/mm"}


def px_per_unit(value: float, per_pixel: bool) -> float:
    """Return pixels-per-unit for a resolution ``value``.

    Parameters
    ----------
    value : float
        The resolution number the user entered (must be > 0).
    per_pixel : bool
        True when ``value`` is <unit>/pixel (µm/px or mm/px) and must be
        inverted; False when it is already pixels/<unit> (px/µm or px/mm).
    """
    value = float(value)
    if value <= 0:
        raise ValueError("Resolution must be greater than 0.")
    return (1.0 / value) if per_pixel else value


def resolution_to_px_per_unit(value: float, units: str) -> float:
    """Convert ``value`` given a unit token to pixels-per-unit.

    ``units`` is one of ``px_per_um``, ``um_per_px``, ``px_per_mm``,
    ``mm_per_px`` (the GUI display labels ``px/µm``, ``µm/px``, ``px/mm``,
    ``mm/px`` are also accepted).
    """
    if units in _PER_PIXEL_UNITS:
        return px_per_unit(value, per_pixel=True)
    if units in _PER_UNIT_UNITS:
        return px_per_unit(value, per_pixel=False)
    raise ValueError(f"Unknown resolution units: {units!r}")


__all__ = ["px_per_unit", "resolution_to_px_per_unit"]
