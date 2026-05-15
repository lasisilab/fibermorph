"""Figure functions for hair cross-section and curvature analysis results.

Each function accepts a pandas DataFrame and returns a matplotlib Figure.
No side effects — no plt.show(), no file I/O.

Usage in Streamlit:
    from fibermorph.gui.visualizations import section_figures, curvature_figures
    for group, title, fig in section_figures(per_image_df):
        st.pyplot(fig)
        plt.close(fig)
"""

import warnings
from typing import Generator

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

REGION_PALETTE = {"A": "#4C72B0", "B": "#C44E52"}

sns.set_theme(style="whitegrid", font_scale=1.05)
plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

_FLIER = {"marker": ".", "markersize": 3, "alpha": 0.4}


def _has(df: pd.DataFrame, *cols: str) -> bool:
    return all(c in df.columns for c in cols)


def _empty(msg: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.text(0.5, 0.5, f"[!]  {msg}", ha="center", va="center",
            fontsize=11, color="gray", transform=ax.transAxes)
    ax.axis("off")
    fig.tight_layout()
    return fig


# ===========================================================================
# SECTION FIGURES
# ===========================================================================

def fig_geometric_boxplots(df: pd.DataFrame) -> plt.Figure:
    metrics = [
        ("circularity",    "Circularity (4πA/P²)"),
        ("aspect_ratio",   "Aspect Ratio"),
        ("eccentricity",   "Eccentricity"),
        ("solidity",       "Solidity"),
        ("area_mu2",       "Area (µm²)"),
        ("convexity",      "Convexity"),
        ("radial_cv",      "Radial Profile CV"),
        ("asymmetry_index","Asymmetry Index"),
    ]
    metrics = [(c, l) for c, l in metrics if c in df.columns]
    if not metrics:
        return _empty("No geometric feature columns found")

    n = len(metrics)
    ncols = 4
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(20, 4.5 * nrows))
    fig.suptitle("Geometric Features by Region", fontsize=13, fontweight="bold")

    if "region" in df.columns:
        regions = sorted(df["region"].dropna().unique())
        palette = {r: REGION_PALETTE.get(r, "#888888") for r in regions}
        for ax, (col, label) in zip(axes.flat, metrics):
            sns.boxplot(data=df, x="region", y=col, order=regions,
                        palette=palette, ax=ax, linewidth=0.9, flierprops=_FLIER)
            ax.set_title(label, fontsize=10)
            ax.set_xlabel("")
            ax.set_ylabel("")
    else:
        for ax, (col, label) in zip(axes.flat, metrics):
            ax.boxplot(df[col].dropna(), flierprops=_FLIER)
            ax.set_title(label, fontsize=10)
            ax.set_xlabel("")
            ax.set_ylabel("")

    for ax in axes.flat[len(metrics):]:
        ax.set_visible(False)

    fig.tight_layout()
    return fig


def fig_size_distributions(df: pd.DataFrame) -> plt.Figure:
    pairs = [
        ("area_mu2",      "Cross-Sectional Area (µm²)"),
        ("radial_mean_mu","Mean Radius (µm)"),
        ("radial_min_mu", "Min Radius (µm)"),
        ("radial_max_mu", "Max Radius (µm)"),
    ]
    pairs = [(c, l) for c, l in pairs if c in df.columns]
    if not pairs:
        return _empty("No size-related columns found")

    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4.5))
    if len(pairs) == 1:
        axes = [axes]
    fig.suptitle("Size Distributions by Region", fontsize=13, fontweight="bold")

    if "region" in df.columns:
        regions = sorted(df["region"].dropna().unique())
        palette = {r: REGION_PALETTE.get(r, "#888888") for r in regions}
        for ax, (col, label) in zip(axes, pairs):
            for reg in regions:
                vals = df[df["region"] == reg][col].dropna()
                if len(vals) < 5:
                    continue
                sns.kdeplot(vals, ax=ax, color=palette[reg],
                            label=f"Region {reg}", linewidth=1.8,
                            fill=True, alpha=0.12)
            ax.set_xlabel(label, fontsize=10)
            ax.set_ylabel("Density")
        handles = [mpatches.Patch(color=REGION_PALETTE.get(r, "#888888"),
                                  label=f"Region {r}") for r in regions]
        axes[-1].legend(handles=handles, title="Region", fontsize=9)
    else:
        for ax, (col, label) in zip(axes, pairs):
            vals = df[col].dropna()
            if len(vals) >= 5:
                sns.kdeplot(vals, ax=ax, color="#4C72B0",
                            linewidth=1.8, fill=True, alpha=0.2)
            ax.set_xlabel(label, fontsize=10)
            ax.set_ylabel("Density")

    fig.tight_layout()
    return fig


def fig_efd_power_spectrum(df: pd.DataFrame) -> plt.Figure:
    efd_cols = [f"efd_power_h{i}" for i in range(1, 11)]
    efd_cols = [c for c in efd_cols if c in df.columns]
    if not efd_cols:
        return _empty("No EFD power columns found")

    harmonics = [int(c.split("h")[1]) for c in efd_cols]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Elliptic Fourier Descriptor Harmonic Power Spectrum",
                 fontsize=13, fontweight="bold")

    if "region" in df.columns:
        regions = sorted(df["region"].dropna().unique())
        palette = {r: REGION_PALETTE.get(r, "#888888") for r in regions}
        for ax, start, title in [
            (axes[0], 0, "All Harmonics (h1 = ellipse fit)"),
            (axes[1], 1, "Shape Complexity — h2–h10"),
        ]:
            hs = harmonics[start:]
            for reg in regions:
                vals = df[df["region"] == reg][efd_cols[start:]].mean().values
                ax.plot(hs, vals, marker="o", markersize=5,
                        color=palette[reg], label=f"Region {reg}", linewidth=1.8)
            ax.set_yscale("log")
            ax.set_xlabel("Harmonic Number")
            ax.set_ylabel("Mean Power (log scale)")
            ax.set_title(title)
            ax.set_xticks(hs)
            ax.legend(title="Region", fontsize=9)
    else:
        for ax, start, title in [
            (axes[0], 0, "All Harmonics (h1 = ellipse fit)"),
            (axes[1], 1, "Shape Complexity — h2–h10"),
        ]:
            hs   = harmonics[start:]
            vals = df[efd_cols[start:]].mean().values
            ax.plot(hs, vals, marker="o", markersize=5,
                    color="#4C72B0", linewidth=1.8)
            ax.set_yscale("log")
            ax.set_xlabel("Harmonic Number")
            ax.set_ylabel("Mean Power (log scale)")
            ax.set_title(title)
            ax.set_xticks(hs)

    fig.tight_layout()
    return fig


def fig_radial_features(df: pd.DataFrame) -> plt.Figure:
    metrics = [
        ("efd_deviation",  "EFD Deviation\n(shape complexity)"),
        ("radial_cv",      "Radial Profile CV\n(boundary irregularity)"),
        ("n_radial_peaks", "Radial Peak Count\n(number of lobes)"),
        ("asymmetry_index","Asymmetry Index\n(tear-drop detector)"),
    ]
    metrics = [(c, l) for c, l in metrics if c in df.columns]
    if not metrics:
        return _empty("No radial feature columns found")

    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))
    if len(metrics) == 1:
        axes = [axes]
    fig.suptitle("Shape Complexity & Boundary Features", fontsize=13, fontweight="bold")

    if "region" in df.columns:
        regions = sorted(df["region"].dropna().unique())
        palette = {r: REGION_PALETTE.get(r, "#888888") for r in regions}
        for ax, (col, label) in zip(axes, metrics):
            sns.violinplot(data=df, x="region", y=col, order=regions,
                           palette=palette, ax=ax, inner="box",
                           linewidth=0.9, cut=0)
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.set_title(label, fontsize=9)
    else:
        for ax, (col, label) in zip(axes, metrics):
            sns.boxplot(data=df, y=col, ax=ax, linewidth=0.9,
                        flierprops=_FLIER, color="#4C72B0")
            ax.set_title(label, fontsize=9)

    fig.tight_layout()
    return fig


def fig_correlation_heatmap(df: pd.DataFrame) -> plt.Figure:
    key_cols = [
        "area_mu2", "circularity", "aspect_ratio", "eccentricity",
        "solidity", "convexity", "radial_cv", "radial_mean_mu",
        "asymmetry_index", "efd_deviation",
        "efd_power_h2", "efd_power_h3", "n_radial_peaks",
    ]
    available = [c for c in key_cols if c in df.columns]
    if len(available) < 3:
        return _empty("Not enough feature columns for correlation")

    labels = {
        "area_mu2": "Area", "circularity": "Circularity",
        "aspect_ratio": "Aspect Ratio", "eccentricity": "Eccentricity",
        "solidity": "Solidity", "convexity": "Convexity",
        "radial_cv": "Radial CV", "radial_mean_mu": "Radial Mean",
        "asymmetry_index": "Asymmetry", "efd_deviation": "EFD Deviation",
        "efd_power_h2": "EFD h2", "efd_power_h3": "EFD h3",
        "n_radial_peaks": "Radial Peaks",
    }
    corr = df[available].corr()
    corr.index   = [labels.get(c, c) for c in corr.index]
    corr.columns = [labels.get(c, c) for c in corr.columns]

    fig, ax = plt.subplots(figsize=(11, 9))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, linewidths=0.4,
                annot_kws={"size": 7.5}, ax=ax,
                cbar_kws={"shrink": 0.7, "label": "Pearson r"})
    ax.set_title("Feature Correlation Matrix", fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    return fig


def fig_region_comparison(df: pd.DataFrame) -> plt.Figure:
    if "region" not in df.columns:
        return _empty("No 'region' column found")

    metrics = [
        ("circularity",  "Circularity"),
        ("aspect_ratio", "Aspect Ratio"),
        ("eccentricity", "Eccentricity"),
        ("area_mu2",     "Area (µm²)"),
        ("efd_deviation","EFD Deviation"),
        ("radial_cv",    "Radial CV"),
    ]
    metrics = [(c, l) for c, l in metrics if c in df.columns]
    if not metrics:
        return _empty("No feature columns for region comparison")

    regions = sorted(df["region"].dropna().unique())
    palette = dict(zip(regions, ["#4C72B0", "#C44E52", "#55A868", "#CCB974"][:len(regions)]))

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle("Region Comparison — Morphological Features",
                 fontsize=13, fontweight="bold")

    for ax, (col, lab) in zip(axes.flat, metrics):
        sns.boxplot(data=df, x="region", y=col, order=regions,
                    palette=palette, ax=ax, width=0.5, linewidth=1,
                    flierprops=_FLIER)
        ax.set_title(lab, fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")
        for i, reg in enumerate(regions):
            n = df[df["region"] == reg][col].notna().sum()
            ax.text(i, ax.get_ylim()[0], f"n={n}",
                    ha="center", va="bottom", fontsize=8, color="gray")

    for ax in axes.flat[len(metrics):]:
        ax.set_visible(False)

    fig.tight_layout()
    return fig


def fig_segmentation_breakdown(df: pd.DataFrame) -> plt.Figure:
    if "segmentation_method" not in df.columns:
        return _empty("No segmentation_method column found")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle("Segmentation Method Summary", fontsize=13, fontweight="bold")

    counts = df["segmentation_method"].value_counts()
    colors = {"sam2": "#4C72B0", "watershed": "#55A868"}
    bar_colors = [colors.get(m, "#888") for m in counts.index]

    ax = axes[0]
    bars = ax.bar(counts.index, counts.values, color=bar_colors, edgecolor="white")
    ax.set_ylabel("Image Count")
    ax.set_title("Segmentation Method Used")
    total = counts.sum()
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total * 0.005,
                f"{v:,}\n({v/total*100:.1f}%)", ha="center", va="bottom", fontsize=9)

    if "confidence" in df.columns:
        ax = axes[1]
        for method in counts.index:
            vals = df[df["segmentation_method"] == method]["confidence"].dropna()
            if len(vals) < 3:
                continue
            sns.kdeplot(vals, ax=ax, label=method, color=colors.get(method, "#888"),
                        linewidth=1.8, fill=True, alpha=0.15)
        ax.set_xlabel("Segmentation Confidence Score")
        ax.set_ylabel("Density")
        ax.set_title("Confidence Distribution by Method")
        ax.legend()
    else:
        axes[1].set_visible(False)

    fig.tight_layout()
    return fig


# ===========================================================================
# CURVATURE FIGURES
# ===========================================================================

def fig_curvature_distributions(df: pd.DataFrame) -> plt.Figure:
    metrics = [
        ("curv_mean",   "Mean Curvature (mm⁻¹)"),
        ("curv_median", "Median Curvature (mm⁻¹)"),
        ("curv_std",    "Curvature Std Dev"),
        ("curv_iqr",    "Curvature IQR"),
    ]
    metrics = [(c, l) for c, l in metrics if c in df.columns]
    if not metrics:
        return _empty("No curvature columns found")

    regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
    palette = dict(zip(regions, ["#4C72B0", "#C44E52", "#55A868", "#CCB974"][:len(regions)]))

    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4.5))
    if len(metrics) == 1:
        axes = [axes]
    fig.suptitle("Curvature Distributions", fontsize=13, fontweight="bold")

    for ax, (col, label) in zip(axes, metrics):
        if regions:
            for reg in regions:
                vals = df[df["region"] == reg][col].dropna()
                if len(vals) < 3:
                    continue
                sns.kdeplot(vals, ax=ax, label=f"Region {reg}",
                            color=palette[reg], linewidth=1.8,
                            fill=True, alpha=0.15)
            ax.legend(fontsize=9)
        else:
            sns.kdeplot(df[col].dropna(), ax=ax, linewidth=1.8,
                        color="#4C72B0", fill=True, alpha=0.2)
        ax.set_xlabel(label, fontsize=10)
        ax.set_ylabel("Density")

    fig.tight_layout()
    return fig


def fig_curl_and_waves(df: pd.DataFrame) -> plt.Figure:
    metrics = [
        ("curl_index",        "Curl Index\n(0 = coiled, 1 = straight)"),
        ("curl_index_std",    "Curl Index Std Dev"),
        ("wave_count",        "Wave Count\n(peaks per image)"),
        ("wave_count_per_mm", "Wave Count per mm"),
    ]
    metrics = [(c, l) for c, l in metrics if c in df.columns]
    if not metrics:
        return _empty("No curl / wave columns found")

    regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
    palette = dict(zip(regions, ["#4C72B0", "#C44E52", "#55A868"][:len(regions)]))

    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4.5))
    if len(metrics) == 1:
        axes = [axes]
    fig.suptitle("Curl Index & Wave Count", fontsize=13, fontweight="bold")

    for ax, (col, label) in zip(axes, metrics):
        if regions:
            for reg in regions:
                vals = df[df["region"] == reg][col].dropna()
                if len(vals) < 3:
                    continue
                sns.kdeplot(vals, ax=ax, label=f"Region {reg}",
                            color=palette[reg], linewidth=1.8,
                            fill=True, alpha=0.15)
            ax.legend(fontsize=9)
        else:
            sns.kdeplot(df[col].dropna(), ax=ax, linewidth=1.8,
                        color="#55A868", fill=True, alpha=0.2)
        ax.set_xlabel(label.split("\n")[0], fontsize=10)
        ax.set_ylabel("Density")
        ax.set_title(label, fontsize=9)

    fig.tight_layout()
    return fig


def fig_curvature_vs_curl(df: pd.DataFrame) -> plt.Figure:
    if not _has(df, "curv_mean", "curl_index"):
        return _empty("Requires curv_mean and curl_index")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
    palette = dict(zip(regions, ["#4C72B0", "#C44E52", "#55A868"][:len(regions)]))

    if regions:
        for reg in regions:
            sub = df[df["region"] == reg]
            ax.scatter(sub["curv_mean"], sub["curl_index"],
                       color=palette[reg], alpha=0.5, s=18,
                       edgecolors="none", label=f"Region {reg}", rasterized=True)
        ax.legend(fontsize=10)
    else:
        ax.scatter(df["curv_mean"], df["curl_index"],
                   color="#4C72B0", alpha=0.5, s=18, edgecolors="none")

    ax.set_xlabel("Mean Curvature (mm⁻¹)", fontsize=11)
    ax.set_ylabel("Curl Index", fontsize=11)
    ax.set_title("Curvature vs Curl Index\n"
                 "(high curv + low curl = tight regular coil; high curl = straight)")
    fig.tight_layout()
    return fig


def fig_fiber_diameter(df: pd.DataFrame) -> plt.Figure:
    cols = [c for c in ["diameter_mean_mu", "diameter_cv"] if c in df.columns]
    if not cols:
        return _empty("No diameter columns found")

    regions = sorted(df["region"].dropna().unique()) if "region" in df.columns else []
    palette = dict(zip(regions, ["#4C72B0", "#C44E52", "#55A868"][:len(regions)]))
    labels  = {"diameter_mean_mu": "Mean Fiber Diameter (µm)",
               "diameter_cv":      "Fiber Diameter CV"}

    fig, axes = plt.subplots(1, len(cols), figsize=(6 * len(cols), 4.5))
    if len(cols) == 1:
        axes = [axes]
    fig.suptitle("Fiber Diameter Statistics", fontsize=13, fontweight="bold")

    for ax, col in zip(axes, cols):
        if regions:
            for reg in regions:
                vals = df[df["region"] == reg][col].dropna()
                if len(vals) < 3:
                    continue
                sns.kdeplot(vals, ax=ax, label=f"Region {reg}",
                            color=palette[reg], linewidth=1.8,
                            fill=True, alpha=0.15)
            ax.legend(fontsize=9)
        else:
            sns.kdeplot(df[col].dropna(), ax=ax, linewidth=1.8,
                        color="#CCB974", fill=True, alpha=0.2)
        ax.set_xlabel(labels[col], fontsize=10)
        ax.set_ylabel("Density")

    fig.tight_layout()
    return fig


def fig_curvature_summary_heatmap(df: pd.DataFrame) -> plt.Figure:
    feature_cols = [
        "curv_mean", "curv_median", "curv_std", "curv_max", "curv_cv",
        "curv_iqr", "curl_index", "wave_count_per_mm",
        "length_mean", "diameter_mean_mu", "diameter_cv",
    ]
    display = {
        "curv_mean": "Mean Curv", "curv_median": "Median Curv",
        "curv_std": "Curv Std", "curv_max": "Max Curv (p99)",
        "curv_cv": "Curv CV", "curv_iqr": "Curv IQR",
        "curl_index": "Curl Index", "wave_count_per_mm": "Waves/mm",
        "length_mean": "Mean Length", "diameter_mean_mu": "Diameter",
        "diameter_cv": "Diameter CV",
    }
    available = [c for c in feature_cols if c in df.columns]
    if len(available) < 3 or "region" not in df.columns:
        return _empty("Not enough curvature columns or no region column")

    regions = sorted(df["region"].dropna().unique())
    means   = df.groupby("region")[available].mean().reindex(regions)
    means.columns = [display[c] for c in available]
    z = (means - means.mean()) / (means.std() + 1e-10)

    fig, ax = plt.subplots(figsize=(13, max(3, len(regions) * 0.9)))
    sns.heatmap(z.T, annot=means.T, fmt=".2f", cmap="RdBu_r",
                center=0, linewidths=0.5, ax=ax,
                annot_kws={"size": 8.5},
                cbar_kws={"label": "Z-score", "shrink": 0.6})
    ax.set_title("Mean Curvature Feature per Region",
                 fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    return fig


# ===========================================================================
# SAMPLE-LEVEL FIGURES
# ===========================================================================

def fig_replicate_variability(df: pd.DataFrame, image_type: str = "section") -> plt.Figure:
    sub = df[df["image_type"] == image_type].copy() \
          if "image_type" in df.columns else df.copy()

    if "sample_id" not in sub.columns:
        return _empty("No sample_id column for variability analysis")

    metrics = (["circularity", "aspect_ratio", "area_mu2", "eccentricity"]
               if image_type == "section"
               else ["curv_mean", "curl_index", "wave_count_per_mm", "diameter_mean_mu"])
    metrics = [c for c in metrics if c in sub.columns]
    if not metrics:
        return _empty("No numeric feature columns for variability")

    counts = sub["sample_id"].value_counts()
    valid  = counts[counts >= 2].index
    sub    = sub[sub["sample_id"].isin(valid)]
    if sub.empty:
        return _empty("No samples with >= 2 replicates")

    cv_df = (sub.groupby("sample_id")[metrics].std() /
             sub.groupby("sample_id")[metrics].mean()).dropna()

    labels = {
        "circularity": "Circularity", "aspect_ratio": "Aspect Ratio",
        "area_mu2": "Area (µm²)", "eccentricity": "Eccentricity",
        "curv_mean": "Mean Curvature", "curl_index": "Curl Index",
        "wave_count_per_mm": "Waves/mm", "diameter_mean_mu": "Diameter (µm)",
    }

    fig, axes = plt.subplots(1, len(metrics), figsize=(4.5 * len(metrics), 4.5))
    if len(metrics) == 1:
        axes = [axes]
    fig.suptitle(f"Within-Individual Replicate Variability — {image_type.title()}\n"
                 f"(N = {len(cv_df)} individuals)",
                 fontsize=12, fontweight="bold")

    for ax, col in zip(axes, metrics):
        data = cv_df[col].dropna()
        ax.hist(data, bins=25, color="#4C72B0", edgecolor="white", alpha=0.85)
        med = data.median()
        ax.axvline(med, color="#C44E52", lw=1.8, ls="--",
                   label=f"Median = {med:.3f}")
        ax.set_title(labels.get(col, col), fontsize=10)
        ax.set_xlabel("CV (std / mean)")
        ax.set_ylabel("Individuals" if ax is axes[0] else "")
        ax.legend(fontsize=8)

    fig.tight_layout()
    return fig


def fig_sample_overview(df: pd.DataFrame) -> plt.Figure:
    useful = [
        "circularity_mean", "aspect_ratio_mean", "eccentricity_mean",
        "area_mu2_mean", "radial_cv_mean", "efd_deviation_mean",
        "curv_mean_mean", "curl_index_mean", "wave_count_per_mm_mean",
        "diameter_mean_mu_mean",
    ]
    available = [c for c in useful if c in df.columns]
    if len(available) < 2:
        return _empty("Not enough aggregated columns in per-sample CSV")

    sort_col = "n_valid" if "n_valid" in df.columns else available[0]
    top      = df.nlargest(min(30, len(df)), sort_col).copy()

    id_col = next((c for c in ["sample_id", "region"] if c in top.columns), None)
    if id_col:
        top.index = top[id_col].astype(str)

    data = top[available]
    z    = (data - data.mean()) / (data.std() + 1e-10)
    z.columns = [c.replace("_mean", "").replace("_", " ").title()
                 for c in z.columns]

    fig, ax = plt.subplots(figsize=(14, max(5, len(top) * 0.35 + 2)))
    sns.heatmap(z.T, cmap="RdBu_r", center=0, linewidths=0.3,
                ax=ax, cbar_kws={"label": "Z-score", "shrink": 0.6})
    ax.set_title(f"Per-Sample Feature Overview  (top {len(top)} samples)",
                 fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", rotation=45)
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    return fig


# ===========================================================================
# Generator catalogues — used by GUI app
# ===========================================================================

FigureSpec = tuple  # (group, title, figure)


def section_figures(df: pd.DataFrame) -> Generator[FigureSpec, None, None]:
    """Yield (group, title, fig) tuples for all cross-section figures."""
    sec = df[df["image_type"] == "section"] if "image_type" in df.columns else df

    yield "Overview",           "Segmentation Method",         fig_segmentation_breakdown(sec)
    yield "Shape Space",        "Geometric Feature Boxplots",  fig_geometric_boxplots(sec)
    yield "Shape Space",        "Size & Radius Distributions", fig_size_distributions(sec)
    yield "Boundary & Complexity", "Radial & EFD Features",    fig_radial_features(sec)
    yield "Boundary & Complexity", "EFD Harmonic Power Spectrum", fig_efd_power_spectrum(sec)
    yield "Comparison",         "Region Comparison",           fig_region_comparison(sec)
    yield "Summary",            "Feature Correlation Heatmap", fig_correlation_heatmap(sec)
    yield "Variability",        "Within-Individual Variability", fig_replicate_variability(df, "section")


def curvature_figures(df: pd.DataFrame) -> Generator[FigureSpec, None, None]:
    """Yield (group, title, fig) tuples for all curvature figures."""
    curv = df[df["image_type"] == "curvature"] if "image_type" in df.columns else df

    yield "Distributions",  "Curvature Distributions",   fig_curvature_distributions(curv)
    yield "Distributions",  "Curl Index & Wave Count",   fig_curl_and_waves(curv)
    yield "Distributions",  "Fiber Diameter",            fig_fiber_diameter(curv)
    yield "Relationships",  "Curvature vs Curl Index",   fig_curvature_vs_curl(curv)
    yield "Summary",        "Curvature Feature Heatmap", fig_curvature_summary_heatmap(curv)
    yield "Variability",    "Within-Individual Variability", fig_replicate_variability(df, "curvature")


def sample_figures(df: pd.DataFrame) -> Generator[FigureSpec, None, None]:
    """Yield figures derived from the per-sample aggregated CSV."""
    yield "Sample Overview", "Per-Sample Feature Heatmap", fig_sample_overview(df)
