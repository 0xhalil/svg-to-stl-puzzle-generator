
import argparse
import sys
from puzzle_processor import PuzzleProcessor

# Default Parameters
DEFAULT_THICKNESS = 3.0 # mm
DEFAULT_TOLERANCE = -0.2 # mm (negative buffer to create gap)
DEFAULT_DENSITY = 0.5 # units per sample (mm)

def parse_args():
    parser = argparse.ArgumentParser(description="Convert an SVG jigsaw puzzle to a 3D printable STL file.")
    parser.add_argument("input_file", help="Path to the input SVG file.")
    parser.add_argument("-o", "--output", default="jigsaw_pieces.stl", help="Output STL filename (default: jigsaw_pieces.stl)")
    parser.add_argument("--thickness", type=float, default=DEFAULT_THICKNESS, help=f"Thickness of the puzzle pieces in mm (default: {DEFAULT_THICKNESS})")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE, help=f"Tolerance offset in mm (negative value makes pieces smaller) (default: {DEFAULT_TOLERANCE})")
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY, help=f"Sampling density for discretizing curves (default: {DEFAULT_DENSITY})")
    return parser.parse_args()

def generate_stl_from_svg(input_file, output_file, thickness=DEFAULT_THICKNESS, tolerance=DEFAULT_TOLERANCE, density=DEFAULT_DENSITY):
    """
    Wrapper function for external calls (e.g. from app.py)
    """
    processor = PuzzleProcessor(
        input_file=input_file,
        output_file=output_file,
        thickness=thickness,
        tolerance=tolerance,
        density=density
    )
    processor.run()

if __name__ == "__main__":
    args = parse_args()
    try:
        generate_stl_from_svg(
            input_file=args.input_file,
            output_file=args.output,
            thickness=args.thickness,
            tolerance=args.tolerance,
            density=args.density
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
