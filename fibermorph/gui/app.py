"""
fibermorph/gui/app.py — fibermorph Streamlit interface
======================================================
Five tabs:

  Cross-Section       — upload cross-section images, segment and measure them
                        in-process; review input/mask/overlay inline.

  Curvature           — upload curvature images and measure them in-process.

  Batch (Cluster)     — point to existing cluster directories, configure
                        settings, and generate an SBATCH script.

  Submit & Monitor    — submit the SBATCH script and watch job status.

  Results             — load the per-image CSV and explore per-image
                        measurements and simple distributions.

Start via:
  fibermorph-gui
  # or directly:
  python -m streamlit run fibermorph/gui/app.py --server.port 8501
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="fibermorph — Hair Analysis",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 fibermorph — Hair Analysis Pipeline")
st.caption(
    "Cross-section shape analysis (SAM2 / watershed) + curvature analysis. "
    "Use the **Cross-Section** and **Curvature** tabs for a few uploaded images, "
    "or **Batch (Cluster)** to submit a cluster job."
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for _key, _default in [
    ("job_id",          None),
    ("job_submitted",   False),
    ("sbatch_script",   ""),
    ("output_dir",      ""),
    ("results_loaded",    False),
    ("section_results",   None),
    ("curvature_results", None),
    ("seg_store",         {}),
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
) -> dict | None:
    """Run curvature analysis on a single image; returns a dict of measurements."""
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
            extended_curvature=True,
        )
    if df is None:
        return None
    if hasattr(df, "empty") and df.empty:
        return None
    if hasattr(df, "iloc"):
        return df.iloc[0].to_dict()
    return None


def _warn_duplicate_names(uploads):
    """Warn if any uploaded files share a filename (ambiguous source_file)."""
    names = [u.name for u in uploads]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        st.warning(
            "Duplicate filenames uploaded — the `source_file` column will be "
            "ambiguous for these (each file is still measured separately): "
            + ", ".join(dups)
        )


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


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_sec, tab_curv, tab_upload, tab_submit, tab_results = st.tabs(
    ["🔬 Cross-Section", "🌀 Curvature", "📁 Batch (Cluster)", "🚀 Submit & Monitor", "📊 Results"]
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
        "Upload cross-section images to segment and measure them immediately on "
        "this server. For large batches use the **Batch (Cluster)** tab."
    )
    st.caption(_FILENAME_NOTE)

    sec_uploads = st.file_uploader(
        "Upload cross-section images (TIFF, PNG, JPG)", type=_UPLOAD_TYPES,
        accept_multiple_files=True, key="sec_uploads",
    )

    with st.expander("Settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        sec_res_mu = c1.number_input(
            "Resolution (px/µm)", value=4.25, step=0.01, min_value=0.0001, key="sec_res_mu",
            help="Pixels per µm. If your scale is in µm/pixel, enter its reciprocal "
                 "(e.g. 0.18 µm/pixel → 1/0.18 ≈ 5.556).")
        sec_min_d  = c2.number_input("Min diameter (µm)", value=30.0,  step=1.0, key="sec_min_d")
        sec_max_d  = c3.number_input("Max diameter (µm)", value=150.0, step=1.0, key="sec_max_d")
        sec_sam2   = st.toggle("Use SAM2 segmentation (GPU required)", value=False, key="sec_sam2")
        sec_ckpt   = st.text_input("SAM2 checkpoint path", value=_DEFAULT_CHECKPOINT, key="sec_ckpt")

    if st.button("▶ Analyse cross-sections", type="primary", key="sec_run"):
        if not sec_uploads:
            st.error("Upload at least one cross-section image.")
        else:
            _warn_duplicate_names(sec_uploads)
            rows            = []
            seg_store       = []
            failed_sections = []
            progress        = st.progress(0, text="Processing…")

            with tempfile.TemporaryDirectory() as tmpdir:
                for idx, uploaded in enumerate(sec_uploads):
                    progress.progress(idx / len(sec_uploads),
                                      text=f"Processing {uploaded.name}…")
                    tmp_path = os.path.join(tmpdir, uploaded.name)
                    with open(tmp_path, "wb") as fh:
                        fh.write(uploaded.read())
                    try:
                        out = _process_section_gui(
                            tmp_path,
                            resolution_mu=float(sec_res_mu),
                            min_diam=float(sec_min_d),
                            max_diam=float(sec_max_d),
                            use_sam2=bool(sec_sam2),
                            sam2_checkpoint=str(sec_ckpt),
                            return_mask=True,
                        )
                    except Exception as e:
                        st.warning(f"{uploaded.name}: {e}")
                        out = None

                    if out is not None:
                        result, gray_img, mask_img = out
                        seg_store.append((uploaded.name, gray_img, mask_img))
                        row = {"image_type": "section", "source_file": uploaded.name}
                        row.update(result)
                        rows.append(row)
                    else:
                        failed_sections.append(uploaded.name)

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
                st.success(f"Measured {len(rows)} / {len(sec_uploads)} cross-section(s).")

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
        "Upload curvature images to measure them immediately on this server. "
        "For large batches use the **Batch (Cluster)** tab."
    )
    st.caption(_FILENAME_NOTE)

    curv_uploads = st.file_uploader(
        "Upload curvature images (TIFF, PNG, JPG)", type=_UPLOAD_TYPES,
        accept_multiple_files=True, key="curv_uploads",
    )

    with st.expander("Settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        curv_res_mm = c1.number_input("Resolution (px/mm)", value=132.0, step=1.0, min_value=0.01, key="curv_res_mm")
        curv_window = c2.number_input("Taubin window (px)", value=50,    step=5,   key="curv_window")
        curv_clahe  = c3.toggle("CLAHE preprocessing",      value=False,           key="curv_clahe")

    if st.button("▶ Analyse curvature", type="primary", key="curv_run"):
        if not curv_uploads:
            st.error("Upload at least one curvature image.")
        else:
            _warn_duplicate_names(curv_uploads)
            rows     = []
            progress = st.progress(0, text="Processing…")
            with tempfile.TemporaryDirectory() as tmpdir:
                for idx, uploaded in enumerate(curv_uploads):
                    progress.progress(idx / len(curv_uploads),
                                      text=f"Processing {uploaded.name}…")
                    tmp_path = os.path.join(tmpdir, uploaded.name)
                    with open(tmp_path, "wb") as fh:
                        fh.write(uploaded.read())
                    try:
                        result = _process_curvature_gui(
                            tmp_path,
                            resolution_mm=float(curv_res_mm),
                            window_size=int(curv_window),
                            use_clahe=bool(curv_clahe),
                        )
                    except Exception as e:
                        st.warning(f"{uploaded.name}: {e}")
                        result = None
                    if result is not None:
                        row = {"image_type": "curvature", "source_file": uploaded.name}
                        row.update(result)
                        rows.append(row)
                progress.progress(1.0, text="Done.")

            if not rows:
                st.session_state.pop("curvature_results", None)
                st.error("No curvature images were measured.")
            else:
                st.session_state["curvature_results"] = pd.DataFrame(rows)
                st.success(f"Measured {len(rows)} / {len(curv_uploads)} image(s).")

    curv_df = st.session_state.get("curvature_results")
    if curv_df is not None and not curv_df.empty:
        import matplotlib.pyplot as plt

        st.divider()
        st.metric("Curvature images measured", len(curv_df))

        curv_cols = {
            "source_file":       "File",
            "curv_mean_mean":    "Mean Curvature (mm⁻¹)",
            "curv_median_mean":  "Median Curvature (mm⁻¹)",
            "curl_index":        "Curl Index",
            "wave_count":        "Wave Count",
            "wave_count_per_mm": "Waves / mm",
            "hair_count":        "Fiber Count",
            "length_total":      "Total Length (mm)",
            "diameter_mean_mu":  "Fiber Diam (µm)",
        }
        present = {k: v for k, v in curv_cols.items() if k in curv_df.columns}
        st.markdown("**Key Measurements**")
        st.dataframe(
            curv_df[list(present.keys())].rename(columns=present).style.format(
                {c: "{:.3f}" for c in list(present.values())[1:]}
            ),
            use_container_width=True,
        )

        if len(curv_df) >= 2:
            fig = _metric_histograms(
                curv_df,
                [("curv_mean_mean", "Mean Curvature (mm⁻¹)"), ("curl_index", "Curl Index")],
                "Distribution across uploaded images",
            )
            if fig is not None:
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("Upload 2 or more curvature images to see a distribution. "
                    "The per-image measurements are in the table above and the CSV.")

        st.download_button(
            "📥 Download curvature CSV",
            data=curv_df.to_csv(index=False),
            file_name="curvature_results.csv",
            mime="text/csv",
        )


# ============================================================
# TAB 3 — Batch (Cluster)
# ============================================================
with tab_upload:
    st.header("Batch — Cluster Paths & Settings")
    st.caption(
        "Images must already be on the cluster. "
        "This generates an SBATCH script calling the `fibermorph` CLI that you "
        "can review, then submit in the next tab."
    )

    col_sec, col_curv = st.columns(2)
    with col_sec:
        st.subheader("Cross-Section Images")
        section_path = st.text_input(
            "Cluster path to cross-section TIFF directory",
            placeholder="/nfs/turbo/.../section/input/",
            key="section_path",
        )
        st.caption("Leave blank to skip cross-section analysis.")

    with col_curv:
        st.subheader("Curvature Images")
        curv_path = st.text_input(
            "Cluster path to curvature TIFF directory",
            placeholder="/nfs/turbo/.../curvature/input/",
            key="curv_path",
        )
        st.caption("Leave blank to skip curvature analysis.")

    st.divider()
    st.header("Output")
    output_dir_batch = st.text_input(
        "Output directory (cluster path)",
        value=str(Path.home() / "fibermorph_output"),
        key="output_dir_input",
    )

    st.divider()
    st.header("Settings")

    with st.expander("Cross-section settings", expanded=False):
        col1, col2, col3 = st.columns(3)
        resolution_mu   = col1.number_input(
            "Section resolution (px/µm)", value=4.25, step=0.01,
            help="Pixels per µm. If your scale is in µm/pixel, enter its reciprocal "
                 "(e.g. 0.18 µm/pixel → 1/0.18 ≈ 5.556).")
        min_diam        = col2.number_input("Min diameter (µm)",          value=30.0,  step=1.0)
        max_diam        = col3.number_input("Max diameter (µm)",          value=150.0, step=1.0)
        use_sam2        = st.toggle("Enable SAM2 segmentation (requires GPU)", value=False)
        sam2_checkpoint = st.text_input("SAM2 checkpoint path", value=_DEFAULT_CHECKPOINT)
        ext_features    = st.toggle(
            "Extended features (EFD, Hu moments, radial profile, shape class)", value=True
        )

    with st.expander("Curvature settings", expanded=False):
        col4, col5, col6 = st.columns(3)
        resolution_mm = col4.number_input("Curvature resolution (px/mm)", value=132.0, step=1.0)
        window_size   = col5.number_input("Taubin window (px)",           value=50,    step=5)
        use_clahe     = col6.toggle("CLAHE preprocessing", value=False)
        ext_curvature = st.toggle(
            "Extended curvature metrics (curl index, wave count, diameter stats)", value=True
        )

    with st.expander("SLURM settings", expanded=False):
        col7, col8, col9 = st.columns(3)
        slurm_account = col7.text_input("Account",  value="tlasisi0")
        slurm_cpus    = col8.number_input("CPUs",   value=4,   step=1, min_value=1)
        slurm_time    = col9.text_input("Walltime", value="04:00:00")

    st.divider()
    if st.button("▶ Generate SBATCH Script", type="primary"):
        if not section_path and not curv_path:
            st.error("Provide at least one image directory.")
        elif not output_dir_batch:
            st.error("Provide an output directory.")
        else:
            st.session_state["output_dir"] = output_dir_batch
            partition = "spgpu" if use_sam2 else "standard"
            mem_gb    = int(slurm_cpus) * 8

            # Build fibermorph CLI commands
            commands = []
            if section_path:
                sec_flags = [
                    "fibermorph --section",
                    f"    -i '{section_path}'",
                    f"    -o '{output_dir_batch}'",
                    f"    --resolution_mu {resolution_mu}",
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
                    f"    --resolution_mm {int(resolution_mm)}",
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
                f"#SBATCH --account={slurm_account}",
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
            ]
            if use_sam2:
                env_lines += [
                    "# Load CUDA for SAM2 GPU segmentation",
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
            st.success("Script generated — go to the Submit & Monitor tab.")


# ============================================================
# TAB 4 — Submit & Monitor
# ============================================================
with tab_submit:
    st.header("SBATCH Script")

    if not st.session_state["sbatch_script"]:
        st.info("Generate a script in the Batch (Cluster) tab first.")
    else:
        script_text = st.text_area(
            "Review and edit before submitting:",
            value=st.session_state["sbatch_script"],
            height=420,
            key="editable_script",
        )
        st.session_state["sbatch_script"] = script_text

        col_sub, col_dl = st.columns([1, 1])

        with col_sub:
            if st.button("🚀 Submit Job", type="primary",
                         disabled=st.session_state["job_submitted"]):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".sbatch", delete=False
                ) as f:
                    f.write(st.session_state["sbatch_script"])
                    sbatch_file = f.name
                try:
                    result = subprocess.run(
                        ["sbatch", sbatch_file],
                        capture_output=True, text=True, timeout=15,
                    )
                    if result.returncode == 0:
                        match  = re.search(r"(\d+)", result.stdout)
                        job_id = match.group(1) if match else "unknown"
                        st.session_state["job_id"]        = job_id
                        st.session_state["job_submitted"] = True
                        st.success(f"Submitted! Job ID: **{job_id}**")
                    else:
                        st.error(f"sbatch failed:\n{result.stderr}")
                except FileNotFoundError:
                    st.error("`sbatch` not found — run this app on a SLURM login node.")
                except Exception as e:
                    st.error(f"Submission error: {e}")
                finally:
                    try:
                        os.unlink(sbatch_file)
                    except OSError:
                        pass

        with col_dl:
            st.download_button(
                "⬇ Download .sbatch script",
                data=st.session_state["sbatch_script"],
                file_name="run_fibermorph.sbatch",
                mime="text/plain",
            )

        if st.session_state["job_id"]:
            st.divider()
            st.subheader(f"Job {st.session_state['job_id']} — Status")

            col_stat, col_refresh = st.columns([3, 1])
            with col_refresh:
                auto_refresh = st.toggle("Auto-refresh (10s)", value=False)

            try:
                squeue = subprocess.run(
                    ["squeue", "-j", str(st.session_state["job_id"]),
                     "--noheader", "-o", "%T %M %R"],
                    capture_output=True, text=True, timeout=10,
                )
                status_line = squeue.stdout.strip()
            except Exception:
                status_line = ""

            if status_line:
                parts = status_line.split()
                state = parts[0] if parts else "UNKNOWN"
                color = {
                    "RUNNING":   "🟢",
                    "PENDING":   "🟡",
                    "FAILED":    "🔴",
                    "COMPLETED": "✅",
                }.get(state, "⚪")
                col_stat.markdown(f"**Status**: {color} `{status_line}`")
            else:
                col_stat.markdown("**Status**: ✅ Job not in queue (completed or failed)")
                st.session_state["results_loaded"] = False

            log_path = os.path.join(
                st.session_state["output_dir"],
                f"slurm_{st.session_state['job_id']}.out",
            )
            if os.path.exists(log_path):
                with open(log_path) as lf:
                    tail = "".join(lf.readlines()[-40:])
                st.text_area("Log (last 40 lines)", value=tail,
                             height=300, disabled=True)

            if auto_refresh:
                time.sleep(10)
                st.rerun()


# ============================================================
# TAB 5 — Results
# ============================================================
with tab_results:
    st.header("Analysis Results")

    results_dir = st.text_input(
        "Results directory (cluster path):",
        value=st.session_state.get("output_dir", ""),
        key="results_dir_input",
    )

    if st.button("🔄 Load Results"):
        per_image_path  = os.path.join(results_dir, "hair_analysis_per_image.csv")

        # Also search inside timestamped subdirs produced by the batch workflow
        if not os.path.exists(per_image_path) and results_dir and os.path.isdir(results_dir):
            subdirs = sorted(
                [d for d in Path(results_dir).iterdir() if d.is_dir()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for sub in subdirs:
                candidate = sub / "hair_analysis_per_image.csv"
                if candidate.exists():
                    per_image_path = str(candidate)
                    break

        if not os.path.exists(per_image_path):
            st.warning(f"Per-image CSV not found:\n{per_image_path}")
        else:
            st.session_state["per_image_df"]   = pd.read_csv(per_image_path)
            st.session_state["results_loaded"] = True
            st.success("Results loaded.")

    if not st.session_state.get("results_loaded"):
        st.stop()

    import matplotlib.pyplot as plt

    per_image = st.session_state.get("per_image_df", pd.DataFrame())

    has_sec  = "image_type" in per_image.columns and \
               (per_image["image_type"] == "section").any()
    has_curv = "image_type" in per_image.columns and \
               (per_image["image_type"] == "curvature").any()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total images", len(per_image))
    if has_sec:
        m2.metric("Section images", int((per_image["image_type"] == "section").sum()))
    if has_curv:
        m3.metric("Curvature images", int((per_image["image_type"] == "curvature").sum()))

    st.caption("Per-image measurements only. Each row carries its source "
               "filename; do any within/between-individual grouping downstream.")
    st.divider()

    if has_sec:
        sec_df = per_image[per_image["image_type"] == "section"]
        st.subheader("Cross-Section — per-image measurements")
        st.dataframe(sec_df.dropna(axis=1, how="all"), use_container_width=True)
        if len(sec_df) >= 2:
            fig = _metric_histograms(
                sec_df, [("area_mu2", "Area (µm²)"), ("eccentricity", "Eccentricity")],
                "Cross-Section — distribution across images",
            )
            if fig is not None:
                st.pyplot(fig)
                plt.close(fig)

    if has_curv:
        curv_df = per_image[per_image["image_type"] == "curvature"]
        st.divider()
        st.subheader("Curvature — per-image measurements")
        st.dataframe(curv_df.dropna(axis=1, how="all"), use_container_width=True)
        if len(curv_df) >= 2:
            fig = _metric_histograms(
                curv_df, [("curv_mean_mean", "Mean Curvature (mm⁻¹)"), ("curl_index", "Curl Index")],
                "Curvature — distribution across images",
            )
            if fig is not None:
                st.pyplot(fig)
                plt.close(fig)

    st.divider()
    if not per_image.empty:
        st.download_button(
            "📥 Download per-image CSV",
            data=per_image.to_csv(index=False),
            file_name="hair_analysis_per_image.csv",
            mime="text/csv",
        )
