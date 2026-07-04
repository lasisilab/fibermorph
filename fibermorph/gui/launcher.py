"""Launcher script for fibermorph GUI via Streamlit."""

from __future__ import annotations

import os
import sys
from pathlib import Path


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


def main() -> None:
    """Launch the Streamlit GUI by running streamlit with the app module."""
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print(
            "Error: Streamlit is not installed. "
            "Install it with: pip install 'fibermorph[gui]'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Mark this as a LOCAL launch. The app uses this to unlock features that
    # only make sense on the user's own machine — reading images straight from
    # a folder on disk (no upload, no size limit).
    os.environ.setdefault("FIBERMORPH_LOCAL", "1")

    # On a machine's first-ever Streamlit run, Streamlit interactively prompts
    # for an email and blocks until the user answers — confusing for a launcher.
    # Pre-seed an empty credentials file (only if the user has none) so
    # `fibermorph-gui` starts straight into the app.
    _skip_streamlit_email_prompt()

    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    # Run the app locally with a high upload ceiling (browser uploads are only
    # a hosted-app limitation; locally you can also use the folder-path input).
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.maxUploadSize", "5000",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
