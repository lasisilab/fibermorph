"""Tests for the fibermorph command line (fibermorph.cli).

Covers how ``--window_size`` is parsed and validated, and runs the real entry
point (``fibermorph.cli.main`` and ``python -m fibermorph``) on a small
synthetic curvature image.

Before ``--window_size`` was parsed as a number, its values reached the
curvature code as strings: ``--window_unit mm`` crashed with a TypeError
(string times float) and ``--window_size 50.0`` with ``--window_unit px``
crashed with a ValueError.
"""

import pathlib
import subprocess
import sys

import pandas as pd
import pytest
from PIL import Image

import fibermorph
from fibermorph import cli
from fibermorph.analysis.curvature_pipeline import curvature_seq
from fibermorph.cli import normalize_window_sizes, parse_args

SYNTHETIC_IMAGE = (
    pathlib.Path(__file__).parent / "test_data" / "curv_golden" / "synthetic_curv.png"
)
RESOLUTION = 132  # pixels per mm

# Arguments every parse needs besides the ones under test.
BASE = ["--curvature", "-i", "in_dir", "-o", "out_dir"]


def _window_size(*args):
    return parse_args(BASE + list(args)).window_size


def _parse_error(capsys, *args):
    """Parse ``args`` expecting argparse to reject them; return the error text."""
    with pytest.raises(SystemExit) as excinfo:
        parse_args(BASE + list(args))
    assert excinfo.value.code == 2
    return capsys.readouterr().err


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestWindowSizeParsing:
    def test_default_is_whole_hair(self):
        assert _window_size() is None

    def test_px_values_become_ints(self):
        value = _window_size("--window_size", "50")
        assert value == [50]
        assert type(value[0]) is int

    def test_px_accepts_a_float_spelling_of_a_whole_number(self):
        value = _window_size("--window_size", "50.0")
        assert value == [50]
        assert type(value[0]) is int

    def test_px_rejects_fractions(self, capsys):
        err = _parse_error(capsys, "--window_size", "50.5")
        assert "--window_size" in err
        assert "whole number" in err
        assert "Traceback" not in err

    def test_mm_values_stay_floats(self):
        value = _window_size("--window_size", "0.5", "--window_unit", "mm")
        assert value == [0.5]
        assert type(value[0]) is float

    def test_mm_whole_number_is_a_float(self):
        value = _window_size("--window_size", "1", "--window_unit", "mm")
        assert value == [1.0]
        assert type(value[0]) is float

    def test_unit_flag_may_come_before_the_sizes(self):
        assert _window_size("--window_unit", "mm", "--window_size", "0.25") == [0.25]

    def test_several_values_are_a_sweep(self):
        value = _window_size("--window_size", "25", "50", "100.0")
        assert value == [25, 50, 100]
        assert all(type(v) is int for v in value)

    def test_several_mm_values(self):
        assert _window_size("--window_size", "0.25", "0.5", "1", "--window_unit", "mm") == [
            0.25,
            0.5,
            1.0,
        ]

    @pytest.mark.parametrize("text", ["none", "None", "NONE"])
    def test_none_means_whole_hair(self, text):
        assert _window_size("--window_size", text) is None
        assert _window_size("--window_size", text, "--window_unit", "mm") is None

    @pytest.mark.parametrize("values", [["50", "none"], ["none", "50"], ["none", "none"]])
    def test_none_must_be_given_on_its_own(self, capsys, values):
        err = _parse_error(capsys, "--window_size", *values)
        assert "--window_size" in err and "on its own" in err

    @pytest.mark.parametrize("text", ["0", "0.0", "-5", "-50.0"])
    def test_px_rejects_zero_and_negative(self, capsys, text):
        err = _parse_error(capsys, "--window_size", text)
        assert "greater than 0" in err

    @pytest.mark.parametrize("text", ["0", "-0.5"])
    def test_mm_rejects_zero_and_negative(self, capsys, text):
        err = _parse_error(capsys, "--window_size", text, "--window_unit", "mm")
        assert "greater than 0" in err

    def test_one_bad_value_in_a_sweep_rejects_the_lot(self, capsys):
        err = _parse_error(capsys, "--window_size", "25", "0", "100")
        assert "greater than 0" in err

    @pytest.mark.parametrize("text", ["nan", "inf"])
    def test_rejects_non_finite_numbers(self, capsys, text):
        err = _parse_error(capsys, "--window_size", text, "--window_unit", "mm")
        assert "finite" in err

    def test_rejects_text_that_is_not_a_number(self, capsys):
        err = _parse_error(capsys, "--window_size", "wide")
        assert "invalid window size 'wide'" in err

    def test_option_without_a_value_is_rejected(self, capsys):
        err = _parse_error(capsys, "--window_size")
        assert "expected at least one argument" in err

    def test_remote_script_arguments_parse(self):
        # The "Run Remote" view of the GUI writes e.g. "--window_size 50"
        # (a whole number of pixels) among the other curvature flags.
        args = parse_args(
            ["--curvature", "-i", "/data/in", "-o", "/data/out"]
            + "--resolution_mm 132 --window_size 50 --jobs 4".split()
        )
        assert args.window_size == [50]
        assert args.window_unit == "px"


class TestNormalizeWindowSizes:
    def test_none_input(self):
        assert normalize_window_sizes(None, "px") is None
        assert normalize_window_sizes(None, "mm") is None

    def test_single_none_value(self):
        assert normalize_window_sizes([None], "px") is None

    def test_px_ints(self):
        assert normalize_window_sizes([50.0, 100.0], "px") == [50, 100]

    def test_mm_floats(self):
        assert normalize_window_sizes([0.5, 2.0], "mm") == [0.5, 2.0]

    @pytest.mark.parametrize(
        "values, unit",
        [([50.5], "px"), ([0.0], "px"), ([-1.0], "mm"), ([float("nan")], "mm"),
         ([float("inf")], "mm"), ([None, 50.0], "px"), ([None, None], "px")],
    )
    def test_invalid_values_raise_value_error(self, values, unit):
        with pytest.raises(ValueError):
            normalize_window_sizes(values, unit)


# ---------------------------------------------------------------------------
# What main() hands to the curvature workflow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra, expected",
    [
        ([], None),
        (["--window_size", "none"], None),
        (["--window_size", "50"], [50]),
        (["--window_size", "50.0"], [50]),
        (["--window_size", "25", "50"], [25, 50]),
        (["--window_size", "0.5", "--window_unit", "mm"], [0.5]),
    ],
)
def test_main_passes_parsed_window_sizes_to_the_workflow(monkeypatch, tmp_path, extra, expected):
    import fibermorph.workflows as workflows

    calls = []
    monkeypatch.setattr(workflows, "curvature", lambda *a, **k: calls.append(a) or True)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--curvature", "-i", str(tmp_path), "-o", str(tmp_path / "out")] + extra)
    assert excinfo.value.code == 0

    (call,) = calls
    window_size, window_unit = call[4], call[5]
    assert window_size == expected
    if expected is not None:
        assert [type(v) for v in window_size] == [type(v) for v in expected]
    assert window_unit == ("mm" if "mm" in extra else "px")


# ---------------------------------------------------------------------------
# End to end: the real entry point on a synthetic image
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def image_dir(tmp_path_factory):
    """A directory holding the synthetic curvature image as a TIFF."""
    directory = tmp_path_factory.mktemp("cli_images")
    Image.open(SYNTHETIC_IMAGE).save(directory / "synthetic_curv.tiff")
    return directory


def _run_cli(image_dir, out_dir, *extra):
    """Run ``fibermorph.cli.main`` for curvature; return (run directory, summary table)."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            ["--curvature", "-i", str(image_dir), "-o", str(out_dir),
             "--resolution_mm", str(RESOLUTION), "--jobs", "1", *extra]
        )
    assert excinfo.value.code == 0

    (run_dir,) = out_dir.glob("*_fibermorph_curvature")
    (summary,) = run_dir.glob("curvature_summary_data_*.csv")
    return run_dir, pd.read_csv(summary, index_col=0, float_precision="round_trip")


def _direct(image_dir, workdir, window_size, window_unit):
    """The summary ``curvature_seq`` gives for the same settings, called directly."""
    return curvature_seq(
        str(image_dir / "synthetic_curv.tiff"),
        str(workdir),
        resolution=RESOLUTION,
        window_size=window_size,
        window_unit=window_unit,
        save_img=False,
        test=False,
        within_element=False,
    )


def _assert_same_table(from_cli, direct):
    pd.testing.assert_frame_equal(
        from_cli.reset_index(drop=True),
        direct.reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


@pytest.mark.parametrize("size_text", ["50", "50.0"])
def test_cli_px_window(image_dir, tmp_path, size_text):
    run_dir, table = _run_cli(image_dir, tmp_path / "out", "--window_size", size_text)

    assert list(table["ID"]) == ["synthetic_curv_WindowSize-50px"]
    assert (run_dir / "analysis" / "ImageSum_synthetic_curv_WindowSize-50px.csv").is_file()
    _assert_same_table(table, _direct(image_dir, tmp_path / "direct", 50, "px"))


def test_cli_mm_window_matches_a_direct_call(image_dir, tmp_path):
    run_dir, table = _run_cli(
        image_dir, tmp_path / "out", "--window_size", "0.5", "--window_unit", "mm"
    )

    assert list(table["ID"]) == ["synthetic_curv_WindowSize-0.5mm"]
    assert (run_dir / "analysis" / "ImageSum_synthetic_curv_WindowSize-0.5mm.csv").is_file()
    assert table["hair_count"].iloc[0] > 0
    _assert_same_table(table, _direct(image_dir, tmp_path / "direct", 0.5, "mm"))


@pytest.mark.parametrize("extra", [[], ["--window_size", "none"]])
def test_cli_whole_hair_when_no_window_size(image_dir, tmp_path, extra):
    run_dir, table = _run_cli(image_dir, tmp_path / "out", *extra)

    assert list(table["ID"]) == ["synthetic_curv"]
    assert "curv_mean" in table.columns and "curv_mean_mean" not in table.columns
    assert (run_dir / "analysis" / "ImageSum_synthetic_curv.csv").is_file()
    _assert_same_table(table, _direct(image_dir, tmp_path / "direct", None, "px"))


def test_cli_window_size_sweep(image_dir, tmp_path):
    run_dir, table = _run_cli(
        image_dir, tmp_path / "out", "--window_size", "25", "50", "100"
    )

    assert list(table["ID"]) == [
        "synthetic_curv_WindowSize-25px",
        "synthetic_curv_WindowSize-50px",
        "synthetic_curv_WindowSize-100px",
    ]
    for window in (25, 50, 100):
        assert (run_dir / "analysis" / f"ImageSum_synthetic_curv_WindowSize-{window}px.csv").is_file()
    _assert_same_table(table, _direct(image_dir, tmp_path / "direct", [25, 50, 100], "px"))


def test_cli_window_under_ten_pixels_measures_each_hair_whole(image_dir, tmp_path):
    # A window that comes to fewer than 10 pixels is not used: every hair is
    # measured over its whole length, whatever the unit. The output still
    # carries the window that was asked for.
    _, mm_table = _run_cli(
        image_dir, tmp_path / "mm", "--window_size", "0.001", "--window_unit", "mm"
    )
    _, px_table = _run_cli(image_dir, tmp_path / "px", "--window_size", "5")

    assert list(mm_table["ID"]) == ["synthetic_curv_WindowSize-0.001mm"]
    assert list(px_table["ID"]) == ["synthetic_curv_WindowSize-5px"]
    _assert_same_table(mm_table.drop(columns="ID"), px_table.drop(columns="ID"))


# ---------------------------------------------------------------------------
# End to end as a subprocess: python -m fibermorph
# ---------------------------------------------------------------------------

# Run from the folder that holds the package under test, so the subprocess
# imports the same fibermorph as this test run.
PACKAGE_PARENT = pathlib.Path(fibermorph.__file__).resolve().parent.parent


def _module_run(*args):
    return subprocess.run(
        [sys.executable, "-m", "fibermorph", *args],
        cwd=PACKAGE_PARENT,
        capture_output=True,
        text=True,
    )


def test_module_run_with_a_mm_window(image_dir, tmp_path):
    out_dir = tmp_path / "out"
    result = _module_run(
        "--curvature", "-i", str(image_dir), "-o", str(out_dir),
        "--resolution_mm", str(RESOLUTION), "--window_size", "0.5", "--window_unit", "mm",
    )

    assert result.returncode == 0, result.stderr
    (summary,) = out_dir.glob("*_fibermorph_curvature/curvature_summary_data_*.csv")
    assert list(pd.read_csv(summary)["ID"]) == ["synthetic_curv_WindowSize-0.5mm"]


@pytest.mark.parametrize(
    "bad_args, message",
    [
        (["--window_size", "50.5"], "whole number"),
        (["--window_size", "-1"], "greater than 0"),
        (["--window_size", "wide"], "invalid window size"),
    ],
)
def test_module_run_reports_bad_window_size_without_a_traceback(
    image_dir, tmp_path, bad_args, message
):
    out_dir = tmp_path / "out"
    result = _module_run(
        "--curvature", "-i", str(image_dir), "-o", str(out_dir), *bad_args
    )

    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "--window_size" in result.stderr and message in result.stderr
    assert not out_dir.exists()
