#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ezdxf

# Color codes
COLOR_ORIGINAL_PLOT = 3  # Green
COLOR_FINAL_PLOT = 1     # Red
COLOR_ROAD = 1           # Red
COLOR_BORDER = 5         # Blue
COLOR_TEXT = 7           # White

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

def draw_plot(msp, coords, label, label_pos, is_final=True):
    layer = "PLOTS_FINAL" if is_final else "PLOTS_ORIGINAL"
    color = COLOR_FINAL_PLOT if is_final else COLOR_ORIGINAL_PLOT
    msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": layer, "color": color})
    msp.add_text(label, dxfattribs={
        "height": 8,
        "layer": "TEXT",
        "color": COLOR_TEXT,
        "insert": label_pos
    })

def draw_road(msp, start, end, label=None, label_pos=None):
    msp.add_line(start, end, dxfattribs={"layer": "ROADS", "color": COLOR_ROAD})
    if label and label_pos:
        msp.add_text(label, dxfattribs={
            "height": 6,
            "layer": "TEXT",
            "color": COLOR_TEXT,
            "insert": label_pos
        })

def draw_custom_map(doc):
    msp = doc.modelspace()

    # 🔴 Final Plots (Add coordinates manually)
    final_plots = [
        "1", "5", "6", "8", "9", "10", "15", "15/A", "17/A", "19/A", "19/B",
        "21", "21/B", "22", "22/A", "23", "24", "25", "25/A", "26", "27", "27/A",
        "28", "29", "30", "30/A", "31", "31/A", "32", "33", "34", "34/A", "35"
    ]
    x, y = 100, 100
    for i, plot in enumerate(final_plots):
        coords = [(x, y), (x+40, y), (x+40, y+40), (x, y+40)]
        label_pos = (x+10, y+15)
        draw_plot(msp, coords, plot, label_pos, is_final=True)
        x += 50
        if (i+1) % 10 == 0:
            x = 100
            y += 60

    # 🟢 Original Plots (Add coordinates manually)
    original_plots = [
        "1", "3", "6", "10", "15/A", "17/A", "19", "21/B", "23", "25", "27",
        "28/6/88", "29", "30", "31/A", "33", "34/A", "49"
    ]
    x, y = 100, 500
    for i, plot in enumerate(original_plots):
        coords = [(x, y), (x+40, y), (x+40, y+40), (x, y+40)]
        label_pos = (x+10, y+15)
        draw_plot(msp, coords, plot, label_pos, is_final=False)
        x += 50
        if (i+1) % 10 == 0:
            x = 100
            y += 60

    # 🛣️ Roads
    draw_road(msp, (80, 90), (600, 90), "Lal Bayerja to Marackha Road", (250, 80))
    draw_road(msp, (80, 480), (600, 480), "Service Road", (250, 470))

    # 🧭 Main Border
    msp.add_lwpolyline([(50, 50), (50, 700), (650, 700), (650, 50)], close=True,
                       dxfattribs={"layer": "BORDER", "color": COLOR_BORDER})

def main():
    dst_file = "lal_darwaja_full_map.dxf"
    doc = ezdxf.new("R2010")
    ensure_layers(doc)

    print("🛠️ Drawing full map with all plots...")
    draw_custom_map(doc)

    doc.saveas(dst_file)
    print(f"✅ Full map saved as {dst_file}")

if __name__ == "__main__":
    main()