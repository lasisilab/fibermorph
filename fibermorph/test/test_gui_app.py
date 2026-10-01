"""Streamlit AppTest checks for hosted vs local mode in fibermorph/gui/app.py.

Hosted mode (FIBERMORPH_LOCAL unset) must not offer anything that touches the
server's disk: no "Folder on disk" input, no SAM2 checkpoint path box, and the
server's SAM2 checkpoint path is not shown anywhere (the Run Remote view's
checkpoint box, which only fills in an SBATCH script, starts empty). The Run
Local view must tell people to start local mode with `fibermorph-gui --local`.
"""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from skimage import draw as sk_draw

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import fibermorph.gui  # noqa: E402

APP_PATH = str(Path(fibermorph.gui.__file__).parent / "app.py")
CKPT_LABEL = "SAM2 checkpoint path"

needs_upload_support = pytest.mark.skipif(
    not hasattr(AppTest, "file_uploader"),
    reason="this Streamlit version's AppTest cannot simulate file uploads",
)


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


def _click(at, key):
    [b for b in at.button if b.key == key][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def _rendered_text(at):
    """Every string the app put on the page, as a list.

    Walks all elements, including widget labels, help, placeholders and the
    initial value of text boxes (via each element's protobuf), plus the current
    value of each widget. Used to check that something appears nowhere.
    """
    out = []

    def walk(node):
        for child in getattr(node, "children", {}).values():
            proto = getattr(child, "proto", None)
            if proto is not None:
                out.append(str(proto))
            value = getattr(child, "value", None)
            if value is not None:
                out.append(str(value))
            walk(child)

    walk(at.main)
    walk(at.sidebar)
    return out


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
# Hosted vs local: SAM2 checkpoint path
# ---------------------------------------------------------------------------

def test_hosted_has_no_sam2_checkpoint_text_input(monkeypatch):
    at = _run_app(monkeypatch, local=False)
    assert CKPT_LABEL not in _labels(at.text_input)


def test_local_has_sam2_checkpoint_text_input(monkeypatch, tmp_path):
    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"x")
    at = _run_app(monkeypatch, local=True, env={"SAM2_CHECKPOINT": str(ckpt)})
    boxes = [t for t in at.text_input if t.label == CKPT_LABEL]
    assert len(boxes) == 1
    assert boxes[0].value == str(ckpt)


def test_hosted_caption_says_checkpoint_is_configured_without_showing_path(monkeypatch, tmp_path):
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    ckpt.parent.mkdir()
    ckpt.write_bytes(b"x")
    at = _run_app(monkeypatch, local=False, env={"SAM2_CHECKPOINT": str(ckpt)})
    captions = [c.value for c in at.caption if c.value.startswith("SAM2 checkpoint")]
    assert len(captions) == 1
    assert "configured on this server" in captions[0]
    assert "none configured" not in captions[0]
    assert not [t for t in _rendered_text(at) if "private_model_dir" in t]


def test_hosted_caption_says_when_no_checkpoint_is_configured(monkeypatch, tmp_path):
    missing = tmp_path / "private_model_dir" / "absent.pt"
    at = _run_app(monkeypatch, local=False, env={"SAM2_CHECKPOINT": str(missing)})
    captions = [c.value for c in at.caption if c.value.startswith("SAM2 checkpoint")]
    assert len(captions) == 1
    assert "none configured" in captions[0]
    assert "private_model_dir" not in captions[0]


@pytest.mark.parametrize("view", ["section", "curvature", "local", "remote"])
@pytest.mark.parametrize("exists", [True, False], ids=["checkpoint-present", "checkpoint-missing"])
def test_hosted_views_never_show_the_server_checkpoint_path(monkeypatch, tmp_path, view, exists):
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    if exists:
        ckpt.parent.mkdir()
        ckpt.write_bytes(b"x")
    at = _run_app(monkeypatch, local=False, view=view, env={"SAM2_CHECKPOINT": str(ckpt)})
    shown = _rendered_text(at)
    assert shown
    assert not [t for t in shown if "private_model_dir" in t]


def test_rendered_text_helper_does_see_the_path_in_local_mode(monkeypatch, tmp_path):
    # Guards the test above against passing only because the helper sees nothing.
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    for view in ("section", "remote"):
        at = _run_app(monkeypatch, local=True, view=view, env={"SAM2_CHECKPOINT": str(ckpt)})
        assert [t for t in _rendered_text(at) if "private_model_dir" in t]


def _remote_checkpoint_box(at):
    boxes = [t for t in at.text_input if t.label == CKPT_LABEL]
    assert len(boxes) == 1
    return boxes[0]


def _generate_script(at, section_dir="/data/sections"):
    at.text_input(key="section_path").set_value(section_dir)
    [t for t in at.toggle if t.label.startswith("Enable SAM2")][0].set_value(True)
    at.run()
    _click(at, "gen_sbatch")
    return at.session_state["sbatch_script"]


def test_hosted_remote_checkpoint_box_starts_empty_with_a_placeholder(monkeypatch, tmp_path):
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    at = _run_app(monkeypatch, local=False, view="remote", env={"SAM2_CHECKPOINT": str(ckpt)})
    box = _remote_checkpoint_box(at)
    assert box.value == ""
    assert box.placeholder.startswith("/path/to/")


def test_local_remote_checkpoint_box_is_prefilled(monkeypatch, tmp_path):
    ckpt = tmp_path / "model.pt"
    at = _run_app(monkeypatch, local=True, view="remote", env={"SAM2_CHECKPOINT": str(ckpt)})
    assert _remote_checkpoint_box(at).value == str(ckpt)


def test_hosted_script_uses_placeholder_for_blank_checkpoint(monkeypatch, tmp_path):
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    at = _run_app(monkeypatch, local=False, view="remote", env={"SAM2_CHECKPOINT": str(ckpt)})
    script = _generate_script(at)
    assert "--use-sam2" in script
    assert "--sam2-checkpoint 'YOUR_SAM2_CHECKPOINT'" in script
    assert "private_model_dir" not in script
    assert not [t for t in _rendered_text(at) if "private_model_dir" in t]


@pytest.mark.parametrize("local", [False, True], ids=["hosted", "local"])
def test_script_uses_the_checkpoint_typed_for_the_cluster(monkeypatch, tmp_path, local):
    at = _run_app(monkeypatch, local=local, view="remote",
                  env={"SAM2_CHECKPOINT": str(tmp_path / "private_model_dir" / "model.pt")})
    _remote_checkpoint_box(at).set_value("/cluster/models/sam2.pt")
    script = _generate_script(at)
    assert "--sam2-checkpoint '/cluster/models/sam2.pt'" in script
    assert "private_model_dir" not in script


# ---------------------------------------------------------------------------
# Which checkpoint reaches segment_section
# ---------------------------------------------------------------------------

def _section_png(radius, size=500):
    img = np.full((size, size), 220, dtype=np.uint8)
    rr, cc = sk_draw.disk((size // 2, size // 2), radius, shape=img.shape)
    img[rr, cc] = 30
    buf = io.BytesIO()
    Image.fromarray(img, mode="L").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def seen_checkpoints(monkeypatch):
    """Record the checkpoint= argument of every segment_section call."""
    from fibermorph.processing import section_sam2

    real = section_sam2.segment_section
    seen = []

    def spy(*args, **kwargs):
        seen.append(kwargs.get("checkpoint"))
        return real(*args, **kwargs)

    monkeypatch.setattr(section_sam2, "segment_section", spy)
    return seen


@needs_upload_support
def test_hosted_ignores_a_client_supplied_checkpoint(monkeypatch, tmp_path, seen_checkpoints):
    server_ckpt = str(tmp_path / "server_model.pt")
    at = _run_app(monkeypatch, local=False, env={"SAM2_CHECKPOINT": server_ckpt})
    # A client that sends widget state for the (non-existent) checkpoint box
    # must not be able to choose what the server loads.
    at.session_state["sec_ckpt"] = "/attacker/chosen/model.pt"
    at.file_uploader[0].set_value(("one.png", _section_png(100), "image/png"))
    at.run()
    _click(at, "sec_run")
    assert seen_checkpoints == [server_ckpt]


@needs_upload_support
def test_local_uses_the_checkpoint_typed_in_the_box(monkeypatch, tmp_path, seen_checkpoints):
    at = _run_app(monkeypatch, local=True, env={"SAM2_CHECKPOINT": str(tmp_path / "default.pt")})
    chosen = str(tmp_path / "my_model.pt")
    [t for t in at.text_input if t.label == CKPT_LABEL][0].set_value(chosen)
    at.file_uploader[0].set_value(("one.png", _section_png(100), "image/png"))
    at.run()
    _click(at, "sec_run")
    assert seen_checkpoints == [chosen]


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
