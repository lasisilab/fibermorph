"""Main workflow functions for fibermorph package."""

import pathlib
from datetime import datetime
from timeit import default_timer as timer
from typing import Union
import logging

import pandas as pd
from joblib import Parallel, delayed
from tqdm import tqdm

logger = logging.getLogger(__name__)


def raw2gray(
    input_directory: Union[str, pathlib.Path],
    output_location: Union[str, pathlib.Path],
    file_type: str,
    jobs: int
) -> bool:
    """Convert raw files to grayscale tiff files.

    Parameters
    ----------
    input_directory : str or pathlib.Path
        String or pathlib object for input directory containing raw files.
    output_location : str or pathlib.Path
        String or pathlib object for output directory where converted files should be created.
    file_type : str
        The extension for the raw files (e.g. ".RW2").
    jobs : int
        Number of jobs to run in parallel.

    Returns
    -------
    bool
        True on success.
    """
    from .utils.filesystem import make_subdirectory
    from .utils.timing import convert
    from .io.converters import raw_to_gray
    from .analysis.parallel import tqdm_joblib
    
    total_start = timer()

    file_list = [
        p for p in pathlib.Path(input_directory).rglob("*") if p.suffix in file_type
    ]
    list.sort(file_list)

    logger.info(f"Found {len(file_list)} files to convert")

    tiff_directory = make_subdirectory(output_location, append_name="tiff")

    with tqdm_joblib(
        tqdm(desc="raw2gray", total=len(file_list), unit="files", miniters=1)
    ) as progress_bar:
        progress_bar.monitor_interval = 2
        Parallel(n_jobs=jobs, verbose=0)(
            delayed(raw_to_gray)(f, tiff_directory) for f in file_list
        )

    total_end = timer()
    total_time = total_end - total_start

    tqdm.write(f"\n\nEntire analysis took: {convert(total_time)}\n\n")
    logger.info(f"raw2gray completed in {convert(total_time)}")

    return True


def curvature(
    input_directory: Union[str, pathlib.Path],
    main_output_path: Union[str, pathlib.Path],
    jobs: int,
    resolution: float,
    window_size: Union[float, int, list],
    window_unit: str,
    save_img: bool,
    within_element: bool,
    use_clahe: bool          = False,
    extended_curvature: bool = False,
) -> bool:
    """Takes directory of grayscale tiff images and analyzes curvature for each curve/line.

    Parameters
    ----------
    input_directory : str or pathlib.Path
        Input directory path as str or pathlib object.
    main_output_path : str or pathlib.Path
        Main output path as str or pathlib object.
    jobs : int
        Number of jobs to run in parallel.
    resolution : float
        Number of pixels per mm in original image.
    window_size : float or int or list
        Desired window of measurement in mm or pixels.
    window_unit : str
        Are the units for the window size in pixels or mm ('px' or 'mm').
    save_img : bool
        True or false for saving images for image processing steps.
    within_element : bool
        True or False for whether to save spreadsheets with within element curvature values.

    Returns
    -------
    bool
        True on success.
    """
    from .utils.filesystem import make_subdirectory, list_images
    from .utils.timing import convert
    from .analysis.curvature_pipeline import curvature_seq
    from .analysis.parallel import tqdm_joblib

    total_start = timer()

    # create an output directory for the analyses
    jetzt = datetime.now()
    timestamp = jetzt.strftime("%b%d_%H%M_")
    dir_name = str(timestamp + "fibermorph_curvature")
    output_path = make_subdirectory(main_output_path, append_name=dir_name)

    file_list = list_images(input_directory)
    logger.info(f"Found {len(file_list)} images to analyze")

    with tqdm_joblib(
        tqdm(desc="curvature", total=len(file_list), unit="files", miniters=1)
    ) as progress_bar:
        progress_bar.monitor_interval = 2
        im_df = Parallel(n_jobs=jobs, verbose=0)(
            delayed(curvature_seq)(
                input_file,
                output_path,
                resolution,
                window_size,
                window_unit,
                save_img,
                test=False,
                within_element=within_element,
                use_clahe=use_clahe,
                extended_curvature=extended_curvature,
            )
            for input_file in file_list
        )

    summary_df = pd.concat(im_df)

    jetzt = datetime.now()
    timestamp = jetzt.strftime("_%b%d_%H%M")

    output_file = pathlib.Path(output_path) / f"curvature_summary_data{timestamp}.csv"
    summary_df.to_csv(output_file)
    logger.info(f"Saved summary data to {output_file}")

    total_end = timer()
    total_time = total_end - total_start

    tqdm.write(f"\n\nComplete analysis took: {convert(total_time)}\n\n")
    logger.info(f"curvature completed in {convert(total_time)}")

    return True


def section(
    input_directory: Union[str, pathlib.Path],
    main_output_path: Union[str, pathlib.Path],
    jobs: int,
    resolution: float,
    minsize: float,
    maxsize: float,
    save_img: bool,
    use_sam2: bool          = False,
    sam2_checkpoint: str    = "",
    sam2_cfg: str           = "",
    extended_features: bool = False,
) -> bool:
    """Takes directory of grayscale images and analyzes cross-sectional properties.

    Parameters
    ----------
    input_directory : str or pathlib.Path
        Input directory path as str or pathlib object.
    main_output_path : str or pathlib.Path
        Main output path as str or pathlib object.
    jobs : int
        Number of jobs to run in parallel.
    resolution : float
        Number of pixels per micrometer in the image.
    minsize : float
        Minimum diameter for sections in microns.
    maxsize : float
        Maximum diameter for sections in microns.
    save_img : bool
        Whether to save intermediate images.

    Returns
    -------
    bool
        True on success.
    """
    from .utils.filesystem import make_subdirectory, list_images
    from .utils.timing import convert
    from .analysis.section_pipeline import section_seq
    from .analysis.parallel import tqdm_joblib

    total_start = timer()

    file_list = list_images(input_directory)
    logger.info(f"Found {len(file_list)} images to analyze")

    jetzt = datetime.now()
    timestamp = jetzt.strftime("%b%d_%H%M_")
    dir_name = str(timestamp + "fibermorph_section")
    output_path = make_subdirectory(main_output_path, append_name=dir_name)

    with tqdm_joblib(
        tqdm(desc="section", total=len(file_list), unit="files", miniters=1)
    ) as progress_bar:
        progress_bar.monitor_interval = 2
        section_df = Parallel(n_jobs=jobs, verbose=0)(
            delayed(section_seq)(
                f, output_path, resolution, minsize, maxsize, save_img,
                use_sam2=use_sam2,
                sam2_checkpoint=sam2_checkpoint,
                sam2_cfg=sam2_cfg,
                extended_features=extended_features,
            )
            for f in file_list
        )

    section_df = pd.concat(section_df).dropna()
    section_df.set_index("ID", inplace=True)

    df_output_path = pathlib.Path(output_path) / "summary_section_data.csv"
    section_df.to_csv(df_output_path)
    logger.info(f"Saved summary data to {df_output_path}")

    total_end = timer()
    total_time = total_end - total_start

    tqdm.write(f"\n\nComplete analysis took: {convert(total_time)}\n\n")
    logger.info(f"section completed in {convert(total_time)}")

    return True


def batch(
    section_directory: Union[str, pathlib.Path, None],
    curvature_directory: Union[str, pathlib.Path, None],
    main_output_path: Union[str, pathlib.Path],
    jobs: int                = 1,
    resolution_mu: float     = 4.25,
    resolution_mm: float     = 132.0,
    minsize: float           = 30.0,
    maxsize: float           = 150.0,
    window_size: int         = 50,
    window_unit: str         = "px",
    save_img: bool           = False,
    use_sam2: bool           = False,
    sam2_checkpoint: str     = "",
    sam2_cfg: str            = "",
    extended_features: bool  = True,
    extended_curvature: bool = True,
    use_clahe: bool          = False,
) -> bool:
    """Run batch analysis on section and/or curvature image directories.

    Produces hair_analysis_per_image.csv and hair_analysis_per_sample.csv
    in a timestamped subdirectory of main_output_path.

    Parameters
    ----------
    section_directory   : directory of cross-section images, or None to skip
    curvature_directory : directory of curvature images, or None to skip
    main_output_path    : parent directory for output
    jobs                : parallel jobs
    resolution_mu       : section resolution in µm/pixel
    resolution_mm       : curvature resolution in pixels/mm
    minsize / maxsize   : diameter filter in µm (section only)
    window_size         : Taubin sliding window size in pixels
    window_unit         : 'px' or 'mm'
    save_img            : save intermediate images
    use_sam2            : attempt SAM2 segmentation (falls back to watershed)
    sam2_checkpoint     : path to SAM2 .pt weights file
    sam2_cfg            : SAM2 model config yaml
    extended_features   : EFD, Hu moments, radial profile, shape class (section)
    extended_curvature  : curl_index, wave_count, diameter stats (curvature)
    use_clahe           : CLAHE preprocessing for curvature

    Returns
    -------
    bool — True on success
    """
    from .utils.filesystem import make_subdirectory
    from .utils.timing import convert
    from .pipeline.batch import run_batch

    total_start = timer()

    jetzt     = datetime.now()
    timestamp = jetzt.strftime("%b%d_%H%M_")
    out_dir   = make_subdirectory(main_output_path, append_name=str(timestamp + "fibermorph_batch"))

    run_batch(
        section_dir     = str(section_directory) if section_directory else None,
        curv_dir        = str(curvature_directory) if curvature_directory else None,
        output_dir      = str(out_dir),
        resolution_mu   = resolution_mu,
        resolution_mm   = resolution_mm,
        min_diam        = minsize,
        max_diam        = maxsize,
        window_size     = window_size,
        window_unit     = window_unit,
        use_sam2        = use_sam2,
        sam2_checkpoint = sam2_checkpoint,
        sam2_cfg        = sam2_cfg,
        save_img        = save_img,
        extended_features   = extended_features,
        extended_curvature  = extended_curvature,
        use_clahe           = use_clahe,
        jobs            = jobs,
    )

    total_end  = timer()
    total_time = total_end - total_start
    tqdm.write(f"\n\nBatch analysis took: {convert(total_time)}\n\n")
    logger.info(f"batch completed in {convert(total_time)}")
    return True
