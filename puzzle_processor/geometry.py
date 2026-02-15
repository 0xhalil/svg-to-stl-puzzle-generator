
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

def extend_line(line, dist=1.0):
    """
    Extends both ends of a LineString by a given distance.
    This helps ensure that lines which almost touch the border or each other
    will actually cross, allowing for proper intersection and polygonization.
    """
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

def discretize_path(path, density):
    """
    Converts a complex path (Bezier curves, etc.) into a series of points (LineString).
    """
    current_points = []
    lines = []
    
    for segment in path:
        # Check for discontinuity (Move command or separate subpaths)
        if current_points:
            last_p = complex(current_points[-1][0], current_points[-1][1])
            # If start of new segment does not match end of previous, flush line
            if abs(segment.start - last_p) > 1e-3:
                if len(current_points) > 1:
                    lines.append(LineString(current_points))
                current_points = []
        
        length = segment.length()
        if length < 1e-5:
            continue
        
        # Sample points along the segment
        count = max(2, int(length / density))
        
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
        lines.append(LineString(current_points))
        
    return lines
