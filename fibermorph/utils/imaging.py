"""Image utilities — resolution-aware downsampling.

Cross-section scans are often 20 MP / tens of MB, far more pixels than a shape
measurement needs. Downsampling to a target working resolution (and scaling the
resolution together with the pixel count) keeps the µm measurements essentially
unchanged (<0.5% on area/eccentricity in testing) while making processing much
lighter.
"""

from __future__ import annotations

import cv2
import numpy as np

# Target working resolution for cross-section analysis, in PIXELS PER µm. A
# ~100 µm section is ~200 px across at 2.0 px/µm — ample for area/eccentricity/EFD.
TARGET_SECTION_RES_MU = 2.0


# Never shrink an image below this longest-side (px); protects already-small
# images from being over-reduced.
MIN_LONG_SIDE = 400


def downsample_to_resolution(
    gray: np.ndarray,
    resolution_mu: float | None,
    target: float = TARGET_SECTION_RES_MU,
    min_long_side: int = MIN_LONG_SIDE,
) -> tuple[np.ndarray, float | None]:
    """Downsample ``gray`` so its working resolution is ~= ``target`` px/µm.

    Never upsamples, and never shrinks the longest side below ``min_long_side``.
    Returns ``(gray_out, effective_resolution_mu)`` where the effective
    resolution reflects the actual (rounded) resize ratio, so µm measurements
    computed at that resolution match the full-resolution values.

    If ``resolution_mu`` is None, already <= target, or the image is already
    small, it is returned unchanged.
    """
    if resolution_mu is None or resolution_mu <= target:
        return gray, resolution_mu

    factor = resolution_mu / target
    if max(gray.shape[:2]) / factor < min_long_side:
        return gray, resolution_mu

    new_w  = max(1, round(gray.shape[1] / factor))
    new_h  = max(1, round(gray.shape[0] / factor))
    gray_ds = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    effective_res = resolution_mu * (new_w / gray.shape[1])
    return gray_ds, effective_res


# ---------------------------------------------------------------------------
# Memory guard for curvature analysis
# ---------------------------------------------------------------------------
# The ridge filter (step 1 of curvature_seq) dominates peak memory. Measured on
# Great Lakes with the published settings: 4,440 MB for a 20.3 MP image and
# 1,258 MB for a 5.1 MP image, i.e. about 200 MB + 210 MB per megapixel.
CURV_MB_BASE = 200.0
CURV_MB_PER_MP = 210.0

# Memory (MB) kept back from the estimate for everything else the app holds while an
# analysis runs: Streamlit itself, the uploaded files and the result tables. What is
# left is what one curvature analysis may plan to use. A fixed allowance, not a share
# of the free memory, so an image that would finish at full size is not reduced just
# because the machine is busy.
HEADROOM_MB = 300.0

# Below this linear scale (a quarter of the width and height) the fibers are only
# a pixel or two wide and the curvature is no longer meaningful, so an image that
# would need a smaller scale is refused with a message instead of being reduced.
MIN_CURV_SCALE = 0.25


def curvature_peak_memory_mb(height: int, width: int) -> float:
    """Estimated peak memory (MB) of curvature analysis on a height x width image."""
    return CURV_MB_BASE + CURV_MB_PER_MP * (height * width) / 1e6


def _read_int(path: str):
    try:
        with open(path) as fh:
            text = fh.read().strip()
        return None if text in ("max", "") else int(text)
    except (OSError, ValueError):
        return None


def _read_stat(path: str, key: str):
    """One counter from a cgroup ``memory.stat`` file, or None."""
    try:
        with open(path) as fh:
            for line in fh:
                name, _, value = line.partition(" ")
                if name == key:
                    return int(value)
    except (OSError, ValueError):
        pass
    return None


# (mount directories to try, limit file, usage file, file-cache counter in memory.stat)
_CGROUP_V2 = (("", "/unified"), "memory.max", "memory.current", "inactive_file")
_CGROUP_V1 = (("/memory",), "memory.limit_in_bytes", "memory.usage_in_bytes", "total_inactive_file")


def cgroup_headroom_mb(cgroup_text: str, root: str = "/sys/fs/cgroup") -> list:
    """Limit minus usage (MB) for every memory limit that applies to a process.

    ``cgroup_text`` is the content of ``/proc/self/cgroup``. Both layouts are read:
    cgroup v2 (a ``0::path`` line) and v1 (a ``N:memory:path`` line), so hybrid hosts,
    where the v2 line exists but the memory controller is still v1, are covered. Each
    group from the process's own up to the root is checked, since a limit can sit on
    any level (a login-node user slice, a Slurm job, a container). Usage excludes the
    inactive file cache, which the kernel gives back under pressure, so copying files
    does not make the budget shrink.
    """
    out = []
    for line in cgroup_text.splitlines():
        hierarchy, _, rest = line.partition(":")
        controllers, _, path = rest.partition(":")
        if hierarchy == "0" and controllers == "":
            layout = _CGROUP_V2
        elif "memory" in controllers.split(","):
            layout = _CGROUP_V1
        else:
            continue
        mounts, limit_name, used_name, cache_key = layout
        parts = [p for p in path.split("/") if p]
        for mount in mounts:
            for depth in range(len(parts) + 1):
                base = root + mount + "".join("/" + p for p in parts[:depth])
                limit = _read_int(f"{base}/{limit_name}")
                used = _read_int(f"{base}/{used_name}")
                if limit is None or used is None or limit >= 1 << 60:
                    continue    # no limit on this level (v1 reports a huge number)
                used -= _read_stat(f"{base}/memory.stat", cache_key) or 0
                out.append((limit - used) / 1048576.0)
    return out


def available_memory_mb() -> float | None:
    """Memory (MB) this process can still use, or None if it cannot be determined.

    The smallest of: free memory on the machine (``MemAvailable``) and the room left
    under every cgroup limit that applies (:func:`cgroup_headroom_mb`). cgroups are
    what cap login-node sessions, Slurm jobs and containers such as Streamlit Cloud,
    so a machine with plenty of RAM but a small per-user cap is reported correctly.
    Only Linux is detected; elsewhere the result is None and no limit is applied.
    """
    candidates = []
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    candidates.append(int(line.split()[1]) / 1024.0)
                    break
    except (OSError, ValueError, IndexError):
        pass

    try:
        with open("/proc/self/cgroup") as fh:
            candidates.extend(cgroup_headroom_mb(fh.read()))
    except OSError:
        pass

    return max(0.0, min(candidates)) if candidates else None


def memory_budget_mb() -> float | None:
    """Memory (MB) one curvature analysis may plan to use; None means no limit known.

    The memory the process can still use, less ``HEADROOM_MB`` for the rest of the
    app. The environment variable FIBERMORPH_MAX_MEMORY_MB sets the total memory the
    app may use (for example on a host that hides its limit); the same allowance is
    taken off it.
    """
    import os

    total = None
    override = os.environ.get("FIBERMORPH_MAX_MEMORY_MB")
    if override:
        try:
            total = float(override)
        except ValueError:
            pass
    if total is None:
        total = available_memory_mb()
    return None if total is None else max(0.0, total - HEADROOM_MB)


def scaled_window_px(window_px: int, scale: float) -> int:
    """Taubin window (px) to use on an image shrunk by ``scale``.

    A window under 10 px means "fit the whole fragment" and is kept as it is.
    Otherwise the window shrinks with the image but never below 10 px, the shortest
    sliding window the curvature code accepts, so for a short window on a strongly
    reduced image the window covers a longer stretch of fiber than requested.
    """
    if window_px < 10:
        return int(window_px)
    return max(10, round(window_px * scale))


def curvature_scale_for_budget(height: int, width: int, budget_mb: float | None) -> float:
    """Linear scale (<= 1) at which curvature analysis of this image fits the budget.

    1.0 when it already fits, or when no budget is known. A result below
    ``MIN_CURV_SCALE`` means the image cannot be analyzed within the budget.
    """
    if budget_mb is None or curvature_peak_memory_mb(height, width) <= budget_mb:
        return 1.0
    megapixels = max(budget_mb - CURV_MB_BASE, 0.0) / CURV_MB_PER_MP
    scale = (megapixels * 1e6 / (height * width)) ** 0.5
    return min(1.0, scale)


def write_scaled_copy(src_path: str, dst_path: str, scale: float):
    """Save a grayscale copy of ``src_path`` shrunk by ``scale``; return (effective_scale, (w, h)).

    The effective scale is the exact ratio of the new width to the old one, so a
    resolution given in px per unit can be multiplied by it.
    """
    from PIL import Image

    with Image.open(src_path) as im:
        gray = np.array(im.convert("L"))
    h, w = gray.shape
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    small = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    Image.fromarray(small).save(dst_path)
    return new_w / w, (new_w, new_h)
