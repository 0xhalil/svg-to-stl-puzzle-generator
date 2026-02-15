import argparse
import os
import struct
import numpy as np
from svgpathtools import svg2paths
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union, triangulate

# Default Parameters
DEFAULT_THICKNESS = 3.0 # mm
DEFAULT_TOLERANCE = -0.2 # mm (negative buffer to create gap)
DEFAULT_DENSITY = 0.5 # units per sample (mm)
EXTENSION_DIST = 1.0 # mm to extend cut lines to ensure intersection

def parse_args():
    parser = argparse.ArgumentParser(description="Convert an SVG jigsaw puzzle to a 3D printable STL file.")
    parser.add_argument("input_file", help="Path to the input SVG file.")
    parser.add_argument("-o", "--output", default="jigsaw_pieces.stl", help="Output STL filename (default: jigsaw_pieces.stl)")
    parser.add_argument("--thickness", type=float, default=DEFAULT_THICKNESS, help=f"Thickness of the puzzle pieces in mm (default: {DEFAULT_THICKNESS})")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE, help=f"Tolerance offset in mm (negative value makes pieces smaller) (default: {DEFAULT_TOLERANCE})")
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY, help=f"Sampling density for discretizing curves (default: {DEFAULT_DENSITY})")
    return parser.parse_args()

def extend_line(line, dist=1.0):
    if line.is_empty: return line
    coords = list(line.coords)
    if len(coords) < 2: return line
    
    # Start extension
    p0 = np.array(coords[0])
    p1 = np.array(coords[1])
    vec = p0 - p1
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        p0_new = p0 + (vec / norm) * dist
        coords[0] = tuple(p0_new)
        
    # End extension
    pn = np.array(coords[-1])
    pn1 = np.array(coords[-2])
    vec = pn - pn1
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        pn_new = pn + (vec / norm) * dist
        coords[-1] = tuple(pn_new)
        
    return LineString(coords)

def write_stl(triangles, filename):
    num_triangles = len(triangles)
    print(f"Writing {num_triangles} triangles to {filename}...")
    
    with open(filename, 'wb') as f:
        f.write(b'\0' * 80) # Header
        f.write(struct.pack('<I', num_triangles))
        for t in triangles:
            # Compute normal
            v1 = np.array(t[0])
            v2 = np.array(t[1])
            v3 = np.array(t[2])
            edge1 = v2 - v1
            edge2 = v3 - v1
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm == 0:
                normal = np.array([0, 0, 0])
            else:
                normal = normal / norm
            
            # Write normal
            f.write(struct.pack('<3f', float(normal[0]), float(normal[1]), float(normal[2])))
            # Write vertices
            for v in t:
                f.write(struct.pack('<3f', float(v[0]), float(v[1]), float(v[2])))
            # Attribute byte count
            f.write(struct.pack('<H', 0))

def process_puzzle(args):
    svg_path = os.path.abspath(args.input_file)
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found at {svg_path}")
        return

    print(f"Reading {svg_path}...")
    try:
        paths, attributes = svg2paths(svg_path)
    except Exception as e:
        print(f"Error parseing SVG: {e}")
        return
    
    lines = []
    print(f"Discretizing paths with density {args.density}...")
    
    for path in paths:
        current_points = []
        for segment in path:
            # Check for discontinuity (Move command or separate subpaths)
            if current_points:
                last_p = complex(current_points[-1][0], current_points[-1][1])
                # If start of new segment does not match end of previous, flush line
                if abs(segment.start - last_p) > 1e-3:
                    if len(current_points) > 1:
                        ls = LineString(current_points)
                        # Extend lines slightly to ensure intersection with border
                        ls = extend_line(ls, EXTENSION_DIST)
                        lines.append(ls)
                    current_points = []
            
            length = segment.length()
            if length < 1e-5:
                continue
            
            # Sample points along the segment
            count = max(2, int(length / args.density))
            
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
    if noded_lines.is_empty:
        print("Error: No valid lines found.")
        return

    print(f"Geometry bounds: {noded_lines.bounds}")
    
    print("Polygonizing...")
    polygons = list(polygonize(noded_lines))
    print(f"Found {len(polygons)} potential pieces.")
    
    if len(polygons) <= 1:
        print("Warning: Only found 0 or 1 polygons. Ensure the SVG lines form closed loops.")
        if len(polygons) == 1:
            print(f"Polygon area: {polygons[0].area}")
        return
    
    all_triangles = []
    
    print("Generating 3D geometry...")
    for i, poly in enumerate(polygons):
        # Apply tolerance
        shrunk_poly = poly.buffer(args.tolerance)
        
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
                    all_triangles.append(((v1[0], v1[1], args.thickness), (v2[0], v2[1], args.thickness), (v3[0], v3[1], args.thickness)))
                    
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
                    v3 = (p2[0], p2[1], args.thickness)
                    v4 = (p1[0], p1[1], args.thickness)
                    
                    # Triangle 1
                    all_triangles.append((v1, v2, v3))
                    # Triangle 2
                    all_triangles.append((v1, v3, v4))

    output_path = os.path.abspath(args.output)
    write_stl(all_triangles, output_path)
    print(f"Success! STL file saved to {output_path}")

if __name__ == "__main__":
    args = parse_args()
    process_puzzle(args)
