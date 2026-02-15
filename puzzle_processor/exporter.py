
import struct
import numpy as np

def write_stl(triangles, filename):
    """
    Writes a list of triangles to a binary STL file.
    
    Args:
        triangles: List of tuples, where each tuple contains 3 vertices like ((x1,y1,z1), (x2,y2,z2), (x3,y3,z3))
        filename: Output path for the STL file
    """
    num_triangles = len(triangles)
    
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
