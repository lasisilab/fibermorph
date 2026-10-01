"""Tests for fibermorph.gui.inputs: safe handling of uploaded files."""

import io
import os

import pytest

from fibermorph.gui import inputs


class FakeUpload:
    """Minimal stand-in for Streamlit's UploadedFile (name + read())."""

    def __init__(self, name, data=b"data"):
        self.name = name
        self._buf = io.BytesIO(data)

    def read(self):
        return self._buf.read()


def _tree(root):
    """Every file under root, as paths relative to root."""
    return sorted(
        os.path.relpath(os.path.join(d, f), root)
        for d, _, files in os.walk(root) for f in files
    )


# ---------------------------------------------------------------------------
# format_upload_cap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("megabytes, expected", [
    (200, "200 MB"),
    (500, "500 MB"),
    (999, "999 MB"),
    (1000, "1 GB"),
    (2000, "2 GB"),
    (2500, "2500 MB"),
    (5000, "5 GB"),
    ("5000", "5 GB"),
])
def test_format_upload_cap(megabytes, expected):
    assert inputs.format_upload_cap(megabytes) == expected


# ---------------------------------------------------------------------------
# display_name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("client_name, expected", [
    ("sample.tif", "sample.tif"),
    ("my scan (1).PNG", "my scan (1).PNG"),
    ("/etc/passwd", "passwd"),
    ("/abs/dir/hair.tiff", "hair.tiff"),
    ("../../escape.tif", "escape.tif"),
    ("a/../../b.jpg", "b.jpg"),
    ("C:\\Users\\me\\scan.tif", "scan.tif"),
    ("..\\..\\scan.tif", "scan.tif"),
    ("mixed/dir\\scan.png", "scan.png"),
    ("trailing.tif ", "trailing.tif"),
    ("bad\x00name\n.tif", "badname.tif"),
])
def test_display_name_keeps_last_component(client_name, expected):
    assert inputs.display_name(client_name) == expected


@pytest.mark.parametrize("client_name", ["", None, ".", "..", "/", "\\", "a/", "a\\..", "  ", "\x00"])
def test_display_name_falls_back_when_nothing_usable(client_name):
    assert inputs.display_name(client_name, fallback="upload_0007.tif") == "upload_0007.tif"


# ---------------------------------------------------------------------------
# safe_extension
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("client_name, expected", [
    ("a.tif", ".tif"),
    ("a.TIFF", ".tiff"),
    ("a.Png", ".png"),
    ("a.jpg", ".jpg"),
    ("a.jpeg", ".jpeg"),
    ("archive.tar.tif", ".tif"),
    ("dir.tif/noext", ""),        # extension of a parent component doesn't count
    ("a.exe", ""),
    ("a.tif.exe", ""),
    ("a.py", ""),
    ("a.", ""),
    (".tif", ""),                  # a dotfile has no extension
    ("noext", ""),
    ("", ""),
    (None, ""),
    ("a.t if", ""),
    ("a.tif/../b.sh", ""),
])
def test_safe_extension_only_for_accepted_types(client_name, expected):
    assert inputs.safe_extension(client_name) == expected


def test_upload_types_match_what_the_app_accepts():
    assert inputs.UPLOAD_TYPES == ["tif", "tiff", "png", "jpg", "jpeg"]


# ---------------------------------------------------------------------------
# save_uploads
# ---------------------------------------------------------------------------

def test_save_uploads_uses_generated_names_and_keeps_content(tmp_path):
    ups = [FakeUpload("first.tif", b"AAA"), FakeUpload("second.PNG", b"BBB")]
    out = inputs.save_uploads(ups, str(tmp_path))
    assert [n for n, _ in out] == ["first.tif", "second.PNG"]
    assert [os.path.basename(p) for _, p in out] == ["upload_0001.tif", "upload_0002.png"]
    assert [open(p, "rb").read() for _, p in out] == [b"AAA", b"BBB"]


@pytest.mark.parametrize("hostile", [
    "/tmp/fibermorph_should_not_exist.tif",
    "../../fibermorph_should_not_exist.tif",
    "../fibermorph_should_not_exist.tif",
    "a/../../fibermorph_should_not_exist.tif",
    "..\\..\\fibermorph_should_not_exist.tif",
    "C:\\Windows\\fibermorph_should_not_exist.tif",
    "\\\\server\\share\\fibermorph_should_not_exist.tif",
    "sub/dir/file.tif",
    "..",
    ".",
    "",
    "/",
])
def test_hostile_names_never_escape_tmpdir(tmp_path, hostile):
    outer = tmp_path / "outer"
    tmpdir = outer / "work"
    tmpdir.mkdir(parents=True)
    out = inputs.save_uploads([FakeUpload(hostile, b"x")], str(tmpdir))

    assert len(out) == 1
    _, path = out[0]
    assert os.path.dirname(os.path.abspath(path)) == str(tmpdir)
    assert os.path.basename(path).startswith("upload_0001")
    # Nothing was created anywhere except directly inside tmpdir.
    assert _tree(str(outer)) == [os.path.join("work", os.path.basename(path))]
    assert not os.path.exists("/tmp/fibermorph_should_not_exist.tif")


def test_duplicate_names_become_distinct_files(tmp_path):
    ups = [FakeUpload("same.tif", b"one"), FakeUpload("same.tif", b"two"),
           FakeUpload("same.tif", b"three")]
    out = inputs.save_uploads(ups, str(tmp_path))
    paths = [p for _, p in out]
    assert len(set(paths)) == 3
    assert [n for n, _ in out] == ["same.tif"] * 3          # display names are the original
    assert [open(p, "rb").read() for p in paths] == [b"one", b"two", b"three"]


def test_names_differing_only_by_directory_do_not_collide(tmp_path):
    ups = [FakeUpload("a/x.tif", b"1"), FakeUpload("b/x.tif", b"2")]
    out = inputs.save_uploads(ups, str(tmp_path))
    assert [n for n, _ in out] == ["x.tif", "x.tif"]
    assert [open(p, "rb").read() for _, p in out] == [b"1", b"2"]


def test_empty_name_gets_generated_display_name(tmp_path):
    out = inputs.save_uploads([FakeUpload("", b"x"), FakeUpload("..", b"y")], str(tmp_path))
    assert [n for n, _ in out] == ["upload_0001", "upload_0002"]
    assert [os.path.basename(p) for _, p in out] == ["upload_0001", "upload_0002"]


def test_unaccepted_extension_is_not_kept_on_disk(tmp_path):
    out = inputs.save_uploads([FakeUpload("evil.sh"), FakeUpload("x.tif.exe")], str(tmp_path))
    assert [os.path.basename(p) for _, p in out] == ["upload_0001", "upload_0002"]
    assert [n for n, _ in out] == ["evil.sh", "x.tif.exe"]   # still shown as uploaded


def test_save_uploads_handles_none_and_empty(tmp_path):
    assert inputs.save_uploads(None, str(tmp_path)) == []
    assert inputs.save_uploads([], str(tmp_path)) == []
    assert _tree(str(tmp_path)) == []


def test_pre_existing_files_are_not_overwritten_by_other_names(tmp_path):
    # A file the app already has in tmpdir can't be clobbered by choosing its name.
    (tmp_path / "important.tif").write_bytes(b"keep")
    inputs.save_uploads([FakeUpload("important.tif", b"new")], str(tmp_path))
    assert (tmp_path / "important.tif").read_bytes() == b"keep"


# ---------------------------------------------------------------------------
# restore_names
# ---------------------------------------------------------------------------

def test_restore_names_replaces_generated_name_and_path(tmp_path):
    (name, path), = inputs.save_uploads([FakeUpload("../x/scan.tif")], str(tmp_path))
    assert name == "scan.tif"
    msg = f"Cannot identify image file 'upload_0001.tif' (read {path})"
    assert inputs.restore_names(msg, path, name) == (
        "Cannot identify image file 'scan.tif' (read scan.tif)")


def test_restore_names_leaves_other_text_alone(tmp_path):
    path = str(tmp_path / "upload_0001.tif")
    assert inputs.restore_names("something else", path, "scan.tif") == "something else"
    assert inputs.restore_names(ValueError("bad upload_0001.tif"), path, "scan.tif") == "bad scan.tif"


def test_restore_names_only_replaces_whole_names(tmp_path):
    # An upload saved without an extension ("upload_0001") must not be matched
    # inside another upload's name ("upload_00010.tif").
    path = str(tmp_path / "upload_0001")
    msg = f"bad upload_0001 and upload_00010.tif and {path} and {path}0"
    assert inputs.restore_names(msg, path, "N") == "bad N and upload_00010.tif and N and " + path + "0"


def test_restore_names_handles_punctuation_around_the_name(tmp_path):
    path = str(tmp_path / "upload_0001.tif")
    assert inputs.restore_names("Cannot read 'upload_0001.tif'.", path, "my scan.tif") == (
        "Cannot read 'my scan.tif'.")
    assert inputs.restore_names("upload_0001.tif: bad", path, r"a\1.tif") == r"a\1.tif: bad"


def test_restore_names_is_a_no_op_for_files_read_from_a_folder(tmp_path):
    path = str(tmp_path / "scan.tif")
    msg = f"Cannot read {path}"
    assert inputs.restore_names(msg, path, "scan.tif") == msg
