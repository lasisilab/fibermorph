"""GUI entry points for fibermorph."""

from importlib import import_module


def main() -> None:
    """Launch the Streamlit application."""
    app = import_module(".app", package=__name__)
    app.main()
