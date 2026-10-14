"""SAM2 loading in section_sam2: empty config/checkpoint values from the CLI
("" when --sam2-cfg / --sam2-checkpoint are not given) must fall back to the
defaults instead of making SAM2 fail to load and silently use watershed."""

import types

import pytest

from fibermorph.processing import section_sam2


@pytest.fixture
def fake_sam2(monkeypatch, tmp_path):
    """Pretend sam2 + a CUDA GPU are present; record what build_sam2 receives."""
    calls = {}

    def build_sam2(cfg, ckpt, device, apply_postprocessing):
        calls.update(cfg=cfg, ckpt=ckpt, device=device)
        return object()

    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: True))
    monkeypatch.setattr(section_sam2, "_SAM2_AVAILABLE", True)
    monkeypatch.setattr(section_sam2, "torch", fake_torch, raising=False)
    monkeypatch.setattr(section_sam2, "build_sam2", build_sam2, raising=False)
    monkeypatch.setattr(section_sam2, "SAM2AutomaticMaskGenerator",
                        lambda model, **kw: ("generator", model), raising=False)
    monkeypatch.setattr(section_sam2, "_sam2_generator", None)
    monkeypatch.setattr(section_sam2, "_sam2_init_logged", False)
    monkeypatch.delenv("SAM2_CHECKPOINT", raising=False)
    ckpt = tmp_path / "model.pt"
    ckpt.write_bytes(b"x")
    return calls, ckpt


def test_empty_model_cfg_uses_default_config(fake_sam2):
    calls, ckpt = fake_sam2
    assert section_sam2._get_sam2_generator(str(ckpt), "") is not None
    assert calls["cfg"] == section_sam2._DEFAULT_CFG
    assert calls["ckpt"] == str(ckpt)
    assert calls["device"] == "cuda"


def test_explicit_model_cfg_is_kept(fake_sam2):
    calls, ckpt = fake_sam2
    section_sam2._get_sam2_generator(str(ckpt), "configs/sam2.1/sam2.1_hiera_s.yaml")
    assert calls["cfg"] == "configs/sam2.1/sam2.1_hiera_s.yaml"


def test_empty_checkpoint_uses_sam2_checkpoint_env(fake_sam2, monkeypatch):
    calls, ckpt = fake_sam2
    monkeypatch.setenv("SAM2_CHECKPOINT", str(ckpt))
    assert section_sam2._get_sam2_generator("", "") is not None
    assert calls["ckpt"] == str(ckpt)


def test_default_checkpoint_is_inside_the_package():
    # The README says to put the checkpoint in fibermorph/checkpoints/ (the
    # package directory), which is also where the GUI looks.
    pkg_dir = section_sam2._PKG_DIR
    assert (pkg_dir / "processing" / "section_sam2.py").exists()
    assert section_sam2._CKPT_CANDIDATES[0] == pkg_dir / "checkpoints" / "sam2.1_hiera_tiny.pt"
