"""
fibermorph/gui/app.py — Hair Analysis Streamlit Interface
=========================================================
Five tabs:

  Quick Test          — upload images, run analysis immediately in-process.
                        No SBATCH needed; ideal for testing a few images.

  Segmentation        — review input/mask/overlay for cross-section images
                        processed in Quick Test.

  Batch (Cluster)     — point to existing cluster directories, configure
                        settings, and generate an SBATCH script.

  Submit & Monitor    — submit the SBATCH script and watch job status.

  Results             — load per-image / per-sample CSVs and explore
                        18 publication-ready figures.

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
    "Use **Quick Test** for a few uploaded images, or **Batch** to submit a cluster job."
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for _key, _default in [
    ("job_id",          None),
    ("job_submitted",   False),
    ("sbatch_script",   ""),
    ("output_dir",      ""),
    ("results_loaded",  False),
    ("quick_results",   None),
    ("seg_store",       {}),
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
# In-process helpers for Quick Test tab
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

    gray = cv2.imread(tmp_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None

    seg_result = segment_section(
        gray,
        resolution_mu=resolution_mu,
        min_diam=min_diam,
        max_diam=max_diam,
        use_sam2=use_sam2,
        sam2_checkpoint=sam2_checkpoint,
        sam2_cfg="",
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


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_quick, tab_seg, tab_upload, tab_submit, tab_results = st.tabs(
    ["🧪 Quick Test", "🔍 Segmentation", "📁 Batch (Cluster)", "🚀 Submit & Monitor", "📊 Results"]
)


# ============================================================
# TAB 1 — Quick Test (file upload + in-process run)
# ============================================================
with tab_quick:
    st.header("Quick Test — Upload & Analyse")
    st.info(
        "Upload up to ~20 images directly from your computer. "
        "Analysis runs immediately on this server (no SBATCH). "
        "For large batches use the **Batch (Cluster)** tab."
    )

    col_sec, col_curv = st.columns(2)
    with col_sec:
        st.subheader("Cross-Section Images")
        sec_uploads = st.file_uploader(
            "Upload images (TIFF, PNG, JPG)", type=["tif", "tiff", "png", "jpg", "jpeg"],
            accept_multiple_files=True, key="sec_uploads",
        )
    with col_curv:
        st.subheader("Curvature Images")
        curv_uploads = st.file_uploader(
            "Upload images (TIFF, PNG, JPG)", type=["tif", "tiff", "png", "jpg", "jpeg"],
            accept_multiple_files=True, key="curv_uploads",
        )

    with st.expander("Settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        qt_res_mu = c1.number_input("Section resolution (µm/px)",   value=4.25,  step=0.01, key="qt_res_mu")
        qt_min_d  = c2.number_input("Min diameter (µm)",            value=30.0,  step=1.0,  key="qt_min_d")
        qt_max_d  = c3.number_input("Max diameter (µm)",            value=150.0, step=1.0,  key="qt_max_d")
        qt_res_mm = c1.number_input("Curvature resolution (px/mm)", value=132.0, step=1.0,  key="qt_res_mm")
        qt_window = c2.number_input("Taubin window (px)",           value=50,    step=5,    key="qt_window")
        qt_clahe  = c3.toggle("CLAHE preprocessing (curvature)",    value=False,            key="qt_clahe")
        qt_sam2   = st.toggle("Use SAM2 segmentation (GPU required)", value=False,           key="qt_sam2")
        qt_ckpt   = st.text_input("SAM2 checkpoint path", value=_DEFAULT_CHECKPOINT,         key="qt_ckpt")

    if st.button("▶ Run Analysis", type="primary", key="qt_run"):
        if not sec_uploads and not curv_uploads:
            st.error("Upload at least one image.")
        else:
            from fibermorph.utils.metadata import parse_metadata

            rows      = []
            seg_store = {}
            total     = len(sec_uploads) + len(curv_uploads)
            progress  = st.progress(0, text="Processing…")

            with tempfile.TemporaryDirectory() as tmpdir:
                all_items = (
                    [(f, "section")   for f in sec_uploads] +
                    [(f, "curvature") for f in curv_uploads]
                )
                for idx, (uploaded, img_type) in enumerate(all_items):
                    progress.progress(idx / total, text=f"Processing {uploaded.name}…")
                    tmp_path = os.path.join(tmpdir, uploaded.name)
                    with open(tmp_path, "wb") as fh:
                        fh.write(uploaded.read())
                    try:
                        if img_type == "section":
                            out = _process_section_gui(
                                tmp_path,
                                resolution_mu=float(qt_res_mu),
                                min_diam=float(qt_min_d),
                                max_diam=float(qt_max_d),
                                use_sam2=bool(qt_sam2),
                                sam2_checkpoint=str(qt_ckpt),
                                return_mask=True,
                            )
                            if out is not None:
                                result, gray_img, mask_img = out
                                seg_store[uploaded.name] = (gray_img, mask_img)
                            else:
                                result = None
                        else:
                            result = _process_curvature_gui(
                                tmp_path,
                                resolution_mm=float(qt_res_mm),
                                window_size=int(qt_window),
                                use_clahe=bool(qt_clahe),
                            )
                    except Exception as e:
                        st.warning(f"{uploaded.name}: {e}")
                        result = None

                    if result is not None:
                        meta = parse_metadata(uploaded.name)
                        row  = {"image_type": img_type, "source_file": uploaded.name}
                        row.update(meta)
                        if isinstance(result, dict):
                            row.update(result)
                        rows.append(row)

                progress.progress(1.0, text="Done.")

            if not rows:
                st.error("No images were processed successfully.")
            else:
                df = pd.DataFrame(rows)
                st.session_state["quick_results"] = df
                st.session_state["seg_store"]     = seg_store
                st.success(
                    f"Processed {len(df)} / {total} images. "
                    "Check the **Segmentation** tab to review masks."
                )

    # ---- Display results ----
    if st.session_state["quick_results"] is not None:
        import matplotlib.pyplot as plt
        from fibermorph.gui.visualizations import section_figures, curvature_figures

        df       = st.session_state["quick_results"]
        has_sec  = "image_type" in df.columns and (df["image_type"] == "section").any()
        has_curv = "image_type" in df.columns and (df["image_type"] == "curvature").any()

        st.divider()
        st.metric("Images processed", len(df))

        if has_sec:
            sec_df   = df[df["image_type"] == "section"]
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
            st.markdown("**Cross-Section — Key Measurements**")
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

        if has_curv:
            curv_df   = df[df["image_type"] == "curvature"]
            curv_cols = {
                "source_file":       "File",
                "curv_mean":         "Mean Curv (mm⁻¹)",
                "curv_median":       "Median Curv (mm⁻¹)",
                "curl_index":        "Curl Index",
                "wave_count":        "Wave Count",
                "wave_count_per_mm": "Waves / mm",
                "hair_count":        "Fiber Count",
                "length_total":      "Total Length (mm)",
                "diameter_mean_mu":  "Fiber Diam (µm)",
            }
            present = {k: v for k, v in curv_cols.items() if k in curv_df.columns}
            st.markdown("**Curvature — Key Measurements**")
            st.dataframe(
                curv_df[list(present.keys())].rename(columns=present).style.format(
                    {c: "{:.3f}" for c in list(present.values())[1:]}
                ),
                use_container_width=True,
            )

        if has_sec:
            st.markdown("**Cross-Section Figures**")
            for group, title, fig in section_figures(df):
                with st.expander(title, expanded=False):
                    st.pyplot(fig)
                    plt.close(fig)

        if has_curv:
            st.markdown("**Curvature Figures**")
            for group, title, fig in curvature_figures(df):
                with st.expander(title, expanded=False):
                    st.pyplot(fig)
                    plt.close(fig)

        st.divider()
        st.download_button(
            "📥 Download CSV",
            data=df.to_csv(index=False),
            file_name="quick_test_results.csv",
            mime="text/csv",
        )


# ============================================================
# TAB 2 — Segmentation Preview
# ============================================================
with tab_seg:
    st.header("Segmentation Preview")
    st.caption(
        "Input images side-by-side with the detected hair mask. "
        "Run **Quick Test** first to populate this view."
    )

    seg_store = st.session_state.get("seg_store", {})
    if not seg_store:
        st.info(
            "No segmentation results yet — upload images in the Quick Test tab "
            "and click Run Analysis."
        )
    else:
        import numpy as _np

        st.write(f"Showing {len(seg_store)} cross-section image(s).")

        for fname, (gray, mask) in seg_store.items():
            st.markdown(f"**{fname}**")
            col_img, col_mask, col_overlay = st.columns(3)

            def _to_u8(arr):
                a  = arr.astype(float)
                lo, hi = a.min(), a.max()
                if hi > lo:
                    a = (a - lo) / (hi - lo) * 255
                return a.astype("uint8")

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
            st.divider()


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
        resolution_mu   = col1.number_input("Section resolution (µm/px)", value=4.25,  step=0.01)
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
        per_sample_path = os.path.join(results_dir, "hair_analysis_per_sample.csv")

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
                    per_image_path  = str(candidate)
                    per_sample_path = str(sub / "hair_analysis_per_sample.csv")
                    break

        if not os.path.exists(per_image_path):
            st.warning(f"Per-image CSV not found:\n{per_image_path}")
        else:
            st.session_state["per_image_df"]   = pd.read_csv(per_image_path)
            st.session_state["results_loaded"] = True
            if os.path.exists(per_sample_path):
                st.session_state["per_sample_df"] = pd.read_csv(per_sample_path)
            st.success("Results loaded.")

    if not st.session_state.get("results_loaded"):
        st.stop()

    import matplotlib.pyplot as plt
    from fibermorph.gui.visualizations import section_figures, curvature_figures, sample_figures

    per_image  = st.session_state.get("per_image_df",  pd.DataFrame())
    per_sample = st.session_state.get("per_sample_df", pd.DataFrame())

    has_sec  = "image_type" in per_image.columns and \
               (per_image["image_type"] == "section").any()
    has_curv = "image_type" in per_image.columns and \
               (per_image["image_type"] == "curvature").any()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total images", len(per_image))
    if "sample_id" in per_image.columns:
        m2.metric("Unique samples", per_image["sample_id"].nunique())
    if has_sec:
        m3.metric("Section images", int((per_image["image_type"] == "section").sum()))
    if has_curv:
        m4.metric("Curvature images", int((per_image["image_type"] == "curvature").sum()))

    st.divider()

    if has_sec:
        st.subheader("Cross-Section Shape Analysis")
        _last_group: str | None = None
        for group, title, fig in section_figures(per_image):
            if group != _last_group:
                st.markdown(f"**{group}**")
                _last_group = group
            with st.expander(title, expanded=(group == "Overview")):
                st.pyplot(fig)
                plt.close(fig)

    if has_curv:
        st.divider()
        st.subheader("Curvature Analysis")
        _last_group = None
        for group, title, fig in curvature_figures(per_image):
            if group != _last_group:
                st.markdown(f"**{group}**")
                _last_group = group
            with st.expander(title, expanded=(group == "Distributions")):
                st.pyplot(fig)
                plt.close(fig)

    if not per_sample.empty:
        st.divider()
        st.subheader("Sample-Level Summary")
        for _, title, fig in sample_figures(per_sample):
            with st.expander(title, expanded=True):
                st.pyplot(fig)
                plt.close(fig)

    st.divider()
    with st.expander("Per-Image Data Table", expanded=False):
        st.dataframe(per_image, use_container_width=True)
    if not per_sample.empty:
        with st.expander("Per-Sample Aggregated Table", expanded=False):
            st.dataframe(per_sample, use_container_width=True)

    st.divider()
    dl1, dl2 = st.columns(2)
    if not per_image.empty:
        dl1.download_button(
            "📥 Download per-image CSV",
            data=per_image.to_csv(index=False),
            file_name="hair_analysis_per_image.csv",
            mime="text/csv",
        )
    if not per_sample.empty:
        dl2.download_button(
            "📥 Download per-sample CSV",
            data=per_sample.to_csv(index=False),
            file_name="hair_analysis_per_sample.csv",
            mime="text/csv",
        )
