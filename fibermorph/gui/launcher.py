"""Launcher script for fibermorph GUI via Streamlit."""

from __future__ import annotations

import os
import sys
from pathlib import Path


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
