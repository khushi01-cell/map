import ezdxf

def scale_point(x, y, origin, scale_factor=1.2):
    return origin[0] + (x - origin[0]) * scale_factor, origin[1] + (y - origin[1]) * scale_factor

def get_centroid(points):
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    return cx, cy

def is_boundary_entity(entity, target_layers, target_colors):
    # Check if entity layer or color matches boundary criteria
    return (entity.dxf.layer in target_layers) or (entity.dxf.color in target_colors)

def scale_plot_boundaries(doc, scale_factor=1.5):
    msp = doc.modelspace()
    to_delete = []

    target_layers = ["0"]  # Add your layers here
    target_colors = [6, 1, 3]  # Magenta(6), White/Default(7), Green(3), add as needed

    for e in msp.query("LWPOLYLINE POLYLINE LINE"):
        if not is_boundary_entity(e, target_layers, target_colors):
            continue
        if e.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
            points = [(p[0], p[1]) for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        elif e.dxftype() == "LINE":
            points = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        else:
            continue

        origin = get_centroid(points)
        new_points = [scale_point(x, y, origin, scale_factor) for x, y in points]

        if e.dxftype() == "LWPOLYLINE":
            msp.add_lwpolyline(new_points, dxfattribs=e.dxfattribs())
        elif e.dxftype() == "POLYLINE":
            msp.add_polyline2d(new_points, dxfattribs=e.dxfattribs())
        elif e.dxftype() == "LINE":
            msp.add_line(new_points[0], new_points[1], dxfattribs=e.dxfattribs())

        to_delete.append(e)

    for e in to_delete:
        msp.delete_entity(e)

# Usage example
doc = ezdxf.readfile("CTP01(LALDARWAJA)FINAL.dxf")
scale_plot_boundaries(doc, scale_factor=1.5)  # Increased scale factor for more impact
doc.saveas("output_big_plot_boundaries.dxf")
