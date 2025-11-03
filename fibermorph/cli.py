"""Command-line interface for fibermorph package."""

import argparse
import sys
import logging

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments.
    
    Returns
    -------
    argparse.Namespace
        Parser argument namespace.
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
        type=int,
        metavar="",
        default=132,
        help="Integer. Number of pixels per mm for curvature analysis. Default is 132.",
    )

    gr_curv.add_argument(
        "--window_size",
        metavar="",
        default=None,
        nargs="+",
        help="Float or integer or None. Desired size for window of measurement for curvature "
        "analysis in pixels or mm (given the flag --window_unit). If nothing is entered, "
        "the default is None and the entire hair will be used for the curve fitting.",
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

    gr_sect = parser.add_argument_group(
        "section options", "arguments used specifically for section module"
    )

    gr_sect.add_argument(
        "--resolution_mu",
        type=float,
        metavar="",
        default=4.25,
        help="Float. Number of pixels per micron for section analysis. Default is 4.25.",
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

    args = parser.parse_args()

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


def main():
    """Main entry point for fibermorph CLI."""
    from .utils.filesystem import make_subdirectory
    from .workflows import raw2gray, curvature, section
    from . import demo
    
    args = parse_args()

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
            args.resolution_mm,
            args.window_size,
            args.window_unit,
            args.save_image,
            args.within_element,
        )
    elif args.section is True:
        section(
            args.input_directory,
            output_dir,
            args.jobs,
            args.resolution_mu,
            args.minsize,
            args.maxsize,
            args.save_image,
        )
    else:
        sys.exit("Error: No valid module selected")

    sys.exit(0)


if __name__ == "__main__":
    main()
