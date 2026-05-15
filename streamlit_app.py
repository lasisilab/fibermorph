"""Entry point for Streamlit Cloud deployment.

Runs fibermorph/gui/app.py via exec so Streamlit's re-run model works
correctly (module imports are cached; exec re-executes every re-run).
"""
from pathlib import Path

exec(  # noqa: S102
    compile(
        (Path(__file__).parent / "fibermorph" / "gui" / "app.py").read_text(),
        "fibermorph/gui/app.py",
        "exec",
    )
)