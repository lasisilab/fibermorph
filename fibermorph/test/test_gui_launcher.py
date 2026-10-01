"""Tests for the GUI launcher: first-run email-prompt skip, and hosted vs local
mode (`fibermorph-gui` vs `fibermorph-gui --local`)."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from fibermorph.gui import launcher


def test_skip_email_prompt_creates_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))          # Path.home() honors HOME on POSIX
    launcher._skip_streamlit_email_prompt()
    cred = tmp_path / ".streamlit" / "credentials.toml"
    assert cred.exists()
    assert 'email = ""' in cred.read_text()


def test_skip_email_prompt_preserves_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cred = tmp_path / ".streamlit" / "credentials.toml"
    cred.parent.mkdir(parents=True)
    cred.write_text('[general]\nemail = "real@example.com"\n')
    launcher._skip_streamlit_email_prompt()
    assert "real@example.com" in cred.read_text(), "existing credentials must not be clobbered"


# ---------------------------------------------------------------------------
# Hosted vs local mode: `fibermorph-gui` is hosted unless --local (or
# FIBERMORPH_LOCAL=1) is given.
# ---------------------------------------------------------------------------

@pytest.fixture
def run_launcher(tmp_path, monkeypatch):
    """Run launcher.main(argv) with streamlit's CLI replaced by a recorder.

    Returns a function that runs the launcher and returns a dict with the
    sys.argv streamlit would have received and the FIBERMORPH_LOCAL value seen
    at that moment. HOME and FIBERMORPH_LOCAL are sandboxed so nothing leaks
    into (or out of) the real environment.
    """
    pytest.importorskip("streamlit")
    from streamlit.web import cli as stcli

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("FIBERMORPH_LOCAL", raising=False)
    monkeypatch.delenv(launcher.UPLOAD_CAP_ENV, raising=False)
    monkeypatch.setattr(sys, "argv", list(sys.argv))  # main() replaces sys.argv; undone on teardown
    seen = {}

    def fake_streamlit_main():
        seen["argv"] = list(sys.argv)
        seen["local_env"] = os.environ.get("FIBERMORPH_LOCAL")
        return 0

    monkeypatch.setattr(stcli, "main", fake_streamlit_main)

    def run(argv):
        with pytest.raises(SystemExit) as exc:
            launcher.main(argv)
        assert exc.value.code == 0
        return seen

    yield run
    # main() sets FIBERMORPH_LOCAL directly in os.environ in local mode, which
    # monkeypatch doesn't know about; remove it before monkeypatch restores
    # whatever the environment had originally.
    os.environ.pop("FIBERMORPH_LOCAL", None)


def _option(argv, name):
    """Last value given for a --name option in a streamlit argv."""
    return [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == name][-1]


def test_default_launch_is_hosted(run_launcher):
    seen = run_launcher([])
    argv = seen["argv"]
    assert argv[:2] == ["streamlit", "run"]
    assert Path(argv[2]) == Path(launcher.__file__).parent / "app.py"
    assert _option(argv, "--server.maxUploadSize") == "500"
    assert "--server.address" not in argv
    assert seen["local_env"] is None


def test_hosted_mode_never_sets_local_env(run_launcher):
    run_launcher([])
    assert "FIBERMORPH_LOCAL" not in os.environ


def test_local_flag_enables_local_mode(run_launcher):
    seen = run_launcher(["--local"])
    argv = seen["argv"]
    assert seen["local_env"] == "1"
    assert _option(argv, "--server.maxUploadSize") == "5000"
    assert _option(argv, "--server.address") == "localhost"
    assert "--local" not in argv, "--local is fibermorph's flag, not streamlit's"


def test_preset_env_var_enables_local_mode(run_launcher, monkeypatch):
    monkeypatch.setenv("FIBERMORPH_LOCAL", "1")
    seen = run_launcher([])
    argv = seen["argv"]
    assert seen["local_env"] == "1"
    assert _option(argv, "--server.maxUploadSize") == "5000"
    assert _option(argv, "--server.address") == "localhost"


@pytest.mark.parametrize("value", ["0", "", "true"])
def test_other_env_values_stay_hosted(run_launcher, monkeypatch, value):
    # The app only treats FIBERMORPH_LOCAL == "1" as local mode.
    monkeypatch.setenv("FIBERMORPH_LOCAL", value)
    seen = run_launcher([])
    assert _option(seen["argv"], "--server.maxUploadSize") == "500"
    assert "--server.address" not in seen["argv"]
    assert seen["local_env"] == value  # left untouched


def test_extra_args_pass_through_after_defaults(run_launcher):
    seen = run_launcher(["--local", "--server.port", "8600", "--server.headless=true"])
    argv = seen["argv"]
    assert argv[-3:] == ["--server.port", "8600", "--server.headless=true"]
    # Pass-through comes after the defaults so it can override them.
    assert argv.index("--server.port") > argv.index("--server.maxUploadSize")
    assert argv.index("--server.port") > argv.index("--server.address")


def test_extra_args_can_override_defaults(run_launcher):
    seen = run_launcher(["--server.maxUploadSize", "1000"])
    assert _option(seen["argv"], "--server.maxUploadSize") == "1000"
    seen = run_launcher(["--local", "--server.address", "192.168.0.5"])
    assert _option(seen["argv"], "--server.address") == "192.168.0.5"


def test_extra_args_pass_through_in_hosted_mode(run_launcher):
    seen = run_launcher(["--server.port", "9000"])
    assert seen["argv"][-2:] == ["--server.port", "9000"]
    assert seen["local_env"] is None


def test_local_flag_position_does_not_matter(run_launcher):
    seen = run_launcher(["--server.port", "9000", "--local"])
    assert seen["local_env"] == "1"
    assert seen["argv"][-2:] == ["--server.port", "9000"]
    assert "--local" not in seen["argv"]


def test_main_reads_sys_argv_by_default(run_launcher, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fibermorph-gui", "--local"])
    seen = run_launcher(None)
    assert seen["local_env"] == "1"


def test_help_documents_local_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        launcher.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--local" in out
    assert "5 GB" in out and "localhost" in out
    assert "500 MB" in out


def test_launch_notice_names_the_mode(run_launcher, capsys):
    run_launcher([])
    assert "hosted mode" in capsys.readouterr().err
    run_launcher(["--local"])
    assert "local mode" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Precedence: the launcher's --server.* defaults vs STREAMLIT_* environment
# variables and the user's own command-line options.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [[], ["--local"]])
def test_env_upload_cap_is_not_overridden(run_launcher, monkeypatch, argv):
    # A command-line option outranks STREAMLIT_SERVER_MAX_UPLOAD_SIZE, so the
    # launcher must not pass one when the host has set the variable.
    monkeypatch.setenv(launcher.UPLOAD_CAP_ENV, "200")
    seen = run_launcher(argv)
    assert "--server.maxUploadSize" not in seen["argv"]


def test_empty_env_upload_cap_counts_as_unset(run_launcher, monkeypatch):
    monkeypatch.setenv(launcher.UPLOAD_CAP_ENV, "")
    seen = run_launcher([])
    assert _option(seen["argv"], "--server.maxUploadSize") == "500"


def test_command_line_upload_cap_wins_over_env(run_launcher, monkeypatch):
    monkeypatch.setenv(launcher.UPLOAD_CAP_ENV, "200")
    seen = run_launcher(["--server.maxUploadSize", "300"])
    assert _option(seen["argv"], "--server.maxUploadSize") == "300"


def test_env_address_does_not_widen_local_mode(run_launcher, monkeypatch):
    monkeypatch.setenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    seen = run_launcher(["--local"])
    assert _option(seen["argv"], "--server.address") == "localhost"


def test_hosted_mode_leaves_address_and_port_to_streamlit(run_launcher, monkeypatch):
    # The Dockerfile sets STREAMLIT_SERVER_ADDRESS=0.0.0.0 and
    # STREAMLIT_SERVER_PORT=7860; hosted mode passes neither option, so both
    # keep applying.
    monkeypatch.setenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    monkeypatch.setenv("STREAMLIT_SERVER_PORT", "7860")
    seen = run_launcher([])
    assert "--server.address" not in seen["argv"]
    assert "--server.port" not in seen["argv"]


@pytest.mark.parametrize("args, expected", [
    (["--server.port", "8600"], "8600"),
    (["--server.port=8600"], "8600"),
    (["--server.port", "1", "--server.port=2"], "2"),
    (["--server.port"], None),
    (["--server.portal", "9"], None),
    ([], None),
])
def test_option_value(args, expected):
    assert launcher._option_value(args, "--server.port") == expected


def test_help_says_how_the_defaults_interact_with_streamlit_settings(capsys):
    with pytest.raises(SystemExit):
        launcher.main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE" in out
    assert "STREAMLIT_SERVER_ADDRESS" in out
    assert "config.toml" in out


# --- startup notice ---------------------------------------------------------

def test_local_notice_says_localhost_only_by_default(run_launcher, capsys):
    run_launcher(["--local"])
    err = capsys.readouterr().err
    assert "localhost only" in err
    assert "5000 MB" in err


@pytest.mark.parametrize("flag", [
    ["--server.address", "0.0.0.0"],
    ["--server.address=0.0.0.0"],
    ["--server.address", "192.168.0.5"],
    # Streamlit treats an empty address as 0.0.0.0 (every interface).
    ["--server.address="],
    ["--server.address", ""],
])
def test_local_notice_warns_when_address_is_widened(run_launcher, capsys, flag):
    run_launcher(["--local", *flag])
    err = capsys.readouterr().err
    assert "localhost only" not in err
    assert "WARNING" in err
    assert "read folders on it" in err


@pytest.mark.parametrize("flag", [["--server.address="], ["--server.address", ""]])
def test_local_notice_says_every_interface_for_an_empty_address(run_launcher, capsys, flag):
    run_launcher(["--local", *flag])
    assert "all network interfaces" in capsys.readouterr().err


@pytest.mark.parametrize("address", ["localhost", "127.0.0.1", "::1"])
def test_local_notice_is_unchanged_for_loopback_address(run_launcher, capsys, address):
    run_launcher(["--local", "--server.address", address])
    err = capsys.readouterr().err
    assert "localhost only" in err
    assert "WARNING" not in err


def test_notice_reports_the_effective_upload_cap(run_launcher, monkeypatch, capsys):
    run_launcher([])
    assert "500 MB" in capsys.readouterr().err
    monkeypatch.setenv(launcher.UPLOAD_CAP_ENV, "200")
    run_launcher([])
    assert "200 MB" in capsys.readouterr().err
    run_launcher(["--server.maxUploadSize=300"])
    assert "300 MB" in capsys.readouterr().err


# --- what Streamlit itself resolves -----------------------------------------

_RESOLVE_SCRIPT = textwrap.dedent("""
    import json, sys
    from streamlit import config
    from streamlit.web import bootstrap, cli as stcli
    from fibermorph.gui import launcher

    seen = {}

    def fake_main_run(file, args=None, flag_options=None):
        # What `streamlit run` does with its options before starting the server.
        bootstrap.load_config_options(flag_options=flag_options or {})
        for name in ("server.maxUploadSize", "server.address"):
            seen[name] = config.get_option(name)

    stcli._main_run = fake_main_run
    try:
        launcher.main(sys.argv[1:])
    except SystemExit:
        pass
    print("RESOLVED " + json.dumps(seen))
""")


def _resolved_options(tmp_path, env, args):
    """Run the launcher in a fresh interpreter with Streamlit's real config
    loader and return the server options Streamlit ends up with.

    Runs in an empty directory with an empty HOME, so neither the repository's
    .streamlit/config.toml nor the developer's own settings are read.
    """
    pytest.importorskip("streamlit")
    from streamlit.web import bootstrap, cli as stcli
    if not (hasattr(stcli, "_main_run") and hasattr(bootstrap, "load_config_options")):
        pytest.skip("this Streamlit version does not expose the config loader used here")
    full_env = {k: v for k, v in os.environ.items()
                if not k.startswith(("STREAMLIT_", "FIBERMORPH_"))}
    full_env.update(env, HOME=str(tmp_path))
    full_env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(launcher.__file__).resolve().parents[2]), full_env.get("PYTHONPATH", "")]
    )
    proc = subprocess.run(
        [sys.executable, "-c", _RESOLVE_SCRIPT, *args],
        cwd=tmp_path, env=full_env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESOLVED ")][-1]
    return json.loads(line[len("RESOLVED "):])


def test_streamlit_uses_host_upload_cap_from_environment(tmp_path):
    got = _resolved_options(tmp_path, {launcher.UPLOAD_CAP_ENV: "200"}, [])
    assert got["server.maxUploadSize"] == 200


def test_streamlit_gets_500_mb_cap_when_host_sets_nothing(tmp_path):
    # Streamlit's own default is 200 MB, so 500 shows the launcher set it.
    got = _resolved_options(tmp_path, {}, [])
    assert got["server.maxUploadSize"] == 500


def test_streamlit_keeps_host_address_in_hosted_mode(tmp_path):
    got = _resolved_options(tmp_path, {"STREAMLIT_SERVER_ADDRESS": "0.0.0.0"}, [])
    assert got["server.address"] == "0.0.0.0"


def test_streamlit_ignores_env_address_in_local_mode(tmp_path):
    got = _resolved_options(tmp_path, {"STREAMLIT_SERVER_ADDRESS": "0.0.0.0"}, ["--local"])
    assert got["server.address"] == "localhost"


def test_streamlit_honours_command_line_address_in_local_mode(tmp_path):
    got = _resolved_options(
        tmp_path, {"STREAMLIT_SERVER_ADDRESS": "localhost"},
        ["--local", "--server.address", "0.0.0.0"],
    )
    assert got["server.address"] == "0.0.0.0"


def test_streamlit_gets_an_empty_address_when_asked_for_one(tmp_path):
    # Streamlit's server then falls back to 0.0.0.0 (every interface), which is
    # why the startup notice warns about it instead of saying "localhost only".
    got = _resolved_options(tmp_path, {}, ["--local", "--server.address="])
    assert got["server.address"] == ""
