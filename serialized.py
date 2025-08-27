import ezdxf


input_file = "CTP01(LALDARWAJA)FINAL.dxf"
output_py = "CTP01_serialized.py"

doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

entities = []
all_points = []  # collect all coordinates for centroid

for e in msp:
    etype = e.dxftype()

    if etype == "LWPOLYLINE":
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "points": pts,
            "closed": e.closed,
        })
        all_points.extend(pts)

    elif etype == "LINE":
        start = (e.dxf.start.x, e.dxf.start.y)
        end = (e.dxf.end.x, e.dxf.end.y)
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "start": start,
            "end": end,
        })
        all_points.extend([start, end])

    elif etype == "CIRCLE":
        center = (e.dxf.center.x, e.dxf.center.y)
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "center": center,
            "radius": e.dxf.radius,
        })
        all_points.append(center)

    elif etype == "ARC":
        center = (e.dxf.center.x, e.dxf.center.y)
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "center": center,
            "radius": e.dxf.radius,
            "start_angle": e.dxf.start_angle,
            "end_angle": e.dxf.end_angle,
        })
        all_points.append(center)

    elif etype == "TEXT":
        insert = (e.dxf.insert.x, e.dxf.insert.y)
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "insert": insert,
            "text": e.dxf.text,
            "height": e.dxf.height,
        })
        all_points.append(insert)

    elif etype == "MTEXT":
        insert = (e.dxf.insert.x, e.dxf.insert.y)
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "insert": insert,
            "text": e.text,
            "char_height": e.dxf.char_height,
            "width": e.dxf.width,
        })
        all_points.append(insert)

# --- Compute centroid for scaling origin ---
if all_points:
    cx = sum(p[0] for p in all_points) / len(all_points)
    cy = sum(p[1] for p in all_points) / len(all_points)
else:
    cx, cy = (0, 0)

# --- Write a Python file that regenerates this DXF with scaling around centroid ---
with open(output_py, "w", encoding="utf-8") as f:
    f.write("import ezdxf\n\n")
    f.write("import numpy as np\n\n")
    f.write("SCALE_FACTOR = 5.5  # Adjust scale factor here\n\n")
    f.write(f"ORIGIN = ({cx}, {cy})  # centroid of drawing\n\n")
    f.write("def scale_point(pt, factor=SCALE_FACTOR, origin=ORIGIN):\n")
    f.write("    return (origin[0] + (pt[0]-origin[0])*factor, origin[1] + (pt[1]-origin[1])*factor)\n\n")
    f.write("def scale_points(pts, factor=SCALE_FACTOR, origin=ORIGIN):\n")
    f.write("    return [scale_point(p, factor, origin) for p in pts]\n\n")
    f.write("def build(filename='rebuilt_scaled.dxf'):\n")
    f.write("    doc = ezdxf.new()\n")
    f.write("    msp = doc.modelspace()\n\n")

    for e in entities:
        if e["type"] == "LWPOLYLINE":
            f.write(f"    msp.add_lwpolyline(scale_points({e['points']}), dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, 'closed': {e['closed']}}})\n")
        elif e["type"] == "LINE":
            f.write(f"    msp.add_line(scale_point({e['start']}), scale_point({e['end']}), dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "CIRCLE":
            f.write(f"    msp.add_circle(scale_point({e['center']}), {e['radius']}*SCALE_FACTOR, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "ARC":
            f.write(f"    msp.add_arc(scale_point({e['center']}), {e['radius']}*SCALE_FACTOR, {e['start_angle']}, {e['end_angle']}, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "TEXT":
            safe_text = e['text'].replace("'", "\\'")
            f.write(
                f"    msp.add_text('{safe_text}', "
                f"dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, 'height': {e['height']}*SCALE_FACTOR}})"
                f".set_pos(scale_point({e['insert']}))\n"
            )
        elif e["type"] == "MTEXT":
            safe_text = e['text'].replace("'''", "\\\"\\\"\\\"")
            f.write(
                f"    msp.add_mtext('''{safe_text}''', "
                f"dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, "
                f"'char_height': {e['char_height']}*SCALE_FACTOR, 'width': {e['width']}*SCALE_FACTOR}})"
                f".set_location(scale_point({e['insert']}))\n"
            )

    f.write("\n    doc.saveas(filename)\n")
    f.write("    print(f'DXF saved as {filename}')\n\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    build()\n")

print(f"✅ Python generator script written to {output_py}")
