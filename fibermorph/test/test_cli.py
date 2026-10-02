"""Tests for the fibermorph command line (fibermorph.cli).

Covers how ``--window_size`` is parsed and validated (including the longest
window accepted), how out-of-range values of ``--jobs``, the resolutions and
the section size limits are refused, and runs the real entry point (``fibermorph.cli.main`` and ``python -m
fibermorph``) on a small synthetic curvature image.

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
from fibermorph.cli import MAX_WINDOW_PX, normalize_window_sizes, parse_args

SYNTHETIC_IMAGE = (
    pathlib.Path(__file__).parent / "test_data" / "curv_golden" / "synthetic_curv.png"
)
RESOLUTION = 132  # pixels per mm

# Arguments every parse needs besides the ones under test.
BASE = ["--curvature", "-i", "in_dir", "-o", "out_dir"]


def _window_size(*args):
    return parse_args(BASE + list(args)).window_size


def _parse_error(capsys, *args, base=BASE):
    """Parse ``args`` expecting argparse to reject them; return the error text."""
    with pytest.raises(SystemExit) as excinfo:
        parse_args(list(base) + list(args))
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


class TestNumericOptions:
    """--jobs, the resolutions and the section size limits."""

    def test_defaults_are_accepted(self):
        args = parse_args(BASE)
        assert (args.jobs, args.resolution_mm, args.resolution_mu) == (1, 132.0, 4.25)
        assert (args.minsize, args.maxsize) == (20, 150)

    @pytest.mark.parametrize("jobs", ["1", "4", "-1", "-2"])
    def test_jobs_accepts_positive_numbers_and_joblibs_negative_ones(self, jobs, monkeypatch):
        monkeypatch.setattr(cli.os, "cpu_count", lambda: 8)
        assert parse_args(BASE + ["--jobs", jobs]).jobs == int(jobs)

    @pytest.mark.parametrize("jobs", ["9", "100000", "2147483648", "99999999999999999999"])
    def test_jobs_above_cpu_count_is_reduced_to_cpu_count(self, jobs, monkeypatch, capsys):
        monkeypatch.setattr(cli.os, "cpu_count", lambda: 8)
        assert parse_args(BASE + ["--jobs", jobs]).jobs == 8
        assert f"--jobs {jobs} is more than the 8 CPUs" in capsys.readouterr().err

    def test_jobs_cap_handles_unknown_cpu_count(self, monkeypatch, capsys):
        monkeypatch.setattr(cli.os, "cpu_count", lambda: None)
        assert parse_args(BASE + ["--jobs", "4"]).jobs == 1

    def test_jobs_rejects_zero(self, capsys):
        err = _parse_error(capsys, "--jobs", "0")
        assert "--jobs" in err and "must not be 0" in err
        assert "Traceback" not in err

    @pytest.mark.parametrize("option", ["--resolution_mm", "--resolution_mu"])
    @pytest.mark.parametrize("text", ["0", "0.0", "-5", "-0.25", "nan", "inf"])
    def test_resolution_rejects_zero_negative_and_non_finite(self, capsys, option, text):
        err = _parse_error(capsys, option, text)
        assert option in err and "finite number greater than 0" in err
        assert "Traceback" not in err

    @pytest.mark.parametrize(
        "option, units_option, units",
        [
            ("--resolution_mm", "--resolution_mm_units", "mm_per_px"),
            ("--resolution_mu", "--resolution_mu_units", "um_per_px"),
        ],
    )
    def test_resolution_in_reciprocal_units(self, capsys, option, units_option, units):
        args = parse_args(BASE + [option, "0.0076", units_option, units])
        assert getattr(args, option[2:]) == 0.0076
        # a value so small that 1 / value overflows cannot become pixels per unit
        err = _parse_error(capsys, option, "1e-320", units_option, units)
        assert option in err and "too small" in err

    @pytest.mark.parametrize("module", ["--section", "--raw2gray"])
    @pytest.mark.parametrize(
        "bad",
        [["--resolution_mm", "0"], ["--resolution_mu", "nan"], ["--jobs", "0"]],
    )
    def test_checked_whichever_module_is_chosen(self, capsys, module, bad):
        err = _parse_error(capsys, *bad, base=[module, "-i", "in_dir", "-o", "out_dir"])
        assert bad[0] in err

    @pytest.mark.parametrize(
        "extra",
        [
            ["--minsize", "0"],
            ["--minsize", "50", "--maxsize", "50"],
            ["--minsize", "0", "--maxsize", "1"],
        ],
    )
    def test_section_size_limits_accepted(self, extra):
        args = parse_args(["--section", "-i", "in_dir", "-o", "out_dir"] + extra)
        assert args.minsize <= args.maxsize

    @pytest.mark.parametrize(
        "extra, message",
        [
            (["--minsize", "-1"], "--minsize: must not be negative"),
            (["--maxsize", "0"], "--maxsize: must be greater than 0"),
            (["--maxsize", "-5"], "--maxsize: must be greater than 0"),
            (["--minsize", "200", "--maxsize", "100"], "--minsize: 200 is larger than --maxsize"),
        ],
    )
    def test_section_size_limits_rejected(self, capsys, extra, message):
        err = _parse_error(capsys, *extra, base=["--section", "-i", "in_dir", "-o", "out_dir"])
        assert message in err
        assert "Traceback" not in err


class TestWindowSizeLimit:
    """A window longer than MAX_WINDOW_PX pixels is refused, in px or after mm conversion.

    Before the limit, ``--window_size 1e307`` with mm (or a huge resolution)
    ended in ``OverflowError: cannot convert float infinity to integer``, and
    ``--window_size 1e300`` with px in ``OSError: File name too long``.
    """

    def test_the_limit(self):
        assert MAX_WINDOW_PX == 1_000_000_000

    def test_largest_px_window_is_accepted(self):
        assert _window_size("--window_size", "1000000000") == [10**9]

    def test_px_window_just_over_the_limit_is_rejected(self, capsys):
        err = _parse_error(capsys, "--window_size", "1000000001")
        assert "argument --window_size:" in err
        assert "largest window allowed (1,000,000,000 pixels)" in err

    @pytest.mark.parametrize("text", ["1e10", "1e20", "1e200", "1e300", "1.7976931348623157e308"])
    def test_huge_px_windows_are_rejected(self, capsys, text):
        err = _parse_error(capsys, "--window_size", text)
        assert "argument --window_size:" in err and "largest window allowed" in err
        assert "Traceback" not in err

    def test_largest_mm_window_is_accepted(self):
        value = _window_size(
            "--window_size", "1000000000", "--window_unit", "mm", "--resolution_mm", "1"
        )
        assert value == [1e9]

    def test_mm_window_just_over_the_limit_is_rejected(self, capsys):
        err = _parse_error(
            capsys, "--window_size", "1000000001", "--window_unit", "mm", "--resolution_mm", "1"
        )
        assert "argument --window_size:" in err and "largest window allowed" in err

    @pytest.mark.parametrize(
        "extra",
        [
            # 1e307 mm * 132 px/mm is infinite
            ["--window_size", "1e307", "--window_unit", "mm"],
            # a finite resolution that still overflows the product
            ["--window_size", "10", "--window_unit", "mm", "--resolution_mm", "1e308"],
            # finite but over the limit: 1e8 mm * 132 px/mm = 1.32e10 px
            ["--window_size", "1e8", "--window_unit", "mm"],
        ],
    )
    def test_huge_mm_windows_are_rejected(self, capsys, extra):
        err = _parse_error(capsys, *extra)
        assert "argument --window_size:" in err and "largest window allowed" in err
        assert "Traceback" not in err

    def test_mm_message_gives_the_length_in_pixels_and_the_resolution(self, capsys):
        err = _parse_error(
            capsys, "--window_size", "1e8", "--window_unit", "mm", "--resolution_mm", "132"
        )
        assert "100000000 mm is 13,200,000,000 pixels at --resolution_mm 132 px_per_mm" in err

    def test_px_message_shows_the_exact_window_just_over_the_limit(self, capsys):
        err = _parse_error(capsys, "--window_size", str(MAX_WINDOW_PX + 1))
        assert f"{MAX_WINDOW_PX + 1:,} px is longer than the largest window allowed" in err

    def test_mm_window_is_converted_with_a_mm_per_px_resolution(self, capsys):
        # 0.0076 mm per pixel is 131.58 pixels per mm: 100 mm is about 13 158 px
        args = parse_args(
            BASE
            + "--window_size 100 --window_unit mm --resolution_mm 0.0076".split()
            + ["--resolution_mm_units", "mm_per_px"]
        )
        assert args.window_size == [100.0]
        # 1e8 mm at 0.001 mm per pixel is 1e11 px
        err = _parse_error(
            capsys, "--window_size", "1e8", "--window_unit", "mm", "--resolution_mm", "0.001",
            "--resolution_mm_units", "mm_per_px",
        )
        assert "mm_per_px" in err and "largest window allowed" in err

    def test_one_long_window_in_a_sweep_rejects_the_lot(self, capsys):
        err = _parse_error(capsys, "--window_size", "25", "1e300")
        assert "largest window allowed" in err

    def test_checked_whichever_module_is_chosen(self, capsys):
        err = _parse_error(
            capsys, "--window_size", "1e300", base=["--section", "-i", "in_dir", "-o", "out_dir"]
        )
        assert "largest window allowed" in err

    def test_a_bad_resolution_is_reported_first(self, capsys):
        err = _parse_error(
            capsys, "--window_size", "1e307", "--window_unit", "mm", "--resolution_mm", "0"
        )
        assert "argument --resolution_mm:" in err

    def test_no_window_size_is_not_affected_by_a_huge_resolution(self):
        args = parse_args(["--section", "-i", "in_dir", "-o", "out_dir", "--resolution_mm", "1e308"])
        assert args.window_size is None


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
        # both used to end in a traceback after the output directory was made
        (["--window_unit", "mm", "--window_size", "1e307"], "largest window allowed"),
        (["--window_size", "1e300"], "largest window allowed"),
        (
            ["--window_unit", "mm", "--window_size", "10", "--resolution_mm", "1e308"],
            "largest window allowed",
        ),
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


def test_module_run_accepts_the_largest_window(image_dir, tmp_path):
    # no hair is that long, so nothing is measured; the run itself still works
    out_dir = tmp_path / "out"
    result = _module_run(
        "--curvature", "-i", str(image_dir), "-o", str(out_dir),
        "--resolution_mm", str(RESOLUTION), "--window_size", str(MAX_WINDOW_PX),
    )

    assert result.returncode == 0, result.stderr
    (summary,) = out_dir.glob("*_fibermorph_curvature/curvature_summary_data_*.csv")
    table = pd.read_csv(summary)
    assert list(table["ID"]) == [f"synthetic_curv_WindowSize-{MAX_WINDOW_PX}px"]
    assert list(table["hair_count"]) == [0]


@pytest.mark.parametrize(
    "module, bad_args, option",
    [
        ("--curvature", ["--jobs", "0"], "--jobs"),
        ("--curvature", ["--resolution_mm", "0"], "--resolution_mm"),
        ("--curvature", ["--resolution_mm", "-5"], "--resolution_mm"),
        ("--curvature", ["--resolution_mm", "nan"], "--resolution_mm"),
        ("--curvature", ["--resolution_mm", "inf"], "--resolution_mm"),
        ("--section", ["--resolution_mu", "0"], "--resolution_mu"),
        ("--section", ["--resolution_mu", "nan"], "--resolution_mu"),
        ("--section", ["--jobs", "0"], "--jobs"),
        ("--section", ["--minsize", "200", "--maxsize", "100"], "--minsize"),
        # an option the chosen module does not use is checked all the same
        ("--section", ["--resolution_mm", "0"], "--resolution_mm"),
        ("--raw2gray", ["--resolution_mm", "0"], "--resolution_mm"),
    ],
)
def test_module_run_reports_bad_numeric_options_without_a_traceback(
    image_dir, tmp_path, module, bad_args, option
):
    out_dir = tmp_path / "out"
    result = _module_run(module, "-i", str(image_dir), "-o", str(out_dir), *bad_args)

    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert f"argument {option}:" in result.stderr
    assert not out_dir.exists()


def test_module_run_accepts_jobs_minus_one(image_dir, tmp_path):
    out_dir = tmp_path / "out"
    result = _module_run(
        "--curvature", "-i", str(image_dir), "-o", str(out_dir),
        "--resolution_mm", str(RESOLUTION), "--window_size", "50", "--jobs", "-1",
    )

    assert result.returncode == 0, result.stderr
    (summary,) = out_dir.glob("*_fibermorph_curvature/curvature_summary_data_*.csv")
    assert list(pd.read_csv(summary)["ID"]) == ["synthetic_curv_WindowSize-50px"]


def test_module_run_with_huge_jobs_runs_on_available_cpus(image_dir, tmp_path):
    out_dir = tmp_path / "out"
    result = _module_run(
        "--curvature", "-i", str(image_dir), "-o", str(out_dir),
        "--resolution_mm", str(RESOLUTION), "--window_size", "50",
        "--jobs", "2147483648",
    )

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert "--jobs 2147483648 is more than the" in result.stderr
    (summary,) = out_dir.glob("*_fibermorph_curvature/curvature_summary_data_*.csv")
    assert list(pd.read_csv(summary)["ID"]) == ["synthetic_curv_WindowSize-50px"]
