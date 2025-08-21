#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redraw DXF into a clean scheme with specific colors:
- Original plots: green
- Final plots: red
- Roads: red
- Main border: blue
"""

import ezdxf


# Color codes
COLOR_ORIGINAL_PLOT = 3  # Green
COLOR_FINAL_PLOT    = 1  # Red
COLOR_ROAD          = 1  # Red
COLOR_BORDER        = 5  # Blue
COLOR_TEXT          = 7  # White (optional)


def ensure_layers(doc):
    layers = doc.layers
    for name, color in [
        ("PLOTS_ORIGINAL", COLOR_ORIGINAL_PLOT),
        ("PLOTS_FINAL", COLOR_FINAL_PLOT),
        ("ROADS", COLOR_ROAD),
        ("BORDER", COLOR_BORDER),
        ("TEXT", COLOR_TEXT)
    ]:
        if name not in layers:
            layers.add(name, color=color)


def redraw_entities(src_doc, dst_doc):
    src_msp = src_doc.modelspace()
    dst_msp = dst_doc.modelspace()

    for e in src_msp:
        try:
            if e.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                points = e.get_points("xy") if e.dxftype() == "LWPOLYLINE" else [v.dxf.location for v in e.vertices]

                # Decide color/layer based on original entity color
                orig_color = int(getattr(e.dxf, "color", 0) or 0)
                if orig_color == COLOR_ORIGINAL_PLOT:
                    layer = "PLOTS_ORIGINAL"
                    color = COLOR_ORIGINAL_PLOT
                else:
                    layer = "PLOTS_FINAL"
                    color = COLOR_FINAL_PLOT
   
                dst_msp.add_lwpolyline(points, close=e.closed, dxfattribs={"layer": layer, "color": color})

            elif e.dxftype() == "CIRCLE":
                dst_msp.add_circle(e.dxf.center, e.dxf.radius, dxfattribs={"layer": "PLOTS_ORIGINAL", "color": COLOR_ORIGINAL_PLOT})

            elif e.dxftype() == "LINE":
                dst_msp.add_line(e.dxf.start, e.dxf.end, dxfattribs={"layer": "ROADS", "color": COLOR_ROAD})

            elif e.dxftype() == "ARC":
                dst_msp.add_arc(e.dxf.center, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle, dxfattribs={"layer": "ROADS", "color": COLOR_ROAD})

            elif e.dxftype() == "TEXT":
                dst_msp.add_text(
                    e.dxf.text,
                    dxfattribs={
                        "height": e.dxf.height,
                        "rotation": e.dxf.rotation,
                        "layer": "TEXT",
                        "color": COLOR_TEXT
                    }
                ).set_pos(e.dxf.insert, align=e.get_align())

            elif e.dxftype() == "MTEXT":
                dst_msp.add_mtext(e.text, dxfattribs={"layer": "TEXT", "color": COLOR_TEXT}).set_location(e.dxf.insert)

        except Exception as ex:
            print(f"⚠️ Skipped {e.dxftype()} due to {ex}")


def main():
    src_file = "CTP01(LALDARWAJA)FINAL.dxf"
    dst_file = "redrawn_map.dxf"

    print(f"Loading {src_file}...")
    src_doc = ezdxf.readfile(src_file)

    dst_doc = ezdxf.new("R2010")
    ensure_layers(dst_doc)

    print("Redrawing entities...")
    redraw_entities(src_doc, dst_doc)

    # Optional: add main border (blue rectangle around map)
    dst_msp = dst_doc.modelspace()
    dst_msp.add_lwpolyline([(0,0), (0,1000), (1000,1000), (1000,0)], close=True, dxfattribs={"layer": "BORDER", "color": COLOR_BORDER})

    dst_doc.saveas(dst_file)
    print(f"✅ Redrawn clean map saved as {dst_file}")


if __name__ == "__main__":
    main()
