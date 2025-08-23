import ezdxf
from shapely.geometry import Polygon
import math

def lwpolyline_to_polygon(entity):
    """Convert DXF LWPolyline to Shapely Polygon"""
    points = [point[:2] for point in entity.get_points("xy")]
    return Polygon(points)

def scale_polygon(entity, target_area):
    poly = lwpolyline_to_polygon(entity)
    current_area = poly.area
    scale_factor = math.sqrt(target_area / current_area)

    # Scale around centroid
    cx, cy = poly.centroid.x, poly.centroid.y
    new_points = []
    for x, y in poly.exterior.coords[:-1]:  # skip duplicate last point
        new_x = cx + (x - cx) * scale_factor
        new_y = cy + (y - cy) * scale_factor
        new_points.append((new_x, new_y))

    # Update polyline vertices
    entity.set_points(new_points, format="xy")
    print(f"Scaled area from {current_area:.2f} to {target_area:.2f}")

if __name__ == "__main__":
    input_file = "CTP01(LALDARWAJA)FINAL.dxf"
    output_file = "modified_final_plot6_area.dxf"

    doc = ezdxf.readfile(input_file)
    msp = doc.modelspace()

    # Target area: 4971 sq.yds → in sq.m
    target_area_sqm = 4971 * 0.836127  

    # Find red closed polylines (color 1 = red, or layer "FinalPlots")
    for entity in msp.query("LWPOLYLINE"):
        if entity.closed and entity.dxf.color == 1:  # red polyline
            scale_polygon(entity, target_area_sqm)

    doc.saveas(output_file)
    print(f"💾 Saved updated DXF as {output_file}")
