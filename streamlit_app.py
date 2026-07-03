"""Entry point for Streamlit Cloud deployment.

Executes fibermorph/gui/app.py in its own namespace on every Streamlit
re-run (the app script is top-level code, not a main() function). The
globals dict pins __file__ to app.py's real path so the app's
__file__-relative lookups (e.g. the SAM2 checkpoint resolver) work.
"""
from pathlib import Path

_APP_PATH = Path(__file__).parent / "fibermorph" / "gui" / "app.py"

exec(  # noqa: S102
    compile(_APP_PATH.read_text(), str(_APP_PATH), "exec"),
    {"__file__": str(_APP_PATH), "__name__": "__main__"},
)
