"""Memory guard for curvature analysis in the GUI.

A 20-megapixel curvature scan needs about 4.4 GB at its peak, which gets the
process killed on a login node (4 GiB cap) or a hosted app. Images that do not
fit the memory this process can use are shrunk, with the resolution and window
scaled alongside, and the output says so; images that fit are untouched.
"""

import io
import os

import numpy as np
import pytest
from PIL import Image

from fibermorph.utils import imaging

# ---------------------------------------------------------------------------
# Estimate and scale
# ---------------------------------------------------------------------------


def test_memory_estimate_matches_the_measurements():
    # Measured on Great Lakes: 4,440 MB at 5208 x 3904 and 1,258 MB at 2604 x 1952.
    assert imaging.curvature_peak_memory_mb(3904, 5208) == pytest.approx(4440, rel=0.03)
    assert imaging.curvature_peak_memory_mb(1952, 2604) == pytest.approx(1258, rel=0.03)


def test_image_that_fits_is_not_scaled():
    assert imaging.curvature_scale_for_budget(3904, 5208, 8000) == 1.0
    assert imaging.curvature_scale_for_budget(3904, 5208, None) == 1.0   # no limit known


def test_scale_makes_the_estimate_fit_the_budget():
    for budget in (3000, 2000, 1200, 800):
        s = imaging.curvature_scale_for_budget(3904, 5208, budget)
        assert 0 < s < 1
        assert imaging.curvature_peak_memory_mb(3904 * s, 5208 * s) == pytest.approx(budget, rel=0.01)


def test_hopeless_budget_gives_a_scale_below_the_minimum():
    assert imaging.curvature_scale_for_budget(3904, 5208, 150) < imaging.MIN_CURV_SCALE


def test_budget_leaves_headroom_for_the_rest_of_the_app(monkeypatch):
    # The variable is the total the app may use; the headroom comes off it.
    monkeypatch.setenv("FIBERMORPH_MAX_MEMORY_MB", "1234")
    assert imaging.memory_budget_mb() == pytest.approx(1234 - imaging.HEADROOM_MB)
    monkeypatch.setenv("FIBERMORPH_MAX_MEMORY_MB", "100")
    assert imaging.memory_budget_mb() == 0.0                 # never negative


def test_garbage_override_falls_back_to_detection(monkeypatch):
    monkeypatch.setenv("FIBERMORPH_MAX_MEMORY_MB", "not a number")
    monkeypatch.setattr(imaging, "available_memory_mb", lambda: 5000.0)
    assert imaging.memory_budget_mb() == pytest.approx(5000 - imaging.HEADROOM_MB)
    monkeypatch.setattr(imaging, "available_memory_mb", lambda: None)
    assert imaging.memory_budget_mb() is None


def test_an_image_that_fits_at_full_size_is_not_reduced_on_a_busy_machine(monkeypatch):
    """No percentage of free memory: 5.1 MP needs 1.26 GB, so 1.6 GB free is enough."""
    monkeypatch.delenv("FIBERMORPH_MAX_MEMORY_MB", raising=False)
    monkeypatch.setattr(imaging, "available_memory_mb", lambda: 1600.0)
    budget = imaging.memory_budget_mb()
    assert imaging.curvature_scale_for_budget(1952, 2604, budget) == 1.0


def test_available_memory_is_positive_or_unknown():
    avail = imaging.available_memory_mb()
    assert avail is None or avail >= 0


def test_scaled_window():
    assert imaging.scaled_window_px(50, 0.5) == 25
    assert imaging.scaled_window_px(50, 0.1) == 10           # never below the 10 px minimum
    assert imaging.scaled_window_px(5, 0.5) == 5             # < 10 px means the whole fragment


# ---------------------------------------------------------------------------
# cgroup parsing, against fake /sys/fs/cgroup trees
# ---------------------------------------------------------------------------

MB = 1048576


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text))


def test_cgroup_v2_limit_on_a_parent_slice_and_cache_is_not_counted(tmp_path):
    # Limit 4096 MB on the user slice, 1000 MB used of which 600 MB is inactive file cache.
    _write(tmp_path, "user.slice/user-1.slice/memory.max", 4096 * MB)
    _write(tmp_path, "user.slice/user-1.slice/memory.current", 1000 * MB)
    _write(tmp_path, "user.slice/user-1.slice/memory.stat", f"anon 1\ninactive_file {600 * MB}\n")
    _write(tmp_path, "user.slice/user-1.slice/session-3.scope/memory.current", 5 * MB)
    _write(tmp_path, "user.slice/user-1.slice/session-3.scope/memory.max", "max")
    got = imaging.cgroup_headroom_mb("0::/user.slice/user-1.slice/session-3.scope\n", str(tmp_path))
    assert got == pytest.approx([4096 - 400])


def test_cgroup_v1_uses_the_process_own_group_not_just_the_root(tmp_path):
    mem = "memory"
    _write(tmp_path, f"{mem}/memory.limit_in_bytes", 9223372036854771712)   # root: unlimited
    _write(tmp_path, f"{mem}/memory.usage_in_bytes", 50000 * MB)
    _write(tmp_path, f"{mem}/slurm/uid_1/job_9/memory.limit_in_bytes", 3000 * MB)
    _write(tmp_path, f"{mem}/slurm/uid_1/job_9/memory.usage_in_bytes", 500 * MB)
    _write(tmp_path, f"{mem}/slurm/uid_1/job_9/memory.stat", f"total_inactive_file {100 * MB}\n")
    text = "4:cpu,cpuacct:/slurm/uid_1/job_9\n3:memory:/slurm/uid_1/job_9\n"
    assert imaging.cgroup_headroom_mb(text, str(tmp_path)) == pytest.approx([3000 - 400])


def test_hybrid_host_still_finds_the_v1_memory_limit(tmp_path):
    # A 0:: line exists (v2 mounted at /unified) but memory.max does not.
    _write(tmp_path, "unified/user.slice/cgroup.procs", "")
    _write(tmp_path, "memory/user.slice/memory.limit_in_bytes", 2048 * MB)
    _write(tmp_path, "memory/user.slice/memory.usage_in_bytes", 48 * MB)
    text = "12:memory:/user.slice\n0::/user.slice\n"
    assert imaging.cgroup_headroom_mb(text, str(tmp_path)) == pytest.approx([2000])


def test_no_cgroup_files_means_no_limit(tmp_path):
    assert imaging.cgroup_headroom_mb("0::/a/b\n3:memory:/a\n", str(tmp_path)) == []
    assert imaging.cgroup_headroom_mb("", str(tmp_path)) == []


def test_write_scaled_copy_returns_the_exact_scale(tmp_path):
    src = tmp_path / "big.png"
    Image.fromarray(np.full((301, 403), 120, np.uint8)).save(src)
    eff, (w, h) = imaging.write_scaled_copy(str(src), str(tmp_path / "small.tif"), 0.5)
    assert (w, h) == (202, 150)
    assert eff == pytest.approx(202 / 403)
    assert Image.open(tmp_path / "small.tif").size == (202, 150)


# ---------------------------------------------------------------------------
# In the GUI
# ---------------------------------------------------------------------------

try:
    from streamlit.testing.v1 import AppTest

    import fibermorph.gui
    from pathlib import Path

    HAVE_STREAMLIT = True
except ImportError:                                    # the guard tests above need no GUI
    HAVE_STREAMLIT = False

if HAVE_STREAMLIT:
    APP_PATH = str(Path(fibermorph.gui.__file__).parent / "app.py")


def _fiber_png(size=1000):
    img = np.full((size, size), 230, dtype=np.uint8)
    xs = np.arange(40, size - 40)
    ys = (size // 2 + 60 * np.sin(2 * np.pi * 2 * xs / size)).astype(int)
    for x, y in zip(xs, ys):
        img[y - 3:y + 4, x] = 20
    buf = io.BytesIO()
    Image.fromarray(img, mode="L").save(buf, format="PNG")
    return buf.getvalue()


def _run_curvature(monkeypatch, budget_mb, auto_reduce=True):
    monkeypatch.delenv("FIBERMORPH_LOCAL", raising=False)
    if budget_mb is None:
        monkeypatch.delenv("FIBERMORPH_MAX_MEMORY_MB", raising=False)
    else:
        monkeypatch.setenv("FIBERMORPH_MAX_MEMORY_MB", str(budget_mb + imaging.HEADROOM_MB))
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.session_state["active_view"] = "curvature"
    at.run()
    if auto_reduce is not None:
        at.checkbox(key="curv_auto_reduce").set_value(auto_reduce)
    at.file_uploader[0].set_value(("fiber.png", _fiber_png(), "image/png"))
    at.run()
    [b for b in at.button if b.key == "curv_run"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


needs_upload_support = pytest.mark.skipif(
    not HAVE_STREAMLIT or not hasattr(AppTest, "file_uploader"),
    reason="streamlit or AppTest upload support is missing")


@needs_upload_support
def test_image_that_fits_is_analyzed_at_full_size_with_unchanged_columns(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=50000)
    summ = at.session_state["curvature_summary"]
    assert list(summ.columns) == ["source_file", "n_fragments", "curv_mean", "curv_median",
                                  "length_mean", "length_median", "length_total"]
    assert "analysis_scale" not in at.session_state["curvature_fragments"].columns
    assert not [w for w in at.warning if "Reduced to fit in memory" in w.value]


@needs_upload_support
def test_image_that_does_not_fit_is_reduced_and_says_so(monkeypatch):
    # 1 MP needs about 410 MB; a 320 MB budget forces a reduction to ~0.76.
    at = _run_curvature(monkeypatch, budget_mb=320)
    summ = at.session_state["curvature_summary"]
    frags = at.session_state["curvature_fragments"]
    assert 0.4 < summ["analysis_scale"].iloc[0] < 0.95
    assert list(frags["analysis_scale"].unique()) == list(summ["analysis_scale"])
    [msg] = [w.value for w in at.warning if "Reduced to fit in memory" in w.value]
    assert "fiber.png" in msg and "1000 × 1000" in msg and "analysis_scale" in msg


@needs_upload_support
def test_reduced_result_stays_close_to_full_size(monkeypatch):
    """Lengths are in mm either way, so a modest reduction changes them only a little."""
    full = _run_curvature(monkeypatch, budget_mb=50000).session_state["curvature_summary"]
    small = _run_curvature(monkeypatch, budget_mb=320).session_state["curvature_summary"]
    assert small["length_total"].iloc[0] == pytest.approx(full["length_total"].iloc[0], rel=0.15)


@needs_upload_support
def test_image_that_cannot_fit_even_at_a_quarter_is_refused_with_a_message(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=205)    # 1 MP at 205 MB would need a scale of 0.15
    assert any("too small to measure curvature" in w.value for w in at.warning)
    assert any(e.value == "No curvature fragments were measured." for e in at.error)


@needs_upload_support
def test_reduction_is_off_by_default_and_the_warning_points_to_the_checkbox(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=320, auto_reduce=None)
    assert at.checkbox(key="curv_auto_reduce").value is False
    [msg] = [w.value for w in at.warning if "will probably be killed" in w.value]
    assert "fiber.png" in msg and "Reduce very large images" in msg
    assert "analysis_scale" not in at.session_state["curvature_summary"].columns


@needs_upload_support
def test_reduction_can_be_turned_off(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=320, auto_reduce=False)
    assert any("will probably be killed" in w.value for w in at.warning)
    assert "analysis_scale" not in at.session_state["curvature_summary"].columns


@needs_upload_support
def test_reduced_warning_stays_after_a_rerun_and_says_which_way_values_move(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=320)
    at.run()                                            # e.g. clicking a download button
    [msg] = [w.value for w in at.warning if "Reduced to fit in memory" in w.value]
    assert "more* curved" in msg and "do not compare" in msg


@needs_upload_support
def test_refused_image_gets_the_memory_message_not_the_resolution_hint(monkeypatch):
    at = _run_curvature(monkeypatch, budget_mb=205)
    assert not any("Check the **Resolution**" in w.value for w in at.warning)
