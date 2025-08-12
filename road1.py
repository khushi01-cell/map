import ezdxf

def build_segments(doc):
    msp = doc.modelspace()
    segments = []

    for e in msp:
        if e.dxftype() in ["LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE"]:
            print(f"Found {e.dxftype()} on layer {e.dxf.layer}")
            if e.dxftype() == "LINE":
                segments.append((e.dxf.start, e.dxf.end))
            elif e.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
                points = list(e.get_points())
                for i in range(len(points) - 1):
                    segments.append((points[i], points[i+1]))
            elif e.dxftype() == "ARC":
                print("⚠ ARC found — needs conversion to small segments if you want length")
            elif e.dxftype() == "SPLINE":
                print("⚠ SPLINE found — needs discretization")

    print(f"Total segments collected: {len(segments)}")
    return segments

if __name__ == "__main__":
    doc = ezdxf.readfile("CTP01(LALDARWAJA)FINAL.dxf")
    build_segments(doc)
