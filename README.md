# SVG Jigsaw Puzzle to STL Generator

This utility converts an SVG file containing jigsaw puzzle paths into a 3D printable STL file.

## Features

- **Parses SVG paths**: Reads complex paths from SVG files.
- **Topology Reconstruction**: Nodes intersections and polygonizes paths to identify closed puzzle pieces.
- **Robust Line Intersection**: Automatically extends cut lines to ensure clean intersections with the border and other lines, even if the input SVG has gaps.
- **Parametric 3D Generation**:
    - **Thickness**: Adjustable extrusion height.
    - **Tolerance/Kerf**: Adjustable offset to ensure pieces fit together after printing (negative buffer).
- **STL Export**: Generates a binary STL file ready for slicers.

## Installation

1.  **Clone the repository** (or download usage files).
2.  **Create a virtual environment** (recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script `generate_stl.py` with the input SVG file:

```bash
python generate_stl.py jigsaw.svg
```

### Options

| Argument | Description | Default |
| :--- | :--- | :--- |
| `input_file` | Path to the input SVG file. | (Required) |
| `-o`, `--output` | Output STL filename. | `jigsaw_pieces.stl` |
| `--thickness` | Thickness of the pieces in mm. | `3.0` |
| `--tolerance` | Tolerance offset (gap) in mm. Negative values create gaps. | `-0.4` |
| `--density` | Sampling density (mm) for curves. Smaller is smoother. | `0.5` |

### Example

Generate a puzzle with 0.2mm gap ( -0.1mm offset per piece), 4mm thickness:

```bash
python generate_stl.py my_puzzle.svg -o output.stl --thickness 4.0 --tolerance -0.1
```

## Requirements

- Python 3.x
- `numpy`
- `shapely`
- `svgpathtools`
- `scipy` (dependency of shapely/trimesh operations if needed)
