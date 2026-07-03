"""GUI entry points for fibermorph."""


def main() -> None:
    """Launch the Streamlit application.

    The v2 app (fibermorph/gui/app.py) is a top-level Streamlit script
    with no main() function, so it must be started through `streamlit
    run`; delegate to the launcher, which does exactly that.
    """
    from .launcher import main as launch

    launch()
