"""Launcher script for fibermorph GUI via Streamlit."""

from __future__ import annotations

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

    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    # Use streamlit's CLI to run the app
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
