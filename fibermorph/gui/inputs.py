"""Safe handling of files uploaded through the Streamlit app.

The filename an uploader sends is chosen by the client and must never be used
to build a path on the server: it can be absolute, contain ``..`` or Windows
separators, or collide with another upload's name. Uploads are therefore
written under names generated here (``upload_0001.tif``, ``upload_0002.png``,
...), and the client's name is kept only as a display label, reduced to its
last path component.

This module has no Streamlit dependency so it can be unit-tested directly.
"""

from __future__ import annotations

import os
import re

# File types the upload widgets accept (lower case, no dot).
UPLOAD_TYPES = ["tif", "tiff", "png", "jpg", "jpeg"]

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def display_name(client_name, fallback: str = "upload") -> str:
    """Reduce a client-supplied filename to a safe label for display.

    Keeps only the last path component (splitting on both ``/`` and ``\\``, so
    Windows-style and POSIX-style paths are handled the same way on any
    platform) and drops control characters. Returns ``fallback`` when nothing
    usable is left (empty name, ``.``, ``..``, a bare separator).
    """
    name = _CONTROL_CHARS.sub("", str(client_name or ""))
    name = re.split(r"[\\/]", name)[-1].strip()
    if name in ("", ".", ".."):
        return fallback
    return name


def safe_extension(client_name) -> str:
    """Return the lower-case extension (with dot) of ``client_name`` if it is
    one of ``UPLOAD_TYPES``, else an empty string."""
    ext = os.path.splitext(display_name(client_name, fallback=""))[1].lower()
    return ext if ext.lstrip(".") in UPLOAD_TYPES else ""


def save_uploads(uploads, tmpdir):
    """Write uploaded files into ``tmpdir`` and return ``(display_name, path)``.

    Each upload is saved as ``upload_NNNN<ext>`` (1-based, in upload order),
    where ``<ext>`` is the original extension only if it is an accepted type.
    The client-supplied name is used for nothing but the returned display
    label, so every file lands directly inside ``tmpdir`` and two uploads with
    the same name are stored (and later measured) as two separate files.

    ``uploads`` is any iterable of objects with a ``name`` attribute and a
    ``read()`` method returning bytes (e.g. Streamlit ``UploadedFile``), or
    ``None``.
    """
    out = []
    for i, up in enumerate(uploads or [], start=1):
        saved_name = f"upload_{i:04d}{safe_extension(up.name)}"
        path = os.path.join(tmpdir, saved_name)
        with open(path, "wb") as fh:
            fh.write(up.read())
        out.append((display_name(up.name, fallback=saved_name), path))
    return out


def restore_names(text, path, name) -> str:
    """Replace the saved file's path and generated name in ``text`` (typically
    an error message from the image reader) with the name the user knows it by.

    Only whole names are replaced: ``upload_0001`` (a file saved without an
    extension) does not match inside ``upload_00010.tif``.

    Leaves ``text`` unchanged when ``path`` already ends in ``name`` (e.g. a
    file read straight from a folder on disk).
    """
    text = str(text)
    saved_name = os.path.basename(path)
    if saved_name == name:
        return text
    return _replace_whole(_replace_whole(text, path, name), saved_name, name)


def _replace_whole(text, old, new) -> str:
    """Replace ``old`` with ``new`` where ``old`` is not part of a longer word."""
    return re.sub(rf"(?<!\w){re.escape(old)}(?!\w)", lambda _m: new, text)
