"""Tests for the GUI launcher's first-run email-prompt skip."""

from fibermorph.gui import launcher


def test_skip_email_prompt_creates_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))          # Path.home() honors HOME on POSIX
    launcher._skip_streamlit_email_prompt()
    cred = tmp_path / ".streamlit" / "credentials.toml"
    assert cred.exists()
    assert 'email = ""' in cred.read_text()


def test_skip_email_prompt_preserves_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cred = tmp_path / ".streamlit" / "credentials.toml"
    cred.parent.mkdir(parents=True)
    cred.write_text('[general]\nemail = "real@example.com"\n')
    launcher._skip_streamlit_email_prompt()
    assert "real@example.com" in cred.read_text(), "existing credentials must not be clobbered"
