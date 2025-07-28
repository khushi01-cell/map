import ezdxf
import numpy as np
from scipy.spatial import ConvexHull

DXF_PATH = 'CTP01(LALDARWAJA)FINAL.dxf'
COLOR_CODES = [3]  # Change this to [162] or any other color code as needed
TOL = 1e-3

def points_equal(p1, p2, tol=TOL):
    return abs(p1[0] - p2[0]) < tol and abs(p1[1] - p2[1]) < tol

def polygon_area(points):
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return 0.5 * abs(sum(x[i] * y[(i+1)%len(points)] - y[i] * x[(i+1)%len(points)] for i in range(len(points))))

def main():
    doc = ezdxf.readfile(DXF_PATH)
    msp = doc.modelspace()
    
    # Collect all lines of the specified color
    lines = []
    for e in msp.query('LINE'):
        if e.dxf.color in COLOR_CODES:
            lines.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
    
    print(f"Found {len(lines)} lines with color(s) {COLOR_CODES}")
    
    if len(lines) == 0:
        print("No lines found for the specified color!")
        return
    
    # Collect all unique endpoints
    points = []
    for start, end in lines:
        if not any(points_equal(start, p) for p in points):
            points.append(start)
        if not any(points_equal(end, p) for p in points):
            points.append(end)
    
    print(f"Found {len(points)} unique points")
    
    if len(points) < 3:
        print("Not enough points to form a polygon")
        return
    
    # Order points using convex hull
    pts = np.array(points)
    hull = ConvexHull(pts)
    hull_points = pts[hull.vertices]
    
    # Calculate area
    area_raw = polygon_area(hull_points)
    
    # Convert from DXF units to square meters
    # You may need to adjust the conversion factor for your drawing
    conversion_factor = 0.0006608  # Example from plot_one_color.py
    area_m2 = area_raw * conversion_factor
    
    print(f"Area of boundaries (color {COLOR_CODES}): {area_m2:.6f} m²")
    print(f"Raw area (DXF units): {area_raw:.2f}")
    print(f"Conversion factor used: {conversion_factor}")
    print(f"Number of hull points: {len(hull_points)}")

if __name__ == '__main__':
    main()
