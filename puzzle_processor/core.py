
import os
import numpy as np
from types import SimpleNamespace
from svgpathtools import svg2paths
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union, triangulate

from .geometry import extend_line
from .exporter import write_stl

# Default Parameters
DEFAULT_THICKNESS = 3.0 # mm
DEFAULT_TOLERANCE = -0.2 # mm (negative buffer to create gap)
DEFAULT_DENSITY = 0.5 # units per sample (mm)
EXTENSION_DIST = 1.0 # mm to extend cut lines to ensure intersection

class PuzzleProcessor:
    def __init__(self, input_file, output_file, thickness=DEFAULT_THICKNESS, 
                 tolerance=DEFAULT_TOLERANCE, density=DEFAULT_DENSITY):
        self.input_file = input_file
        self.output_file = output_file
        self.thickness = float(thickness)
        self.tolerance = float(tolerance)
        self.density = float(density)
        
    def run(self):
        svg_path = os.path.abspath(self.input_file)
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"Error: SVG file not found at {svg_path}")

        print(f"Reading {svg_path}...")
        try:
            paths, _ = svg2paths(svg_path)
        except Exception as e:
            raise ValueError(f"Error parsing SVG: {e}")
        
        lines = []
        print(f"Discretizing paths with density {self.density}...")
        
        for path in paths:
            # Reimplementing discretization logic inline for now, but could use geometry.discretize_path
            # The current logic is slightly intertwined with start/end processing
            current_points = []
            for segment in path:
                # Check for discontinuity (Move command or separate subpaths)
                if current_points:
                    last_p = complex(current_points[-1][0], current_points[-1][1])
                    # If start of new segment does not match end of previous, flush line
                    if abs(segment.start - last_p) > 1e-3:
                        if len(current_points) > 1:
                            ls = LineString(current_points)
                            ls = extend_line(ls, EXTENSION_DIST)
                            lines.append(ls)
                        current_points = []
                
                length = segment.length()
                if length < 1e-5:
                    continue
                
                # Sample points along the segment
                count = max(2, int(length / self.density))
                
                # If start of new line, add start point
                if not current_points:
                    p = segment.point(0)
                    current_points.append((round(p.real, 4), round(p.imag, 4)))

                for i in range(1, count + 1):
                    t = i / count
                    p = segment.point(t)
                    current_points.append((round(p.real, 4), round(p.imag, 4)))
            
            # Flush path end
            if len(current_points) > 1:
                ls = LineString(current_points)
                ls = extend_line(ls, EXTENSION_DIST)
                lines.append(ls)
        
        print(f"Noding {len(lines)} lines (this may take a moment)...")
        # unary_union splits lines at intersections, creating a valid planar graph
        noded_lines = unary_union(lines)
        if hasattr(noded_lines, "is_empty") and noded_lines.is_empty:
             raise ValueError("Error: No valid lines found.")

        print(f"Geometry bounds: {noded_lines.bounds}")
        
        print("Polygonizing...")
        polygons = list(polygonize(noded_lines))
        print(f"Found {len(polygons)} potential pieces.")
        
        if len(polygons) <= 1:
            print("Warning: Only found 0 or 1 polygons. Ensure the SVG lines form closed loops.")
            if len(polygons) == 1:
                print(f"Polygon area: {polygons[0].area}")
            # We don't necessarily raise here to allow inspection/debug
        
        all_triangles = []
        
        print("Generating 3D geometry...")
        for i, poly in enumerate(polygons):
            # Apply tolerance
            shrunk_poly = poly.buffer(self.tolerance)
            
            # Buffer might return MultiPolygon or empty if piece is too small/invalid
            if shrunk_poly.is_empty:
                continue
            
            target_polys = []
            if shrunk_poly.geom_type == 'MultiPolygon':
                target_polys.extend(shrunk_poly.geoms)
            elif shrunk_poly.geom_type == 'Polygon':
                target_polys.append(shrunk_poly)
                
            for piece in target_polys:
                # Triangulate top/bottom faces
                try:
                    mesh = triangulate(piece)
                except Exception as e:
                    print(f"Triangulation failed for piece {i}: {e}")
                    continue
                
                for tri in mesh:
                    # Check if triangle centroid is inside the piece
                    if piece.contains(tri.centroid):
                        coords = list(tri.exterior.coords)
                        v1, v2, v3 = coords[0], coords[1], coords[2]
                        
                        # Top face (z = THICKNESS) - CCW
                        all_triangles.append(((v1[0], v1[1], self.thickness), (v2[0], v2[1], self.thickness), (v3[0], v3[1], self.thickness)))
                        
                        # Bottom face (z = 0) - CW (to face down)
                        all_triangles.append(((v1[0], v1[1], 0), (v3[0], v3[1], 0), (v2[0], v2[1], 0)))
                
                # Side walls
                boundaries = [piece.exterior] + list(piece.interiors)
                for boundary in boundaries:
                    coords = list(boundary.coords)
                    for j in range(len(coords) - 1):
                        p1 = coords[j]
                        p2 = coords[j+1]
                        
                        # Create two triangles for the vertical face
                        v1 = (p1[0], p1[1], 0)
                        v2 = (p2[0], p2[1], 0)
                        v3 = (p2[0], p2[1], self.thickness)
                        v4 = (p1[0], p1[1], self.thickness)
                        
                        # Triangle 1
                        all_triangles.append((v1, v2, v3))
                        # Triangle 2
                        all_triangles.append((v1, v3, v4))

        output_path = os.path.abspath(self.output_file)
        print(f"Writing {len(all_triangles)} triangles to {output_path}...")
        write_stl(all_triangles, output_path)
        print(f"Success! STL file saved to {output_path}")

