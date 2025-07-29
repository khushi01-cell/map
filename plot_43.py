import ezdxf

def polygon_area(points):
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return abs(area) / 2.0

def is_green(entity, doc):
    if entity.dxf.color == 3:
        return True
    if entity.dxf.color == 256:
        layer = doc.layers.get(entity.dxf.layer)
        if layer and layer.color == 3:
            return True
    return False

def get_plot_43_area(file_path, target_index=6):  # <-- Use correct index for "43"
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    index = 1
    for entity in msp.query("LWPOLYLINE"):
        if entity.closed and is_green(entity, doc):
            points = [(p[0], p[1]) for p in entity.get_points()]
            area = polygon_area(points)
            if index == target_index:
                print(f"✅ Plot 43 Area: {area:.2f} sq.meter")
                return
            index += 1

# Path to your DXF file
file_path = "CTP01(LALDARWAJA)FINAL.dxf"

# Update the target_index based on the order of green closed polylines
get_plot_43_area(file_path, target_index=6)
