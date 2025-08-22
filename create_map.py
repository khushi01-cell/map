#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redraw DXF into a clean scheme:
- Keeps original entity colors & layers exactly as in source DXF
- Copies plots, roads, borders, and text without forcing new colors
"""

import ezdxf

def ensure_layers(src_doc, dst_doc):
    """Copy all layers from source to destination so colors remain identical"""
    for layer in src_doc.layers:
        if layer.dxf.name not in dst_doc.layers:
            dst_doc.layers.add(layer.dxf.name, color=layer.dxf.color)

def redraw_entities(src_doc, dst_doc):
    src_msp = src_doc.modelspace()
    dst_msp = dst_doc.modelspace()

    for e in src_msp:
        try:
            if e.dxftype() == "LWPOLYLINE":
                dst_msp.add_lwpolyline(
                    e.get_points("xy"),
                    close=e.closed,
                    dxfattribs={
                        "layer": e.dxf.layer,
                        "color": e.dxf.color,
                        "linetype": e.dxf.linetype,
                        "lineweight": e.dxf.lineweight
                    }
                )

            elif e.dxftype() == "POLYLINE":
                points = [v.dxf.location for v in e.vertices]
                dst_msp.add_lwpolyline(
                    points,
                    close=e.is_closed,
                    dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color}
                )

            elif e.dxftype() == "CIRCLE":
                dst_msp.add_circle(
                    e.dxf.center, e.dxf.radius,
                    dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color}
                )

            elif e.dxftype() == "LINE":
                dst_msp.add_line(
                    e.dxf.start, e.dxf.end,
                    dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color}
                )

            elif e.dxftype() == "ARC":
                dst_msp.add_arc(
                    e.dxf.center, e.dxf.radius,
                    e.dxf.start_angle, e.dxf.end_angle,
                    dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color}
                )

            elif e.dxftype() == "TEXT":
                dst_msp.add_text(
                    e.dxf.text,
                    dxfattribs={
                        "height": e.dxf.height,
                        "rotation": e.dxf.rotation,
                        "layer": e.dxf.layer,
                        "color": e.dxf.color
                    }
                ).set_pos(e.dxf.insert, align=e.get_align())

            elif e.dxftype() == "MTEXT":
                dst_msp.add_mtext(
                    e.text,
                    dxfattribs={"layer": e.dxf.layer, "color": e.dxf.color}
                ).set_location(e.dxf.insert)

        except Exception as ex:
            print(f"⚠️ Skipped {e.dxftype()} due to {ex}")

def main():
    src_file = "CTP01(LALDARWAJA)FINAL.dxf"
    dst_file = "redrawn_samecolors.dxf"

    print(f"Loading {src_file}...")
    src_doc = ezdxf.readfile(src_file)

    dst_doc = ezdxf.new("R2010")
    ensure_layers(src_doc, dst_doc)

    print("Copying entities with original colors...")
    redraw_entities(src_doc, dst_doc)

    dst_doc.saveas(dst_file)
    print(f"✅ Redrawn map (same colors as source) saved as {dst_file}")

if __name__ == "__main__":
    main()
