"""Streamlit AppTest checks for hosted vs local mode in fibermorph/gui/app.py.

Hosted mode (FIBERMORPH_LOCAL unset) must not offer anything that touches the
server's disk, such as the "Folder on disk" input. The Run Local view must tell
people to start local mode with `fibermorph-gui --local`.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import fibermorph.gui  # noqa: E402

APP_PATH = str(Path(fibermorph.gui.__file__).parent / "app.py")


def _run_app(monkeypatch, local, view="section", env=None):
    """Run the app once in hosted or local mode and return the AppTest."""
    if local:
        monkeypatch.setenv("FIBERMORPH_LOCAL", "1")
    else:
        monkeypatch.delenv("FIBERMORPH_LOCAL", raising=False)
    for name, value in (env or {}).items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.session_state["active_view"] = view
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _labels(elements):
    return [e.label for e in elements]


# ---------------------------------------------------------------------------
# Hosted vs local: folder input
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("view", ["section", "curvature"])
def test_hosted_has_no_folder_on_disk_option(monkeypatch, view):
    at = _run_app(monkeypatch, local=False, view=view)
    assert "Input source" not in _labels(at.radio)
    assert not [t for t in at.text_input if t.label.startswith("Folder containing")]
    assert len(at.file_uploader) == 1


@pytest.mark.parametrize("view", ["section", "curvature"])
def test_local_offers_folder_on_disk_option(monkeypatch, view):
    at = _run_app(monkeypatch, local=True, view=view)
    radios = [r for r in at.radio if r.label == "Input source"]
    assert len(radios) == 1
    assert "Folder on disk" in radios[0].options
    radios[0].set_value("Folder on disk")
    at.run()
    assert [t for t in at.text_input if t.label.startswith("Folder containing")]


# ---------------------------------------------------------------------------
# User-facing text
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("local", [False, True])
def test_run_local_view_says_to_use_local_flag(monkeypatch, local):
    at = _run_app(monkeypatch, local=local, view="local")
    text = "\n".join(m.value for m in at.markdown)
    assert "fibermorph-gui --local" in text
    # No instruction still tells people to run bare `fibermorph-gui` for local mode.
    for line in text.splitlines():
        if line.strip() == "fibermorph-gui":
            pytest.fail("Run Local view still shows bare `fibermorph-gui`")


def test_run_local_view_status_hosted_vs_local(monkeypatch):
    hosted = _run_app(monkeypatch, local=False, view="local")
    assert not hosted.success
    assert any("--local" in i.value for i in hosted.info)
    local = _run_app(monkeypatch, local=True, view="local")
    assert any("running locally" in s.value for s in local.success)
