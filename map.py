import ezdxf

INPUT_FILE = "CTP01(LALDARWAJA)FINAL.dxf"
OUTPUT_FILE = "CTP01_scaled_geometry_clean.dxf"

SCALE_FACTOR = 2.0  # make map bigger/smaller

def compute_geometry_centroid(msp):
    """Compute centroid using only geometry (not text)."""
    points = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            points.extend([(p[0], p[1]) for p in e.get_points("xy")])
        elif e.dxftype() == "LINE":
            points.extend([(e.dxf.start.x, e.dxf.start.y)
                           (e.dxf.end.x, e.dxf.end.y)])
        elif e.dxftype() in {"CIRCLE", "ARC"}:
            points.append((e.dxf.center.x, e.dxf.center.y))
    if not points:
        return (0, 0)
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return (cx, cy)

def scale_point(pt, factor, origin):
    return (
        origin[0] + (pt[0] - origin[0]) * factor,
        origin[1] + (pt[1] - origin[1]) * factor,
    )

def main():
    doc = ezdxf.readfile(INPUT_FILE)
    msp = doc.modelspace()

    # Only geometry used for centroid
    origin = compute_geometry_centroid(msp)
    print(f"Scaling geometry around centroid: {origin}")

    new_doc = ezdxf.new()
    new_msp = new_doc.modelspace()

    for e in msp:
        etype = e.dxftype()

        if etype == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            scaled_pts = [scale_point(p, SCALE_FACTOR, origin) for p in pts]
            new_msp.add_lwpolyline(
                scaled_pts,
                dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color},
                close=e.closed,
            )

        elif etype == "LINE":
            start = scale_point((e.dxf.start.x, e.dxf.start.y), SCALE_FACTOR, origin)
            end = scale_point((e.dxf.end.x, e.dxf.end.y), SCALE_FACTOR, origin)
            new_msp.add_line(start, end, dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color})

        elif etype == "CIRCLE":
            center = scale_point((e.dxf.center.x, e.dxf.center.y), SCALE_FACTOR, origin)
            new_msp.add_circle(center, e.dxf.radius * SCALE_FACTOR,
                               dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color})

        elif etype == "ARC":
            center = scale_point((e.dxf.center.x, e.dxf.center.y), SCALE_FACTOR, origin)
            new_msp.add_arc(center, e.dxf.radius * SCALE_FACTOR,
                            e.dxf.start_angle, e.dxf.end_angle,
                            dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color})

        else:
            # ✅ Leave text & other annotations untouched
            try:
                new_msp.add_foreign_entity(e)
            except Exception:
                pass

    new_doc.saveas(OUTPUT_FILE)
    print(f"✅ Scaled geometry (plots, roads, borders) saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
