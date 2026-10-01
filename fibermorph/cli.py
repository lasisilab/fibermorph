"""Command-line interface for fibermorph package."""

import argparse
import math
import sys
import logging

logger = logging.getLogger(__name__)


def _window_size_value(text):
    """Parse one ``--window_size`` value: a number, or ``none`` for the whole hair.

    Used as the argparse ``type`` for ``--window_size``. Unit-dependent checks
    (positive, whole number of pixels) are made afterwards by
    :func:`normalize_window_sizes`, once ``--window_unit`` is known.

    Parameters
    ----------
    text : str
        One value as typed on the command line.

    Returns
    -------
    float or None
        The number, or None for ``none`` / ``None`` (any capitalisation).
    """
    cleaned = text.strip().lower()
    if cleaned == "none":
        return None
    try:
        return float(cleaned)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid window size {text!r}: expected a number or 'none'"
        ) from None


def normalize_window_sizes(values, window_unit):
    """Validate parsed ``--window_size`` values against ``--window_unit``.

    Parameters
    ----------
    values : list of (float or None) or None
        Values returned by :func:`_window_size_value`, or None when the option
        was not given.
    window_unit : str
        ``"px"`` or ``"mm"``.

    Returns
    -------
    list of (int or float) or None
        None for the whole-hair setting (option omitted, or the single value
        ``none``). Otherwise one number per value, in the order given: ints
        for ``px`` (so output files are named ``..._WindowSize-50px``), floats
        for ``mm`` (``..._WindowSize-0.5mm``).

    Raises
    ------
    ValueError
        If ``none`` is mixed with numbers, a value is not a finite number
        greater than 0, or a ``px`` value is not a whole number.
    """
    if values is None:
        return None
    if any(v is None for v in values):
        if len(values) > 1:
            raise ValueError(
                "'none' (fit the whole hair) must be given on its own, "
                "not repeated or combined with window sizes"
            )
        return None

    normalized = []
    for value in values:
        if not (math.isfinite(value) and value > 0):
            raise ValueError(
                f"window sizes must be finite numbers greater than 0 (got {value:g})"
            )
        if window_unit == "px":
            if not float(value).is_integer():
                raise ValueError(
                    f"with --window_unit px the window size must be a whole number "
                    f"of pixels (got {value:g}); use --window_unit mm for fractional sizes"
                )
            normalized.append(int(value))
        else:
            normalized.append(float(value))
    return normalized


def parse_args(argv=None):
    """Parse command-line arguments.

    Parameters
    ----------
    argv : list of str, optional
        Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns
    -------
    argparse.Namespace
        Parser argument namespace. ``window_size`` is None (fit the whole hair)
        or a list of window sizes: ints for ``--window_unit px``, floats for
        ``mm``.
    """
    from . import __version__
    
    parser = argparse.ArgumentParser(description="fibermorph")

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "-o",
        "--output_directory",
        metavar="",
        default=None,
        help="Required. Full path to and name of desired output directory. "
        "Will be created if it doesn't exist.",
    )

    parser.add_argument(
        "-i",
        "--input_directory",
        metavar="",
        default=None,
        help="Required. Full path to and name of desired directory containing "
        "input files.",
    )

    parser.add_argument(
        "--jobs",
        type=int,
        metavar="",
        default=1,
        help="Integer. Number of parallel jobs to run. Default is 1.",
    )

    parser.add_argument(
        "-s",
        "--save_image",
        action="store_true",
        default=False,
        help="Default is False. Will save intermediate curvature/section processing images "
        "if --save_image flag is included.",
    )

    gr_curv = parser.add_argument_group(
        "curvature options", "arguments used specifically for curvature module"
    )

    gr_curv.add_argument(
        "--resolution_mm",
        type=float,
        metavar="",
        default=132.0,
        help="Float. Curvature scale, interpreted per --resolution_mm_units. "
        "Default is 132 (pixels per mm).",
    )

    gr_curv.add_argument(
        "--resolution_mm_units",
        type=str,
        default="px_per_mm",
        choices=["px_per_mm", "mm_per_px"],
        help="Units for --resolution_mm: 'px_per_mm' (default, pixels per mm) or "
        "'mm_per_px' (mm per pixel). Converted to pixels/mm internally.",
    )

    gr_curv.add_argument(
        "--window_size",
        metavar="",
        default=None,
        nargs="+",
        type=_window_size_value,
        help="Float or integer or None. Desired size for window of measurement for curvature "
        "analysis in pixels or mm (given the flag --window_unit). Give several values "
        "(e.g. 25 50 100) to measure each window size in turn. With --window_unit px "
        "each value must be a whole number (50 or 50.0); with mm it can be any number "
        "greater than 0 (0.5). A window shorter than 10 pixels (for mm, after conversion "
        "with --resolution_mm) is not used: each hair is measured over its whole length "
        "in one window, with a warning. If nothing is entered, or the value is 'none', the "
        "default is None and the entire hair will be used for the curve fitting.",
    )

    gr_curv.add_argument(
        "--window_unit",
        type=str,
        default="px",
        choices=["px", "mm"],
        help="String. Unit of measurement for window of measurement for curvature analysis. "
        "Can be 'px' (pixels) or 'mm'. Default is 'px'.",
    )

    gr_curv.add_argument(
        "-W",
        "--within_element",
        action="store_true",
        default=False,
        help="Boolean. Default is False. Will create an additional directory with spreadsheets "
        "of raw curvature measurements for each hair if the --within_element flag is included.",
    )

    gr_curv.add_argument(
        "--use-clahe",
        action="store_true",
        default=False,
        dest="use_clahe",
        help="Enable CLAHE contrast enhancement before Frangi ridge filter. "
        "Improves results on images with uneven illumination.",
    )

    gr_curv.add_argument(
        "--extended-curvature",
        action="store_true",
        default=False,
        dest="extended_curvature",
        help="Compute extended curvature metrics: curl_index, curl_index_std, "
        "wave_count, wave_count_per_mm, length_total.",
    )

    gr_sect = parser.add_argument_group(
        "section options", "arguments used specifically for section module"
    )

    gr_sect.add_argument(
        "--resolution_mu",
        type=float,
        metavar="",
        default=4.25,
        help="Float. Section scale, interpreted per --resolution_mu_units. "
        "Default is 4.25 (pixels per micron).",
    )

    gr_sect.add_argument(
        "--resolution_mu_units",
        type=str,
        default="px_per_um",
        choices=["px_per_um", "um_per_px"],
        help="Units for --resolution_mu: 'px_per_um' (default, pixels per micron) "
        "or 'um_per_px' (microns per pixel, e.g. a 0.18 scale). Converted to "
        "pixels/µm internally.",
    )

    gr_sect.add_argument(
        "--minsize",
        type=int,
        metavar="",
        default=20,
        help="Integer. Minimum diameter in microns for sections. Default is 20.",
    )

    gr_sect.add_argument(
        "--maxsize",
        type=int,
        metavar="",
        default=150,
        help="Integer. Maximum diameter in microns for sections. Default is 150.",
    )

    gr_sect.add_argument(
        "--use-sam2",
        action="store_true",
        default=False,
        dest="use_sam2",
        help="Use SAM2 GPU segmentation for cross-sections. Falls back to watershed "
        "automatically if SAM2 is not installed or no GPU is available. "
        "Requires: pip install git+https://github.com/facebookresearch/segment-anything-2",
    )

    gr_sect.add_argument(
        "--sam2-checkpoint",
        type=str,
        metavar="",
        default="",
        dest="sam2_checkpoint",
        help="Path to SAM2 model checkpoint (.pt file). Only used with --use-sam2.",
    )

    gr_sect.add_argument(
        "--sam2-cfg",
        type=str,
        metavar="",
        default="",
        dest="sam2_cfg",
        help="Path to SAM2 model config YAML. Only used with --use-sam2.",
    )

    gr_sect.add_argument(
        "--extended-features",
        action="store_true",
        default=False,
        dest="extended_features",
        help="Compute extended cross-section features: EFD (40 coefficients), "
        "Hu moments (7), radial distance profile (7), and shape classification.",
    )

    gr_raw = parser.add_argument_group(
        "raw2gray options", "arguments used specifically for raw2gray module"
    )

    gr_raw.add_argument(
        "--file_extension",
        type=str,
        metavar="",
        default=".RW2",
        help="Optional. String. Extension of input files to use in input_directory when using "
        "raw2gray function. Default is .RW2.",
    )

    # Create mutually exclusive flags for each of fibermorph's modules
    group = parser.add_argument_group(
        "fibermorph module options",
        "mutually exclusive modules that can be run with the fibermorph package",
    )
    module_group = group.add_mutually_exclusive_group(required=True)

    module_group.add_argument(
        "--raw2gray",
        action="store_true",
        default=False,
        help="Convert raw image files to grayscale TIFF files.",
    )

    module_group.add_argument(
        "--curvature",
        action="store_true",
        default=False,
        help="Analyze curvature in grayscale TIFF images.",
    )

    module_group.add_argument(
        "--section",
        action="store_true",
        default=False,
        help="Analyze cross-sections in grayscale TIFF images.",
    )

    module_group.add_argument(
        "--demo_real_curv",
        action="store_true",
        default=False,
        help="A demo of fibermorph curvature analysis with real data.",
    )

    module_group.add_argument(
        "--demo_real_section",
        action="store_true",
        default=False,
        help="A demo of fibermorph section analysis with real data.",
    )

    args = parser.parse_args(argv)

    # Window sizes: check them against --window_unit (exit code 2 if invalid)
    try:
        args.window_size = normalize_window_sizes(args.window_size, args.window_unit)
    except ValueError as exc:
        parser.error(f"argument --window_size: {exc}")

    # Validate arguments
    demo_mods = [args.demo_real_curv, args.demo_real_section]

    if not any(demo_mods):
        if args.input_directory is None and args.output_directory is None:
            sys.exit("ExitError: need both --input_directory and --output_directory")
        if args.input_directory is None:
            sys.exit("ExitError: need --input_directory")
        if args.output_directory is None:
            sys.exit("ExitError: need --output_directory")
    else:
        if args.output_directory is None:
            sys.exit("ExitError: need --output_directory")

    return args


def main(argv=None):
    """Main entry point for fibermorph CLI.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments. Defaults to ``sys.argv[1:]``.
    """
    from .utils.filesystem import make_subdirectory
    from .utils.units import resolution_to_px_per_unit
    from .workflows import raw2gray, curvature, section, batch
    from . import demo

    args = parse_args(argv)

    # Normalise resolutions to the pixels-per-unit the pipeline expects,
    # honouring the reciprocal (µm/px, mm/px) units if the user chose them.
    resolution_mu = resolution_to_px_per_unit(args.resolution_mu, args.resolution_mu_units)
    resolution_mm = resolution_to_px_per_unit(args.resolution_mm, args.resolution_mm_units)

    if args.demo_real_curv is True:
        demo.real_curv(args.output_directory)
        sys.exit(0)
    elif args.demo_real_section is True:
        demo.real_section(args.output_directory)
        sys.exit(0)

    # Check for output directory and create it if it doesn't exist
    output_dir = make_subdirectory(args.output_directory)

    if args.raw2gray is True:
        raw2gray(args.input_directory, output_dir, args.file_extension, args.jobs)
    elif args.curvature is True:
        curvature(
            args.input_directory,
            output_dir,
            args.jobs,
            resolution_mm,
            args.window_size,
            args.window_unit,
            args.save_image,
            args.within_element,
            use_clahe=args.use_clahe,
            extended_curvature=args.extended_curvature,
        )
    elif args.section is True:
        section(
            args.input_directory,
            output_dir,
            args.jobs,
            resolution_mu,
            args.minsize,
            args.maxsize,
            args.save_image,
            use_sam2=args.use_sam2,
            sam2_checkpoint=args.sam2_checkpoint,
            sam2_cfg=args.sam2_cfg,
            extended_features=args.extended_features,
        )
    else:
        sys.exit("Error: No valid module selected")

    sys.exit(0)


if __name__ == "__main__":
    main()
