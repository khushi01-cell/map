import ezdxf

input_file = "CTP01(LALDARWAJA)FINAL.dxf"
output_py = "CTP01_serialized.py"

doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

entities = []

for e in msp:
    etype = e.dxftype()

    if etype == "LWPOLYLINE":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "points": [(p[0], p[1]) for p in e.get_points("xy")],
            "closed": e.closed,
        })

    elif etype == "LINE":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "start": (e.dxf.start.x, e.dxf.start.y),
            "end": (e.dxf.end.x, e.dxf.end.y),
        })

    elif etype == "CIRCLE":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "center": (e.dxf.center.x, e.dxf.center.y),
            "radius": e.dxf.radius,
        })

    elif etype == "ARC":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "center": (e.dxf.center.x, e.dxf.center.y),
            "radius": e.dxf.radius,
            "start_angle": e.dxf.start_angle,
            "end_angle": e.dxf.end_angle,
        })

    elif etype == "TEXT":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "insert": (e.dxf.insert.x, e.dxf.insert.y),
            "text": e.dxf.text,
            "height": e.dxf.height,
        })

    elif etype == "MTEXT":
        entities.append({
            "type": etype,
            "layer": e.dxf.layer,
            "color": e.dxf.color,
            "insert": (e.dxf.insert.x, e.dxf.insert.y),
            "text": e.text,
            "char_height": e.dxf.char_height,
            "width": e.dxf.width,
        })

# --- Write a Python file that regenerates this DXF ---
with open(output_py, "w", encoding="utf-8") as f:
    f.write("import ezdxf\n\n")
    f.write("def build(filename='rebuilt.dxf'):\n")
    f.write("    doc = ezdxf.new()\n")
    f.write("    msp = doc.modelspace()\n\n")

    for e in entities:
        if e["type"] == "LWPOLYLINE":
            f.write(f"    msp.add_lwpolyline({e['points']}, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, 'closed': {e['closed']}}})\n")
        elif e["type"] == "LINE":
            f.write(f"    msp.add_line({e['start']}, {e['end']}, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "CIRCLE":
            f.write(f"    msp.add_circle({e['center']}, {e['radius']}, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "ARC":
            f.write(f"    msp.add_arc({e['center']}, {e['radius']}, {e['start_angle']}, {e['end_angle']}, dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}}})\n")
        elif e["type"] == "TEXT":
            safe_text = e['text'].replace("'", "\\'")
            f.write(f"    msp.add_text('{safe_text}', dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, 'height': {e['height']}}}).set_pos({e['insert']})\n")
        elif e["type"] == "MTEXT":
            safe_text = e['text'].replace("'''", "\\'\\'\\'")
            f.write(f"    msp.add_mtext('''{safe_text}''', dxfattribs={{'layer': '{e['layer']}', 'color': {e['color']}, 'char_height': {e['char_height']}, 'width': {e['width']}}}).set_location({e['insert']})\n")

    f.write("\n    doc.saveas(filename)\n")
    f.write("    print(f'DXF saved as {filename}')\n\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    build()\n")

print(f"✅ Python generator script written to {output_py}")
