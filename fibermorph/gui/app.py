"""Streamlit-powered graphical interface for fibermorph."""

from __future__ import annotations

import io
import logging
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlsplit

try:  # pragma: no cover - exercised at runtime
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised at runtime
    st = None  # type: ignore[assignment]

import pandas as pd
import requests

from fibermorph import __version__
from fibermorph.workflows import curvature, section

LOGGER = logging.getLogger(__name__)


@dataclass
class CurvatureOptions:
    resolution_mm: float = 132.0
    window_size: Optional[float] = 50.0
    window_unit: str = "px"
    jobs: int = 1
    save_images: bool = False
    within_element: bool = False


@dataclass
class SectionOptions:
    resolution_mu: float = 4.25
    minsize: float = 20.0
    maxsize: float = 150.0
    jobs: int = 1
    save_images: bool = False


def _ensure_streamlit_installed() -> None:
    if st is None:
        raise RuntimeError(
            "Streamlit is not installed. Install GUI dependencies with "
            "`pip install fibermorph[gui]` and try again."
        )


def _write_uploaded_files(
    uploaded_files: Iterable["st.runtime.uploaded_file_manager.UploadedFile"],  # type: ignore[attr-defined]
    target_dir: Path,
) -> List[Path]:
    saved: List[Path] = []
    for file in uploaded_files:
        filename = Path(file.name).name
        suffix = Path(filename).suffix.lower()

        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(file.getvalue())) as archive:
                archive.extractall(target_dir)
        else:
            destination = target_dir / filename
            destination.write_bytes(file.getbuffer())

    saved = sorted(
        [
            p
            for p in target_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
        ]
    )
    return saved


def _latest_child_dir(directory: Path) -> Optional[Path]:
    children = [p for p in directory.iterdir() if p.is_dir()]
    if not children:
        return None
    return max(children, key=lambda p: p.stat().st_mtime)


def _download_dataset(url: str, target_dir: Path) -> List[Path]:
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()

    filename = Path(urlsplit(url).path).name or "dataset"
    suffix = Path(filename).suffix.lower()

    if suffix == ".zip":
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            archive.extractall(target_dir)
        files = sorted(
            [
                p
                for p in target_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
            ]
        )
        if not files:
            raise ValueError("No TIFF files were found inside the downloaded archive.")
        return files

    if suffix in {".tif", ".tiff"}:
        destination = target_dir / filename
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                handle.write(chunk)
        return [destination]

    raise ValueError("URL must point to a .tif/.tiff image or a .zip archive containing TIFFs.")


def _load_csvs(root: Path, pattern: str) -> List[pd.DataFrame]:
    frames: List[pd.DataFrame] = []
    for csv_path in sorted(root.rglob(pattern)):
        try:
            frames.append(pd.read_csv(csv_path))
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.warning("Unable to read %s: %s", csv_path, exc)
    return frames


def _zip_directory(directory: Path) -> bytes:
    archive_path = shutil.make_archive(
        base_name=str(directory),
        format="zip",
        root_dir=directory.parent,
        base_dir=directory.name,
    )
    data = Path(archive_path).read_bytes()
    Path(archive_path).unlink(missing_ok=True)
    return data


def _run_curvature(
    input_dir: Path,
    output_dir: Path,
    options: CurvatureOptions,
) -> List[pd.DataFrame]:
    curvature(
        input_directory=str(input_dir),
        main_output_path=str(output_dir),
        jobs=options.jobs,
        resolution=options.resolution_mm,
        window_size=options.window_size,
        window_unit=options.window_unit,
        save_img=options.save_images,
        within_element=options.within_element,
    )
    result_dir = _latest_child_dir(output_dir)
    if result_dir is None:
        return []
    return _load_csvs(result_dir, "curvature_summary_data*.csv")


def _run_section(
    input_dir: Path,
    output_dir: Path,
    options: SectionOptions,
) -> List[pd.DataFrame]:
    section(
        input_directory=str(input_dir),
        main_output_path=str(output_dir),
        jobs=options.jobs,
        resolution=options.resolution_mu,
        minsize=options.minsize,
        maxsize=options.maxsize,
        save_img=options.save_images,
    )
    result_dir = _latest_child_dir(output_dir)
    if result_dir is None:
        return []
    return _load_csvs(result_dir, "summary_section_data.csv")


def main() -> None:
    """Launch the Streamlit interface."""
    _ensure_streamlit_installed()

    st.set_page_config(page_title="fibermorph GUI", layout="wide")
    st.title("fibermorph")
    st.caption(f"Version {__version__}")

    analysis_mode = st.radio(
        "Choose analysis workflow", options=("Curvature", "Section"), horizontal=True
    )
    input_mode = st.radio(
        "Image source",
        options=("Upload TIFF files", "Download from URL"),
        horizontal=True,
    )

    uploaded_files = None
    dataset_url = ""
    if input_mode == "Upload TIFF files":
        uploaded_files = st.file_uploader(
            "Upload grayscale TIFF images or ZIP archives",
            type=["tif", "tiff", "zip"],
            accept_multiple_files=True,
            help="You can upload individual TIFFs or a ZIP folder containing multiple images.",
        )
    else:
        dataset_url = st.text_input(
            "Dataset URL",
            placeholder="https://zenodo.org/record/.../fibermorph_dataset.zip",
            help="Provide a direct link to a .zip archive or a single .tif/.tiff file.",
        ).strip()
        st.caption(
            "Tip: host sample data on GitHub Releases or Zenodo. "
            "Archived downloads are extracted automatically."
        )

    if analysis_mode == "Curvature":
        options = CurvatureOptions()
        with st.expander("Curvature settings", expanded=False):
            options.resolution_mm = st.number_input(
                "Resolution (pixels per mm)", min_value=1.0, value=options.resolution_mm
            )
            options.window_unit = st.selectbox("Window unit", options=["px", "mm"], index=0)
            window_size = st.number_input(
                f"Window size ({options.window_unit})",
                min_value=0.0,
                value=options.window_size if options.window_size else 0.0,
                help="Set to 0 to use the full length of each hair.",
            )
            options.window_size = None if window_size == 0 else window_size
            options.jobs = st.slider("Parallel jobs", min_value=1, max_value=8, value=options.jobs)
            options.save_images = st.checkbox("Save intermediate images", value=options.save_images)
            options.within_element = st.checkbox(
                "Save within-element curvature tables", value=options.within_element
            )
    else:
        options = SectionOptions()
        with st.expander("Section settings", expanded=False):
            options.resolution_mu = st.number_input(
                "Resolution (pixels per micron)", min_value=0.1, value=options.resolution_mu
            )
            options.minsize = st.number_input(
                "Minimum diameter (μm)", min_value=0.0, value=options.minsize
            )
            options.maxsize = st.number_input(
                "Maximum diameter (μm)", min_value=0.0, value=options.maxsize
            )
            options.jobs = st.slider("Parallel jobs", min_value=1, max_value=8, value=options.jobs)
            options.save_images = st.checkbox("Save intermediate images", value=options.save_images)

    if st.button("Run analysis", type="primary"):
        if input_mode == "Upload TIFF files" and not uploaded_files:
            st.error("Please upload at least one TIFF file.")
            return

        if input_mode == "Download from URL" and not dataset_url:
            st.error("Enter a dataset URL to download.")
            return

        with st.spinner("Running fibermorph analysis..."):
            with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
                input_dir = Path(tmp_in)
                output_dir = Path(tmp_out)
                if input_mode == "Upload TIFF files":
                    saved_files = _write_uploaded_files(uploaded_files, input_dir)  # type: ignore[arg-type]
                else:
                    try:
                        saved_files = _download_dataset(dataset_url, input_dir)
                    except Exception as exc:
                        st.error(f"Failed to download dataset: {exc}")
                        return

                if not saved_files:
                    st.error("No TIFF files were available for analysis.")
                    return

                if analysis_mode == "Curvature":
                    results = _run_curvature(input_dir, output_dir, options)
                else:
                    results = _run_section(input_dir, output_dir, options)

                result_dir = _latest_child_dir(output_dir)
                if not results or result_dir is None:
                    st.warning("Analysis finished but no summary files were produced.")
                    return

                combined = pd.concat(results, ignore_index=True)
                st.success("Analysis complete!")
                st.dataframe(combined)

                csv_bytes = combined.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download table as CSV",
                    data=csv_bytes,
                    file_name="fibermorph_results.csv",
                    mime="text/csv",
                )

                zip_bytes = _zip_directory(result_dir)
                st.download_button(
                    label="Download full output (ZIP)",
                    data=zip_bytes,
                    file_name="fibermorph_results.zip",
                    mime="application/zip",
                )


if __name__ == "__main__":  # pragma: no cover
    main()
