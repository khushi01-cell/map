import ezdxf

def create_tp_scheme_map(output_file="tp_scheme_map.dxf"):
    # Create a new DXF drawing
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # -------------------------
    # 1. Boundary of Scheme
    # -------------------------
    scheme_boundary = [
        (0, 0), (200, 0), (200, 150), (0, 150), (0, 0)
    ]
    msp.add_lwpolyline(scheme_boundary, close=True, dxfattribs={"color": 6})  # magenta

    # -------------------------
    # 2. Roads
    # -------------------------
    # Example main road
    msp.add_lwpolyline([(10, 10), (190, 10)], dxfattribs={"color": 6})  # pink/magenta
    # Example internal road
    msp.add_lwpolyline([(100, 10), (100, 140)], dxfattribs={"color": 3})  # green

    # -------------------------
    # 3. Plot Boundaries
    # -------------------------
    plot1 = [(10, 20), (90, 20), (90, 60), (10, 60), (10, 20)]
    plot2 = [(110, 20), (190, 20), (190, 60), (110, 60), (110, 20)]
    msp.add_lwpolyline(plot1, close=True, dxfattribs={"color": 2})  # red
    msp.add_lwpolyline(plot2, close=True, dxfattribs={"color": 2})  # red

    # -------------------------
    # 4. Labels (Plot Numbers)
    # -------------------------
    text_plot1 = msp.add_text("1", dxfattribs={"height": 3, "color": 1})
    text_plot1.dxf.insert = (40, 40)  # Set the insertion point for Plot 1

    text_plot2 = msp.add_text("2", dxfattribs={"height": 3, "color": 1})
    text_plot2.dxf.insert = (140, 40)  # Set the insertion point for Plot 2

    # -------------------------
    # 5. Legend
    # -------------------------
    text_legend = msp.add_text("LEGEND:", dxfattribs={"height": 3, "color": 5})
    text_legend.dxf.insert = (220, 140)  # Set the insertion point for the legend title

    msp.add_text("1) Boundary of T.P. Scheme", dxfattribs={"height": 2}).dxf.insert = (220, 130)
    msp.add_text("2) Roads", dxfattribs={"height": 2}).dxf.insert = (220, 125)
    msp.add_text("3) Plot Boundaries", dxfattribs={"height": 2}).dxf.insert = (220, 120)

    # -------------------------
    # Save File
    # -------------------------
    doc.saveas(output_file)
    print(f"Map saved as {output_file}")

if __name__ == "__main__":
    create_tp_scheme_map()
