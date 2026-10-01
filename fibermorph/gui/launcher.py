"""Launcher script for fibermorph GUI via Streamlit.

``fibermorph-gui`` starts the app in *hosted* mode: uploads only, a 500 MB
upload cap, and Streamlit's normal network binding. ``fibermorph-gui --local``
starts it in *local* mode for use on your own machine: a "Folder on disk"
input that reads images straight from this computer, a 5 GB upload cap, and
the server bound to localhost only.

Local mode lets every visitor read folders on the machine running the app, so
it must be asked for explicitly and should never be used on a shared server.

Precedence of the launcher's server options (Streamlit ranks them, highest
first: command-line option, ``STREAMLIT_*`` environment variable,
``.streamlit/config.toml``, built-in default):

* ``--server.maxUploadSize`` is passed on the command line unless the
  ``STREAMLIT_SERVER_MAX_UPLOAD_SIZE`` environment variable is set, in which
  case the environment variable is used. It does override ``config.toml``.
* In local mode ``--server.address localhost`` is always passed, so
  ``STREAMLIT_SERVER_ADDRESS`` and ``config.toml`` do not widen who can reach
  folder input. Pass ``--server.address`` yourself to change it.
* Anything given on the ``fibermorph-gui`` command line overrides all of the
  above. An empty ``--server.address=`` is not "unset": Streamlit then listens
  on every interface, so the startup notice warns about it like any other
  address that is not localhost.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Upload caps (MB), passed to Streamlit as --server.maxUploadSize. The hosted
# value matches .streamlit/config.toml, but is passed explicitly so it applies
# regardless of the directory the command is run from. It is not passed when
# the host has set the environment variable below.
HOSTED_MAX_UPLOAD_MB = 500
LOCAL_MAX_UPLOAD_MB = 5000
UPLOAD_CAP_ENV = "STREAMLIT_SERVER_MAX_UPLOAD_SIZE"

# Addresses that only this machine can reach.
_LOOPBACK_ADDRESSES = ("localhost", "127.0.0.1", "::1")


def _skip_streamlit_email_prompt() -> None:
    """Write an empty Streamlit credentials file if the user has none, so the
    one-time first-run email prompt doesn't block a fresh `fibermorph-gui`.

    Non-destructive: never overwrites an existing credentials file.
    """
    cred = Path.home() / ".streamlit" / "credentials.toml"
    try:
        if not cred.exists():
            cred.parent.mkdir(parents=True, exist_ok=True)
            cred.write_text('[general]\nemail = ""\n')
    except OSError:
        pass  # non-fatal: worst case, Streamlit shows its usual prompt


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fibermorph-gui",
        description=(
            "Launch the fibermorph GUI. With no flags it starts in hosted mode: "
            "uploads only, with a 500 MB upload cap. Use --local to run on your "
            "own machine."
        ),
        epilog=(
            "Any other arguments are passed through to `streamlit run` after "
            "fibermorph's defaults, so they can override them "
            "(for example: fibermorph-gui --local --server.port 8600). "
            "fibermorph passes --server.maxUploadSize (500 MB hosted, 5000 MB "
            "local) unless the STREAMLIT_SERVER_MAX_UPLOAD_SIZE environment "
            "variable is set, and in local mode always passes "
            "--server.address localhost. Command-line options take precedence "
            "over environment variables and .streamlit/config.toml, so to "
            "change the bind address use --server.address on this command "
            "line (the STREAMLIT_SERVER_ADDRESS variable has no effect in "
            "local mode)."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help=(
            "Run in local mode, for use on your own computer: adds a 'Folder on "
            "disk' input that reads images from this machine, raises the upload "
            "cap to 5 GB, and listens on localhost only. Do not use on a shared "
            "server: every visitor could read folders on it. Setting the "
            "environment variable FIBERMORPH_LOCAL=1 does the same."
        ),
    )
    return parser


def _option_value(args, name):
    """Last value given for ``name`` in ``args`` (as ``--name value`` or
    ``--name=value``), or None if it was not given."""
    value = None
    for i, arg in enumerate(args):
        if arg == name and i + 1 < len(args):
            value = args[i + 1]
        elif arg.startswith(name + "="):
            value = arg[len(name) + 1:]
    return value


def _upload_cap_mb(local: bool, extra_args) -> str:
    """The upload cap (MB) the app will run with, for the startup notice."""
    given = _option_value(extra_args, "--server.maxUploadSize")
    if given is not None:
        return given
    if os.environ.get(UPLOAD_CAP_ENV):
        return os.environ[UPLOAD_CAP_ENV]
    return str(LOCAL_MAX_UPLOAD_MB if local else HOSTED_MAX_UPLOAD_MB)


def _build_streamlit_argv(local: bool, app_path: Path, extra_args) -> list:
    """Return the ``sys.argv`` for ``streamlit run``.

    Defaults come first and user-supplied ``extra_args`` last, so a user can
    override any default (Streamlit uses the last value given for an option).
    """
    defaults = []
    if not os.environ.get(UPLOAD_CAP_ENV):
        # A command-line option would outrank the host's environment variable,
        # so only pass the cap when the host has not chosen one.
        cap = LOCAL_MAX_UPLOAD_MB if local else HOSTED_MAX_UPLOAD_MB
        defaults += ["--server.maxUploadSize", str(cap)]
    if local:
        # Always passed (even if STREAMLIT_SERVER_ADDRESS is set): local mode
        # reads folders on this machine, so only an explicit command-line
        # --server.address may open it to other machines.
        defaults += ["--server.address", "localhost"]
    return ["streamlit", "run", str(app_path), *defaults, *extra_args]


def _startup_notice(local: bool, extra_args) -> str:
    cap = _upload_cap_mb(local, extra_args)
    if not local:
        return (
            f"fibermorph-gui: starting in hosted mode (uploads only, {cap} MB "
            "upload cap). To run on your own machine with folder input and "
            "5 GB uploads, use: fibermorph-gui --local"
        )
    address = _option_value(extra_args, "--server.address")
    if address is None:
        address = "localhost"  # the launcher's own default (see above)
    notice = f"fibermorph-gui: starting in local mode (folder input, {cap} MB uploads"
    if address in _LOOPBACK_ADDRESSES:
        return notice + ", localhost only)."
    # An empty --server.address is not "unset" to Streamlit: it listens on
    # every interface (0.0.0.0), so it is reported as wider than localhost.
    listening = address or "all network interfaces"
    return (
        notice + f", listening on {listening}). WARNING: anyone who can reach this "
        "machine over the network can read folders on it."
    )


def main(argv=None) -> None:
    """Launch the Streamlit GUI by running streamlit with the app module.

    ``argv`` defaults to ``sys.argv[1:]``.
    """
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print(
            "Error: Streamlit is not installed. "
            "Install it with: pip install 'fibermorph[gui]'",
            file=sys.stderr,
        )
        sys.exit(1)

    args, extra_args = _build_parser().parse_known_args(
        sys.argv[1:] if argv is None else argv
    )

    # Local mode is opt-in: the --local flag, or FIBERMORPH_LOCAL=1 already set
    # in the environment. It unlocks features that only make sense on the
    # user's own machine (reading images straight from a folder on disk), and
    # lets anyone who can reach the app read folders on this machine. Hosted
    # mode never sets the variable.
    local = args.local or os.environ.get("FIBERMORPH_LOCAL") == "1"
    if local:
        os.environ["FIBERMORPH_LOCAL"] = "1"

    # On a machine's first-ever Streamlit run, Streamlit interactively prompts
    # for an email and blocks until the user answers — confusing for a launcher.
    # Pre-seed an empty credentials file (only if the user has none) so
    # `fibermorph-gui` starts straight into the app.
    _skip_streamlit_email_prompt()

    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    print(_startup_notice(local, extra_args), file=sys.stderr)

    sys.argv = _build_streamlit_argv(local, app_path, extra_args)
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
