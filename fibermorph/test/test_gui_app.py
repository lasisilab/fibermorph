"""Streamlit AppTest checks for hosted vs local mode in fibermorph/gui/app.py.

Hosted mode (FIBERMORPH_LOCAL unset) must not offer anything that touches the
server's disk: no "Folder on disk" input, no SAM2 checkpoint path box, and the
server's SAM2 checkpoint path is not shown anywhere (the Run Remote view's
checkpoint box, which only fills in an SBATCH script, starts empty). Uploads
must be measured separately even when file names repeat, and must report the
uploaded file names, not the names of the temporary files. The Run Local view
must tell people to start local mode with `fibermorph-gui --local`.
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


def test_hosted_caption_says_checkpoint_is_found_without_showing_path(monkeypatch, tmp_path):
    ckpt = tmp_path / "private_model_dir" / "model.pt"
    ckpt.parent.mkdir()
    ckpt.write_bytes(b"x")
    at = _run_app(monkeypatch, local=False, env={"SAM2_CHECKPOINT": str(ckpt)})
    captions = [c.value for c in at.caption if c.value.startswith("SAM2 checkpoint")]
    assert len(captions) == 1
    assert "file found on this server" in captions[0]
    assert "no file found" not in captions[0]
    # A checkpoint file alone does not make SAM2 usable: the caption says a GPU
    # is needed too, so it does not promise SAM2 where only a file exists.
    assert "GPU" in captions[0] and "watershed" in captions[0]
    assert not [t for t in _rendered_text(at) if "private_model_dir" in t]


def test_hosted_caption_says_when_no_checkpoint_file_is_found(monkeypatch, tmp_path):
    missing = tmp_path / "private_model_dir" / "absent.pt"
    at = _run_app(monkeypatch, local=False, env={"SAM2_CHECKPOINT": str(missing)})
    captions = [c.value for c in at.caption if c.value.startswith("SAM2 checkpoint")]
    assert len(captions) == 1
    assert "no file found" in captions[0]
    assert "watershed" in captions[0]
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
# Uploads: hostile names, duplicate names, and reported file names
# ---------------------------------------------------------------------------

@needs_upload_support
def test_section_duplicate_uploads_are_measured_separately_and_named_as_uploaded(
        monkeypatch, tmp_path):
    escape = tmp_path / "escaped.png"
    at = _run_app(monkeypatch, local=False)
    at.file_uploader[0].set_value([
        ("sample.png", _section_png(100), "image/png"),
        ("sample.png", _section_png(130), "image/png"),
        (str(escape), _section_png(110), "image/png"),
        ("..\\..\\win\\path.png", _section_png(120), "image/png"),
    ])
    at.run()
    _click(at, "sec_run")

    df = at.session_state["section_results"]
    assert list(df["source_file"]) == ["sample.png", "sample.png", "escaped.png", "path.png"]
    # Every column that carries a file name shows the uploaded name, never
    # the generated temp name (upload_0001.png ...).
    assert list(df["ID"]) == list(df["source_file"])
    assert list(df["mask_filename"]) == list(df["source_file"])
    assert "upload_" not in df.to_csv(index=False)
    # The two "sample.png" uploads are different images and give different areas.
    assert df["area_mu2"].iloc[0] != pytest.approx(df["area_mu2"].iloc[1], rel=0.05)
    assert [name for name, _, _ in at.session_state["seg_store"]] == list(df["source_file"])
    assert not escape.exists()
    assert any("Duplicate filenames" in w.value and "sample.png" in w.value for w in at.warning)


@needs_upload_support
def test_curvature_duplicate_uploads_are_measured_separately_and_named_as_uploaded(
        monkeypatch):
    def fiber_png(amplitude, size=800):
        img = np.full((size, size), 230, dtype=np.uint8)
        xs = np.arange(40, size - 40)
        ys = (size // 2 + amplitude * np.sin(2 * np.pi * 2 * xs / size)).astype(int)
        for x, y in zip(xs, ys):
            img[y - 2:y + 3, x] = 20
        buf = io.BytesIO()
        Image.fromarray(img, mode="L").save(buf, format="PNG")
        return buf.getvalue()

    at = _run_app(monkeypatch, local=False, view="curvature")
    at.file_uploader[0].set_value([
        ("fiber.png", fiber_png(20), "image/png"),
        ("../../fiber.png", fiber_png(80), "image/png"),
    ])
    at.run()
    _click(at, "curv_run")

    frags = at.session_state["curvature_fragments"]
    summ = at.session_state["curvature_summary"]
    assert list(frags["source_file"]) == ["fiber.png", "fiber.png"]
    assert list(summ["source_file"]) == ["fiber.png", "fiber.png"]
    assert "upload_" not in frags.to_csv(index=False)
    assert "upload_" not in summ.to_csv(index=False)
    # Two different images, so two different measurements (not the second one twice).
    assert frags["length"].iloc[0] != pytest.approx(frags["length"].iloc[1], rel=0.01)
    assert summ["length_mean"].iloc[0] != pytest.approx(summ["length_mean"].iloc[1], rel=0.01)
    assert any("Duplicate filenames" in w.value for w in at.warning)


@needs_upload_support
def test_unreadable_upload_error_names_the_uploaded_file(monkeypatch):
    at = _run_app(monkeypatch, local=False, view="curvature")
    at.file_uploader[0].set_value([("my scan.tif", b"not an image", "image/tiff")])
    at.run()
    _click(at, "curv_run")
    messages = [w.value for w in at.warning]
    assert any(m.startswith("my scan.tif: ") for m in messages), messages
    assert not any("upload_" in m for m in messages), messages


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


# ---------------------------------------------------------------------------
# The upload cap shown in the app is the cap Streamlit enforces
# ---------------------------------------------------------------------------

@pytest.fixture
def set_upload_cap():
    """Set Streamlit's server.maxUploadSize (in MB) for one test, then restore it."""
    from streamlit import config
    original = config.get_option("server.maxUploadSize")

    def setter(megabytes):
        config.set_option("server.maxUploadSize", megabytes)

    yield setter
    config.set_option("server.maxUploadSize", original)


@pytest.mark.parametrize("megabytes, shown", [
    (500, "500 MB"), (2000, "2 GB"), (750, "750 MB"),
])
def test_hosted_text_follows_the_configured_upload_cap(monkeypatch, set_upload_cap, megabytes, shown):
    set_upload_cap(megabytes)
    at = _run_app(monkeypatch, local=False, view="local")
    footer = [m.value for m in at.sidebar.markdown if "fm-foot__status" in m.value]
    assert len(footer) == 1 and f"Hosted · {shown} upload cap" in footer[0]
    body = "\n".join(m.value for m in at.markdown)
    assert f"caps uploads ({shown} here)" in body
    assert any(f"upload-only, {shown}" in i.value for i in at.info)
    others = {"500 MB", "2 GB", "750 MB", "5 GB"} - {shown}
    page = "\n".join(_rendered_text(at))
    assert not [o for o in others if o in page], [o for o in others if o in page]


@pytest.mark.parametrize("megabytes, shown", [
    (5000, "5 GB"), (2000, "2 GB"), (300, "300 MB"),
])
def test_local_text_follows_the_configured_upload_cap(monkeypatch, set_upload_cap, megabytes, shown):
    set_upload_cap(megabytes)
    at = _run_app(monkeypatch, local=True, view="local")
    footer = [m.value for m in at.sidebar.markdown if "fm-foot__status" in m.value]
    assert len(footer) == 1 and f"Local · {shown} cap · folder input" in footer[0]
    assert any(f"capped at {shown}" in s.value for s in at.success)
    others = {"500 MB", "2 GB", "300 MB", "5 GB"} - {shown}
    page = "\n".join(_rendered_text(at))
    assert not [o for o in others if o in page], [o for o in others if o in page]
