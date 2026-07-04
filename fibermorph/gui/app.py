"""
fibermorph/gui/app.py — fibermorph Streamlit interface
======================================================
Four tabs:

  Cross-Section    — segment and measure cross-section images in-process;
                     per-image results and mask previews appear inline.

  Curvature        — measure curvature images in-process; per-fragment length
                     and curvature (plus per-image summaries) appear inline.

  Run Local        — how to install and launch this same GUI on your own
                     machine (no upload limit; read images straight from a
                     folder on disk). Those extra options appear automatically
                     when launched via `fibermorph-gui`.

  Run Remote       — documentation + an SBATCH script scaffold for running the
                     fibermorph CLI on an HPC cluster. It generates a script to
                     download and submit yourself; it does not submit anything
                     or connect to any cluster.

Start via:
  fibermorph-gui
  # or directly:
  python -m streamlit run fibermorph/gui/app.py --server.port 8501
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from fibermorph.utils.units import resolution_to_px_per_unit

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="fibermorph",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 fibermorph — Fiber Cross-Section & Curvature Analysis")
st.caption(
    "Cross-section shape analysis (SAM2 / watershed) + curvature analysis. "
    "Use **Cross-Section** and **Curvature** to analyse images; **Run Local** to "
    "process large images on your own machine; **Run Remote** for a cluster job."
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for _key, _default in [
    ("sbatch_script",       ""),
    ("section_results",     None),
    ("curvature_fragments", None),
    ("curvature_summary",   None),
    ("seg_store",           {}),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ---------------------------------------------------------------------------
# Resolve default SAM2 checkpoint
# ---------------------------------------------------------------------------
_HERE     = Path(__file__).resolve().parent   # fibermorph/gui/
_PKG_ROOT = _HERE.parent                      # fibermorph/


def _resolve_checkpoint() -> str:
    if os.environ.get("SAM2_CHECKPOINT"):
        return os.environ["SAM2_CHECKPOINT"]
    candidates = [
        _PKG_ROOT / "checkpoints" / "sam2.1_hiera_tiny.pt",
        _PKG_ROOT.parent.parent / "sam2" / "checkpoints" / "sam2.1_hiera_tiny.pt",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(candidates[0])


_DEFAULT_CHECKPOINT = _resolve_checkpoint()


# ---------------------------------------------------------------------------
# In-process helpers for the Cross-Section and Curvature tabs
# ---------------------------------------------------------------------------

def _process_section_gui(
    tmp_path: str,
    resolution_mu: float,
    min_diam: float,
    max_diam: float,
    use_sam2: bool,
    sam2_checkpoint: str,
    return_mask: bool = False,
):
    """Run section analysis on a single image.

    Returns dict of measurements, or (dict, gray_img, mask_uint8) when
    return_mask=True. Returns None if no cross-section was detected.
    """
    import cv2
    from fibermorph.processing.section_sam2 import segment_section
    from fibermorph.core.section import section_props_extended
    from fibermorph.utils.imaging import downsample_to_resolution

    gray = cv2.imread(tmp_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None

    # Large scans carry far more pixels than a shape measurement needs. Downsample
    # to the target working resolution and scale resolution_mu with it — the µm
    # measurements are preserved (<0.5%) while processing is much lighter.
    gray, resolution_mu = downsample_to_resolution(gray, resolution_mu)

    # Note: don't pass model_cfg="" — that empty string would override
    # segment_section's default SAM2 config and make SAM2 silently fail to
    # load (falling back to watershed). Omit it so the default applies.
    seg_result = segment_section(
        gray,
        resolution_mu=resolution_mu,
        min_diam=min_diam,
        max_diam=max_diam,
        use_sam2=use_sam2,
        checkpoint=sam2_checkpoint,
    )
    if seg_result is None:
        return None

    mask_uint8, confidence, method = seg_result

    df = section_props_extended(mask_uint8, os.path.basename(tmp_path), resolution_mu)
    if df is None or df.empty:
        return None

    row = df.iloc[0].to_dict()
    row["confidence"]           = confidence
    row["segmentation_method"]  = method

    if return_mask:
        return row, gray, mask_uint8
    return row


def _process_curvature_gui(
    tmp_path: str,
    resolution_mm: float,
    window_size: int,
    use_clahe: bool = False,
    extended: bool = False,
):
    """Run curvature analysis on a single image.

    Returns a dict {"fragments": DataFrame|None, "image_row": dict} or None.

    The pipeline detects each connected fiber fragment, measures its length and
    curvature, and writes that per-fragment table to analysis/ImageSum_<name>.csv
    (columns curv_mean, curv_median, length — one row per fragment). We read that
    back before the temp dir is removed so the GUI can show per-fragment results,
    not just the per-image aggregate the pipeline returns.
    """
    import glob
    import tempfile as _tmpmod
    from fibermorph.analysis.curvature_pipeline import curvature_seq

    with _tmpmod.TemporaryDirectory() as out_dir:
        df = curvature_seq(
            tmp_path,
            out_dir,
            resolution=resolution_mm,
            window_size=window_size,
            window_unit="px",
            save_img=False,
            test=False,
            within_element=False,
            use_clahe=use_clahe,
            extended_curvature=extended,
        )
        if df is None or (hasattr(df, "empty") and df.empty):
            return None
        image_row = df.iloc[0].to_dict() if hasattr(df, "iloc") else {}

        fragments = None
        matches = glob.glob(os.path.join(out_dir, "**", "ImageSum_*.csv"),
                            recursive=True)
        if matches:
            fdf = pd.read_csv(matches[0])
            keep = [c for c in ("curv_mean", "curv_median", "length")
                    if c in fdf.columns]
            if keep:
                fdf = fdf[keep].dropna(how="all").reset_index(drop=True)
                fdf.insert(0, "fragment", range(1, len(fdf) + 1))
                fragments = fdf

    return {"fragments": fragments, "image_row": image_row}


def _warn_duplicate_names(names):
    """Warn if any inputs share a filename (ambiguous source_file)."""
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        st.warning(
            "Duplicate filenames — the `source_file` column will be ambiguous for "
            "these (each file is still measured separately): " + ", ".join(dups)
        )


# ---------------------------------------------------------------------------
# Local mode: read images straight from a folder on disk (no upload, no size
# cap). Only offered when the app was launched via `fibermorph-gui` on the
# user's own machine — the hosted cloud app stays upload-only.
# ---------------------------------------------------------------------------
_LOCAL = os.environ.get("FIBERMORPH_LOCAL") == "1"


def _list_folder_images(folder):
    """Image files in a local folder matching the accepted upload types."""
    import glob
    if not folder or not os.path.isdir(folder):
        return []
    files = []
    for ext in _UPLOAD_TYPES:
        files += glob.glob(os.path.join(folder, f"*.{ext}"))
        files += glob.glob(os.path.join(folder, f"*.{ext.upper()}"))
    return sorted(set(files))


def _render_input_picker(kind, key_prefix):
    """Render the input control for an analysis tab.

    Returns ("folder", path) or ("upload", uploaded_files). The folder option
    only appears in local mode.
    """
    if _LOCAL:
        mode = st.radio(
            "Input source", ["Upload files", "Folder on disk"],
            horizontal=True, key=f"{key_prefix}_mode",
            help="Running locally — you can read images straight from a folder on "
                 "this computer, with no upload and no file-size limit.",
        )
        if mode == "Folder on disk":
            folder = st.text_input(
                f"Folder containing {kind} images", placeholder="/path/to/images",
                key=f"{key_prefix}_folder",
            )
            if folder:
                n = len(_list_folder_images(folder))
                st.caption(f"{n} image(s) found." if n
                           else "No images found in that folder.")
            return ("folder", folder)
    ups = st.file_uploader(
        f"Upload {kind} images (TIFF, PNG, JPG)", type=_UPLOAD_TYPES,
        accept_multiple_files=True, key=f"{key_prefix}_uploads",
    )
    return ("upload", ups)


def _gather_inputs(source, tmpdir):
    """Turn a picker result into a list of (display_name, filepath).

    Folder mode reads paths directly from disk; upload mode persists each
    uploaded file into tmpdir first.
    """
    mode, payload = source
    if mode == "folder":
        return [(os.path.basename(p), p) for p in _list_folder_images(payload)]
    out = []
    for up in payload or []:
        p = os.path.join(tmpdir, up.name)
        with open(p, "wb") as fh:
            fh.write(up.read())
        out.append((up.name, p))
    return out


def _source_is_empty(source):
    """True when a picker result has no images to process."""
    mode, payload = source
    if mode == "folder":
        return not _list_folder_images(payload)
    return not payload


def _metric_histograms(df, metrics, suptitle):
    """Simple ungrouped histograms of the given (column, label) metrics.

    Returns a matplotlib Figure, or None if no metric has 2+ values. This is a
    per-image sanity view — not a grouped statistical analysis.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    series = []
    for col, label in metrics:
        if col not in df.columns:
            continue
        vals = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(vals) >= 2:
            series.append((label, vals))
    if not series:
        return None
    fig, axes = plt.subplots(1, len(series), figsize=(5 * len(series), 4))
    if len(series) == 1:
        axes = [axes]
    for ax, (label, vals) in zip(axes, series):
        ax.hist(vals, bins="auto", color="#4C72B0", edgecolor="white")
        ax.set_xlabel(label)
        ax.set_ylabel("Count")
    fig.suptitle(suptitle, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig


def _faceted_histograms(df, group_col, metrics, suptitle):
    """One row of histograms per group (e.g. per source image), one column per
    metric — so each sample's distribution is on its own panelled row.

    Returns a matplotlib Figure, or None if nothing is plottable.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    groups = list(dict.fromkeys(df[group_col].tolist()))  # unique, order-preserving
    cols = [(c, label) for c, label in metrics if c in df.columns]
    if not groups or not cols:
        return None

    nrows, ncols = len(groups), len(cols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 2.6 * nrows),
                             squeeze=False)
    for r, g in enumerate(groups):
        sub = df[df[group_col] == g]
        for c, (col, label) in enumerate(cols):
            ax = axes[r][c]
            vals = sub[col].replace([np.inf, -np.inf], np.nan).dropna()
            if len(vals) >= 1:
                ax.hist(vals, bins="auto", color="#4C72B0", edgecolor="white")
            if r == 0:
                ax.set_title(label, fontsize=10)
            if c == 0:
                ax.set_ylabel(str(g), fontsize=9)
            if r == nrows - 1:
                ax.set_xlabel(label)
    fig.suptitle(suptitle, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_sec, tab_curv, tab_local, tab_hpc = st.tabs(
    ["🔬 Cross-Section", "🌀 Curvature", "💻 Run Local", "🖥️ Run Remote"]
)

_FILENAME_NOTE = (
    "Each result row records its **source filename**. The app analyses one image "
    "at a time and does no grouping — name your files however you'll want to group "
    "them (within/between individual) in your own downstream analysis."
)
_UPLOAD_TYPES = ["tif", "tiff", "png", "jpg", "jpeg"]


# ============================================================
# TAB 1 — Cross-Section (file upload + in-process run)
# ============================================================
with tab_sec:
    st.header("Cross-Section Analysis")
    st.info(
        "Segment and measure cross-section images here. For images too large to "
        "upload, run this app locally (see **Run Local**); for a whole study on a "
        "cluster, see **Run Remote**."
    )
    st.caption(_FILENAME_NOTE)

    sec_source = _render_input_picker("cross-section", "sec")

    with st.expander("Settings", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        sec_res_val  = c1.number_input(
            "Resolution", value=4.25, step=0.01, min_value=0.0001, key="sec_res_val",
            help="Enter your microscope scale in whichever unit you have; pick the "
                 "matching unit on the right and it is converted for you.")
        sec_res_unit = c2.selectbox("Unit", ["px/µm", "µm/px"], key="sec_res_unit")
        sec_min_d    = c3.number_input("Min diameter (µm)", value=30.0,  step=1.0, key="sec_min_d")
        sec_max_d    = c4.number_input("Max diameter (µm)", value=150.0, step=1.0, key="sec_max_d")
        sec_res_mu   = resolution_to_px_per_unit(sec_res_val, sec_res_unit)
        st.caption(f"Working resolution: **{sec_res_mu:.4g} px/µm**")
        sec_sam2     = st.toggle("Use SAM2 segmentation (GPU required)", value=False, key="sec_sam2")
        sec_ckpt     = st.text_input("SAM2 checkpoint path", value=_DEFAULT_CHECKPOINT, key="sec_ckpt")

    if st.button("▶ Analyse cross-sections", type="primary", key="sec_run"):
        if _source_is_empty(sec_source):
            st.error("Provide at least one cross-section image.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                sec_inputs = _gather_inputs(sec_source, tmpdir)
                _warn_duplicate_names([n for n, _ in sec_inputs])
                rows            = []
                seg_store       = []
                failed_sections = []
                progress        = st.progress(0, text="Processing…")

                for idx, (name, path) in enumerate(sec_inputs):
                    progress.progress(idx / len(sec_inputs),
                                      text=f"Processing {name}…")
                    try:
                        out = _process_section_gui(
                            path,
                            resolution_mu=float(sec_res_mu),
                            min_diam=float(sec_min_d),
                            max_diam=float(sec_max_d),
                            use_sam2=bool(sec_sam2),
                            sam2_checkpoint=str(sec_ckpt),
                            return_mask=True,
                        )
                    except Exception as e:
                        st.warning(f"{name}: {e}")
                        out = None

                    if out is not None:
                        result, gray_img, mask_img = out
                        seg_store.append((name, gray_img, mask_img))
                        row = {"image_type": "section", "source_file": name}
                        row.update(result)
                        rows.append(row)
                    else:
                        failed_sections.append(name)

                progress.progress(1.0, text="Done.")

                if failed_sections:
                    st.warning(
                        "No cross-section was detected in: "
                        + ", ".join(failed_sections)
                        + ".  If a cross-section is clearly present, the most common cause is the "
                        "**Resolution** — it must be in **pixels per µm** (e.g. enter **5.556** "
                        "for a 0.18 µm/pixel scale), not µm/pixel. Also check the min/max "
                        "diameter range."
                    )

                if not rows:
                    # Clear any prior run's results so stale tables/masks don't linger.
                    st.session_state.pop("section_results", None)
                    st.session_state.pop("seg_store", None)
                    st.error("No cross-sections were measured.")
                else:
                    st.session_state["section_results"] = pd.DataFrame(rows)
                    st.session_state["seg_store"]       = seg_store
                    st.success(f"Measured {len(rows)} / {len(sec_inputs)} cross-section(s).")

    # ---- Cross-section results ----
    sec_df = st.session_state.get("section_results")
    if sec_df is not None and not sec_df.empty:
        import matplotlib.pyplot as plt

        st.divider()
        st.metric("Cross-sections measured", len(sec_df))

        sec_cols = {
            "source_file":         "File",
            "area_mu2":            "Area (µm²)",
            "circularity":         "Circularity",
            "aspect_ratio":        "Aspect Ratio",
            "eccentricity":        "Eccentricity",
            "solidity":            "Solidity",
            "segmentation_method": "Method",
        }
        present = {k: v for k, v in sec_cols.items() if k in sec_df.columns}
        st.markdown("**Key Measurements**")
        st.dataframe(
            sec_df[list(present.keys())].rename(columns=present).style.format({
                "Area (µm²)":   "{:.0f}",
                "Circularity":  "{:.3f}",
                "Aspect Ratio": "{:.2f}",
                "Eccentricity": "{:.3f}",
                "Solidity":     "{:.3f}",
            }),
            use_container_width=True,
        )

        if len(sec_df) >= 2:
            fig = _metric_histograms(
                sec_df,
                [("area_mu2", "Area (µm²)"), ("eccentricity", "Eccentricity")],
                "Distribution across uploaded images",
            )
            if fig is not None:
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("Upload 2 or more cross-section images to see a distribution. "
                    "The per-image measurements are in the table above and the CSV.")

        st.download_button(
            "📥 Download cross-section CSV",
            data=sec_df.to_csv(index=False),
            file_name="section_results.csv",
            mime="text/csv",
        )

        # Segmentation mask preview for this run
        seg_store = st.session_state.get("seg_store", {})
        if seg_store:
            with st.expander(f"Segmentation masks ({len(seg_store)})", expanded=False):
                import numpy as _np

                def _to_u8(arr):
                    a = arr.astype(float)
                    lo, hi = a.min(), a.max()
                    if hi > lo:
                        a = (a - lo) / (hi - lo) * 255
                    return a.astype("uint8")

                for fname, gray, mask in seg_store:
                    st.markdown(f"**{fname}**")
                    col_img, col_mask, col_overlay = st.columns(3)
                    gray_u8 = _to_u8(gray)
                    mask_u8 = (mask > 0).astype("uint8") * 255
                    rgb      = _np.stack([gray_u8, gray_u8, gray_u8], axis=-1)
                    green_ch = rgb[:, :, 1].copy()
                    green_ch[mask_u8 > 0] = _np.clip(
                        green_ch[mask_u8 > 0].astype(int) + 80, 0, 255
                    ).astype("uint8")
                    rgb[:, :, 1] = green_ch
                    col_img.image(gray_u8,  caption="Input",   use_container_width=True, clamp=True)
                    col_mask.image(mask_u8, caption="Mask",    use_container_width=True, clamp=True)
                    col_overlay.image(rgb,  caption="Overlay", use_container_width=True, clamp=True)


# ============================================================
# TAB 2 — Curvature
# ============================================================
with tab_curv:
    st.header("Curvature Analysis")
    st.info(
        "Measure curvature images here. For images too large to upload, run this "
        "app locally (see **Run Local**); for a whole study on a cluster, see "
        "**Run Remote**."
    )
    st.caption(_FILENAME_NOTE)

    curv_source = _render_input_picker("curvature", "curv")

    with st.expander("Settings", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        curv_res_val  = c1.number_input(
            "Resolution", value=132.0, step=1.0, min_value=0.0001, key="curv_res_val",
            help="Enter your scale in whichever unit you have; pick the matching "
                 "unit on the right and it is converted for you.")
        curv_res_unit = c2.selectbox("Unit", ["px/mm", "mm/px"], key="curv_res_unit")
        curv_window   = c3.number_input(
            "Taubin window (px)", value=50, step=5, key="curv_window",
            help="Length (in pixels) of the sliding window used to fit a circle "
                 "to the fiber (Taubin method) and measure local curvature at each "
                 "step along it. Larger = smoother, more global curvature; smaller "
                 "= more local detail. Keep it well below your fragment length.")
        curv_clahe    = c4.toggle(
            "CLAHE preprocessing", value=False, key="curv_clahe",
            help="Contrast-Limited Adaptive Histogram Equalization: boosts local "
                 "contrast before fibers are detected. Helps when illumination is "
                 "uneven across the image; may add noise on already-clean images.")
        curv_res_mm   = resolution_to_px_per_unit(curv_res_val, curv_res_unit)
        st.caption(f"Working resolution: **{curv_res_mm:.4g} px/mm**")
        curv_ext = st.toggle(
            "Show extended (experimental) metrics", value=False, key="curv_ext",
            help="Curl index and wave count. These were added in the v2 student "
                 "fork and are NOT part of the published fibermorph curvature "
                 "method — treat them as experimental.")

    if st.button("▶ Analyse curvature", type="primary", key="curv_run"):
        if _source_is_empty(curv_source):
            st.error("Provide at least one curvature image.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                curv_inputs = _gather_inputs(curv_source, tmpdir)
                _warn_duplicate_names([n for n, _ in curv_inputs])
                frag_frames = []
                summ_rows   = []
                failed      = []
                progress = st.progress(0, text="Processing…")
                for idx, (name, path) in enumerate(curv_inputs):
                    progress.progress(idx / len(curv_inputs),
                                      text=f"Processing {name}…")
                    try:
                        result = _process_curvature_gui(
                            path,
                            resolution_mm=float(curv_res_mm),
                            window_size=int(curv_window),
                            use_clahe=bool(curv_clahe),
                            extended=bool(curv_ext),
                        )
                    except Exception as e:
                        st.warning(f"{name}: {e}")
                        result = None

                    frags = result.get("fragments") if result else None
                    if frags is not None and not frags.empty:
                        f = frags.copy()
                        f.insert(0, "source_file", name)
                        frag_frames.append(f)
                        summ = {
                            "source_file":   name,
                            "n_fragments":   int(len(frags)),
                            "curv_mean":     float(frags["curv_mean"].mean()),
                            "curv_median":   float(frags["curv_mean"].median()),
                            "length_mean":   float(frags["length"].mean()),
                            "length_median": float(frags["length"].median()),
                            "length_total":  float(frags["length"].sum()),
                        }
                        if curv_ext:
                            ir = (result or {}).get("image_row", {}) or {}
                            for k in ("curl_index", "wave_count",
                                      "wave_count_per_mm"):
                                if k in ir:
                                    summ[k] = ir[k]
                        summ_rows.append(summ)
                    else:
                        failed.append(name)
                progress.progress(1.0, text="Done.")

            if failed:
                st.warning(
                    "No fiber fragments were measured in: " + ", ".join(failed)
                    + ". Check the **Resolution** (px/mm) and that the fibers are "
                    "visible against the background."
                )
            if not frag_frames:
                st.session_state.pop("curvature_fragments", None)
                st.session_state.pop("curvature_summary", None)
                st.error("No curvature fragments were measured.")
            else:
                st.session_state["curvature_fragments"] = pd.concat(
                    frag_frames, ignore_index=True)
                st.session_state["curvature_summary"] = pd.DataFrame(summ_rows)
                n_frag = int(sum(len(f) for f in frag_frames))
                st.success(f"Measured {n_frag} fragment(s) across "
                           f"{len(summ_rows)} / {len(curv_inputs)} image(s).")

    frag_df = st.session_state.get("curvature_fragments")
    summ_df = st.session_state.get("curvature_summary")
    if frag_df is not None and not frag_df.empty:
        import matplotlib.pyplot as plt

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Fragments measured", len(frag_df))
        m2.metric("Images", frag_df["source_file"].nunique())

        # --- Per-fragment table (primary output) ---
        st.markdown("**Per-fragment measurements** — one row per fiber fragment")
        frag_cols = {
            "source_file": "File",
            "fragment":    "Fragment",
            "length":      "Length (mm)",
            "curv_mean":   "Mean Curvature (mm⁻¹)",
            "curv_median": "Median Curvature (mm⁻¹)",
        }
        fpresent = {k: v for k, v in frag_cols.items() if k in frag_df.columns}
        st.dataframe(
            frag_df[list(fpresent.keys())].rename(columns=fpresent).style.format({
                "Length (mm)":             "{:.3f}",
                "Mean Curvature (mm⁻¹)":   "{:.4f}",
                "Median Curvature (mm⁻¹)": "{:.4f}",
            }),
            use_container_width=True,
        )
        st.download_button(
            "📥 Download per-fragment CSV",
            data=frag_df.to_csv(index=False),
            file_name="curvature_per_fragment.csv",
            mime="text/csv",
        )

        # --- Per-image summary (aggregated across fragments) ---
        if summ_df is not None and not summ_df.empty:
            st.markdown("**Per-image summary** — aggregated across each image's fragments")
            summ_labels = {
                "source_file":       "File",
                "n_fragments":       "Fragments",
                "curv_mean":         "Mean Curvature (mm⁻¹)",
                "curv_median":       "Median Curvature (mm⁻¹)",
                "length_mean":       "Mean Length (mm)",
                "length_median":     "Median Length (mm)",
                "length_total":      "Total Length (mm)",
                "curl_index":        "Curl Index (v2)",
                "wave_count":        "Wave Count (v2)",
                "wave_count_per_mm": "Waves/mm (v2)",
            }
            spresent = {k: v for k, v in summ_labels.items() if k in summ_df.columns}
            fmt = {v: "{:.4f}" for k, v in spresent.items()
                   if k not in ("source_file", "n_fragments", "wave_count")}
            st.dataframe(
                summ_df[list(spresent.keys())].rename(columns=spresent).style.format(fmt),
                use_container_width=True,
            )
            st.download_button(
                "📥 Download per-image summary CSV",
                data=summ_df.to_csv(index=False),
                file_name="curvature_per_image.csv",
                mime="text/csv",
            )

        # --- Distributions of fragment length + mean curvature ---
        hist_metrics = [("length", "Fragment Length (mm)"),
                        ("curv_mean", "Fragment Mean Curvature (mm⁻¹)")]

        # Per-sample: one panelled row per uploaded image (only when >1 sample).
        if frag_df["source_file"].nunique() >= 2:
            fig_by = _faceted_histograms(
                frag_df, "source_file", hist_metrics, "Per-sample distributions",
            )
            if fig_by is not None:
                st.pyplot(fig_by)
                plt.close(fig_by)

        # Joint: all fragments from all samples pooled together.
        if len(frag_df) >= 2:
            fig = _metric_histograms(
                frag_df, hist_metrics,
                "Joint distribution — all samples pooled",
            )
            if fig is not None:
                st.pyplot(fig)
                plt.close(fig)


# ============================================================
# TAB 3 — Run Local (same GUI, on your own machine)
# ============================================================
with tab_local:
    st.header("Run Local — the same GUI on your own computer")
    st.markdown(
        "**Why:** this hosted app runs on a shared server, so it can't reach files "
        "on your computer and it caps uploads (500 MB here). Large scans — like a "
        "2 GB curvature image — won't upload.\n\n"
        "**Fix:** fibermorph is an ordinary Python package, and this whole interface "
        "ships with it. Install it once and launch the *same* app on your own "
        "machine — Streamlit runs perfectly well locally — where there's no upload "
        "limit and you can point it straight at a folder of images:\n\n"
        "```bash\n"
        "pip install 'fibermorph[gui]'\n"
        "fibermorph-gui\n"
        "```\n\n"
        "That opens the identical interface in your browser at "
        "`http://localhost:8501`, but running on your computer. On the "
        "**Cross-Section** and **Curvature** tabs you then get an extra "
        "**“Folder on disk”** option — choose it, paste the path to your images, and "
        "they are read directly from disk (no upload, any size)."
    )
    if _LOCAL:
        st.success(
            "✅ You're running locally right now — the **Folder on disk** option is "
            "available on the Cross-Section and Curvature tabs, and uploads are "
            "raised to 5 GB."
        )
    else:
        st.info(
            "You're on the hosted app (upload-only, 500 MB). Follow the steps above "
            "to run locally for large images."
        )
    st.caption(
        "No GPU or cluster needed — this runs on an ordinary laptop or desktop. For "
        "a whole study on a shared HPC cluster, see the **Run Remote** tab."
    )


# ============================================================
# TAB 4 — Run Remote (HPC)
# ============================================================
with tab_hpc:
    st.header("Run Remote on your own cluster")
    st.markdown(
        "The tabs above analyse a few uploaded images right here in the browser. "
        "For a whole study — or images too large to upload — run the **fibermorph "
        "command-line tool** where your images already live (your workstation or an "
        "HPC cluster):\n\n"
        "```bash\n"
        "pip install fibermorph\n"
        "fibermorph --section -i /path/to/images -o /path/to/output --resolution_mu 5.556\n"
        "```\n\n"
        "This tab builds a matching **SBATCH script** you can download, edit, and "
        "submit yourself with `sbatch`. It does **not** submit anything or connect to "
        "any cluster — nothing here leaves your browser."
    )

    st.divider()
    st.subheader("1 · Inputs")
    col_sec, col_curv = st.columns(2)
    with col_sec:
        section_path = st.text_input(
            "Cross-section image directory (on the machine you'll run on)",
            placeholder="/path/to/section/input/",
            key="section_path",
        )
        st.caption("Leave blank to skip cross-section analysis.")

    with col_curv:
        curv_path = st.text_input(
            "Curvature image directory (on the machine you'll run on)",
            placeholder="/path/to/curvature/input/",
            key="curv_path",
        )
        st.caption("Leave blank to skip curvature analysis.")

    output_dir_batch = st.text_input(
        "Output directory",
        value="fibermorph_output",
        key="output_dir_input",
        help="Where fibermorph writes its CSVs. Relative to where you submit the "
             "job, or an absolute path on your cluster.",
    )

    st.divider()
    st.subheader("2 · Settings")

    with st.expander("Cross-section settings", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        sec_res_val_b  = col1.number_input(
            "Section resolution", value=4.25, step=0.01, min_value=0.0001,
            key="batch_sec_res_val")
        sec_res_unit_b = col2.selectbox("Unit", ["px/µm", "µm/px"], key="batch_sec_res_unit")
        min_diam       = col3.number_input("Min diameter (µm)", value=30.0,  step=1.0)
        max_diam       = col4.number_input("Max diameter (µm)", value=150.0, step=1.0)
        resolution_mu  = resolution_to_px_per_unit(sec_res_val_b, sec_res_unit_b)
        st.caption(f"Script will pass **--resolution_mu {resolution_mu:.4g}** (px/µm).")
        use_sam2        = st.toggle("Enable SAM2 segmentation (requires GPU)", value=False)
        sam2_checkpoint = st.text_input("SAM2 checkpoint path", value=_DEFAULT_CHECKPOINT)
        ext_features    = st.toggle(
            "Extended features (EFD, Hu moments, radial profile, shape class)", value=True
        )

    with st.expander("Curvature settings", expanded=False):
        col5, col6, col7, col8 = st.columns(4)
        curv_res_val_b  = col5.number_input(
            "Curvature resolution", value=132.0, step=1.0, min_value=0.0001,
            key="batch_curv_res_val")
        curv_res_unit_b = col6.selectbox("Unit", ["px/mm", "mm/px"], key="batch_curv_res_unit")
        window_size     = col7.number_input(
            "Taubin window (px)", value=50, step=5,
            help="Length (in pixels) of the sliding window used to fit a circle "
                 "to the fiber (Taubin method) and measure local curvature. Larger "
                 "= smoother/more global; smaller = more local detail. Keep it well "
                 "below your fragment length.")
        use_clahe       = col8.toggle(
            "CLAHE preprocessing", value=False,
            help="Contrast-Limited Adaptive Histogram Equalization: boosts local "
                 "contrast before fibers are detected. Helps with uneven "
                 "illumination; may add noise on already-clean images.")
        resolution_mm   = resolution_to_px_per_unit(curv_res_val_b, curv_res_unit_b)
        st.caption(f"Script will pass **--resolution_mm {resolution_mm:.4g}** (px/mm).")
        ext_curvature = st.toggle(
            "Extended curvature metrics (curl index, wave count)", value=True
        )

    with st.expander("SLURM settings", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        slurm_account       = col_a.text_input("Account", value="", placeholder="YOUR_ACCOUNT")
        slurm_cpus          = col_b.number_input("CPUs", value=4, step=1, min_value=1)
        slurm_time          = col_c.text_input("Walltime", value="04:00:00")
        col_d, col_e        = st.columns(2)
        slurm_partition     = col_d.text_input("Partition (CPU)", value="", placeholder="e.g. standard")
        slurm_gpu_partition = col_e.text_input("Partition (GPU, for SAM2)", value="", placeholder="e.g. gpu")
        st.caption(
            "Account and partition names are specific to your cluster — check its "
            "docs. Left blank, the script uses YOUR_ACCOUNT / YOUR_PARTITION "
            "placeholders for you to fill in."
        )

    st.divider()
    st.subheader("3 · Generate script")
    if st.button("▶ Generate SBATCH script", type="primary"):
        if not section_path and not curv_path:
            st.error("Provide at least one image directory.")
        elif not output_dir_batch:
            st.error("Provide an output directory.")
        else:
            account = slurm_account.strip() or "YOUR_ACCOUNT"
            if use_sam2:
                partition = slurm_gpu_partition.strip() or "YOUR_GPU_PARTITION"
            else:
                partition = slurm_partition.strip() or "YOUR_PARTITION"
            mem_gb = int(slurm_cpus) * 8

            # Build fibermorph CLI commands
            commands = []
            if section_path:
                sec_flags = [
                    "fibermorph --section",
                    f"    -i '{section_path}'",
                    f"    -o '{output_dir_batch}'",
                    f"    --resolution_mu {resolution_mu:g}",
                    f"    --minsize {int(min_diam)}",
                    f"    --maxsize {int(max_diam)}",
                    f"    --jobs {int(slurm_cpus)}",
                ]
                if use_sam2:
                    sec_flags += [
                        "    --use-sam2",
                        f"    --sam2-checkpoint '{sam2_checkpoint}'",
                    ]
                if ext_features:
                    sec_flags.append("    --extended-features")
                commands.append(" \\\n".join(sec_flags))

            if curv_path:
                curv_flags = [
                    "fibermorph --curvature",
                    f"    -i '{curv_path}'",
                    f"    -o '{output_dir_batch}'",
                    f"    --resolution_mm {resolution_mm:g}",
                    f"    --window_size {int(window_size)}",
                    f"    --jobs {int(slurm_cpus)}",
                ]
                if use_clahe:
                    curv_flags.append("    --use-clahe")
                if ext_curvature:
                    curv_flags.append("    --extended-curvature")
                commands.append(" \\\n".join(curv_flags))

            directives = [
                "#!/bin/bash",
                "#SBATCH --job-name=fibermorph",
                f"#SBATCH --account={account}",
                f"#SBATCH --partition={partition}",
            ]
            if use_sam2:
                directives.append("#SBATCH --gpus=1")
            directives += [
                "#SBATCH --nodes=1",
                "#SBATCH --ntasks=1",
                f"#SBATCH --cpus-per-task={int(slurm_cpus)}",
                f"#SBATCH --mem={mem_gb}G",
                f"#SBATCH --time={slurm_time}",
                f"#SBATCH --output={output_dir_batch}/slurm_%j.out",
                f"#SBATCH --error={output_dir_batch}/slurm_%j.err",
            ]

            env_lines = [
                "",
                "set -euo pipefail",
                f'mkdir -p "{output_dir_batch}"',
                "",
                "# Activate the environment where you installed fibermorph, e.g.:",
                "# module load python            # adjust for your cluster",
                "# source ~/fibermorph-venv/bin/activate",
                "",
            ]
            if use_sam2:
                env_lines += [
                    "# Load CUDA for SAM2 GPU segmentation (adjust module name for your cluster)",
                    "module load cuda",
                    "",
                    'echo "GPU(s): $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo none)"',
                    "",
                ]
            env_lines += [
                'echo "Host: $(hostname)"',
                'echo "Start: $(date)"',
                "",
            ]
            for cmd in commands:
                env_lines.append(cmd)
                env_lines.append("")
            env_lines += [
                'echo "Done: $(date)"',
                "",
            ]

            script = "\n".join(directives) + "\n" + "\n".join(env_lines)
            st.session_state["sbatch_script"] = script

    if st.session_state["sbatch_script"]:
        st.download_button(
            "⬇ Download run_fibermorph.sbatch",
            data=st.session_state["sbatch_script"],
            file_name="run_fibermorph.sbatch",
            mime="text/plain",
        )
        st.code(st.session_state["sbatch_script"], language="bash")
        st.caption(
            "Edit the placeholders, copy this to your cluster, and run "
            "`sbatch run_fibermorph.sbatch`. fibermorph writes a timestamped "
            "subfolder per module under your output directory, each with a summary "
            "CSV (`summary_section_data.csv` / `curvature_summary_data*.csv`) — one "
            "row per image, carrying its source filename for downstream grouping."
        )

