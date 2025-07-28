import ezdxf
from ezdxf.math import area, Vec2

doc = ezdxf.readfile("CTP01(LALDARWAJA)FINAL.dxf")
msp = doc.modelspace()
M2_TO_SQYDS = 1.19599

# Collect all text entities for lookup
text_entities = []
for e in msp:
    if e.dxftype() in ["TEXT", "MTEXT"]:
        try:
            text = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
            insert = e.dxf.insert if hasattr(e.dxf, 'insert') else e.dxf.insert
            text_entities.append((text.strip(), Vec2(insert.x, insert.y)))
        except Exception:
            continue

# Search for plots in area range
for idx, entity in enumerate(msp):
    if entity.dxftype() == "LWPOLYLINE" and entity.closed:
        points = entity.get_points('xy')
        raw = area(points)
        sqyd = raw * M2_TO_SQYDS

        if 51 <= sqyd <= 52:
            # Compute centroid of the polyline
            x = [p[0] for p in points]
            y = [p[1] for p in points]
            centroid = Vec2(sum(x)/len(x), sum(y)/len(y))

            # Find closest text entity
            closest_text = None
            min_dist = float('inf')
            for text, position in text_entities:
                dist = (centroid - position).magnitude
                if dist < min_dist and dist < 10:
                    print(f"Checking text '{text}' at distance {dist:.2f}")
 # 10 units = proximity threshold
                    min_dist = dist
                    closest_text = text

            plot_number = closest_text if closest_text else "UNKNOWN"
            print(f"Plot Number: {plot_number}, Area: {sqyd:.2f} sq.yds, Raw: {raw:.2f}, Entity Index: {idx}")
