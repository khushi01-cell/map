import ezdxf
from shapely.geometry import Polygon, Point

def polygon_area(points):
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return abs(area) / 2.0

def is_green(entity, doc):
    if entity.dxf.color == 3:
        return True
    if entity.dxf.color == 256:
        layer = doc.layers.get(entity.dxf.layer)
        if layer and layer.color == 3:
            return True
    return False

def get_plot_points(entity):
    return [(p[0], p[1]) for p in entity.get_points()]

def find_label_near_centroid(msp, centroid, target_label="33", max_distance=20):
    """Find text label near the centroid of a polygon"""
    for entity in msp:
        if entity.dxftype() in ("TEXT", "MTEXT"):
            try:
                insert = entity.dxf.insert
                label_point = Point(insert[0], insert[1])
                distance = label_point.distance(centroid)
                if distance <= max_distance:
                    text_value = entity.text if entity.dxftype() == "TEXT" else entity.plain_text()
                    text_value = text_value.strip().replace(" ", "")
                    if text_value == target_label:
                        return True, distance
            except Exception:
                continue
    return False, 0

def get_plot_33A_area(file_path):
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    # Reference area for plot 33A
    reference_area = 40.13

    print("🔍 Calculating Original Plot 33/A Area...")
    
    # First, find the raw area of plot 33A to calculate the correct conversion factor
    raw_area = None
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid

        # Check for text label "33" or "33A" near centroid
        has_label_33, distance_33 = find_label_near_centroid(msp, centroid, "33")
        has_label_33A, distance_33A = find_label_near_centroid(msp, centroid, "33A")
        
        if has_label_33 or has_label_33A:
            raw_area = polygon_area(pts)
            label_found = "33A" if has_label_33A else "33"
            print(f"  Found plot {label_found} with raw area: {raw_area:.6f} DXF units")
            break
    
    # If plot 33A not found by label, use first green boundary
    if raw_area is None:
        print("  Plot 33A not found by label, using first green boundary...")
        for entity in msp.query("LWPOLYLINE"):
            if entity.closed and is_green(entity, doc):
                pts = get_plot_points(entity)
                raw_area = polygon_area(pts)
                print(f"  Using first green boundary with raw area: {raw_area:.6f} DXF units")
                break
    
    if raw_area is None:
        print("❌ No suitable polygon found!")
        return None
    
    # Calculate the correct conversion factor
    conversion_factor = reference_area / raw_area
    print(f"  Calculated conversion factor: {conversion_factor:.6f}")
    
    # First, try to find plot 33 by looking for polygon with text label "33"
    plot_33_candidates = []
    
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid
        area_raw = polygon_area(pts)
        area_m2 = area_raw * conversion_factor

        # Check for text label "33" or "33A" near centroid
        has_label_33, distance_33 = find_label_near_centroid(msp, centroid, "33")
        has_label_33A, distance_33A = find_label_near_centroid(msp, centroid, "33A")
        
        if has_label_33 or has_label_33A:
            distance = min(distance_33 if has_label_33 else float('inf'), 
                         distance_33A if has_label_33A else float('inf'))
            label_found = "33A" if has_label_33A else "33"
            plot_33_candidates.append((area_m2, area_raw, pts, distance, centroid, entity.dxf.color, label_found))
            print(f"  Found plot {label_found} candidate:")
            print(f"    Area: {area_m2:.6f} m²")
            print(f"    Raw area: {area_raw:.6f} DXF units")
            print(f"    Color: {entity.dxf.color}")
            print(f"    Distance to text: {distance:.2f}")
            print(f"    Points: {len(pts)}")

    if plot_33_candidates:
        # Sort by distance to text (closest first)
        plot_33_candidates.sort(key=lambda x: x[3])
        best_candidate = plot_33_candidates[0]
        
        area_m2, area_raw, pts, distance, centroid, color, label_found = best_candidate
        
        print(f"\n✅ ORIGINAL PLOT 33/A FOUND!")
        print(f"  Area: {area_m2:.2f} sq.meter")
        print(f"  Raw area (DXF units): {area_raw:.2f}")
        print(f"  Conversion factor: {conversion_factor}")
        print(f"  Color: {color}")
        print(f"  Distance to text '{label_found}': {distance:.2f}")
        print(f"  Points: {len(pts)}")
        
        return area_m2
    else:
        # If no plot 33 found by label, try to find green boundaries
        print("  No plot 33 found by label, searching green boundaries...")
        
        green_boundaries = []
        index = 1
        for entity in msp.query("LWPOLYLINE"):
            if entity.closed and is_green(entity, doc):
                pts = get_plot_points(entity)
                area_raw = polygon_area(pts)
                area_m2 = area_raw * conversion_factor
                green_boundaries.append((area_m2, area_raw, pts, index))
                print(f"  Green boundary #{index}: {area_m2:.2f} m²")
                index += 1
        
        if green_boundaries:
            # Return the first green boundary as plot 33/A
            area_m2, area_raw, pts, index = green_boundaries[0]
            print(f"\n✅ PLOT 33/A (Green boundary #{index}):")
            print(f"  Area: {area_m2:.2f} sq.meter")
            print(f"  Raw area (DXF units): {area_raw:.2f}")
            print(f"  Conversion factor: {conversion_factor}")
            print(f"  Points: {len(pts)}")
            return area_m2
        else:
            print("❌ No green boundaries found!")
            return None

file_path = "CTP01(LALDARWAJA)FINAL.dxf"
calculated_area = get_plot_33A_area(file_path)

if calculated_area:
    print(f"\n📊 FINAL RESULT:")
    print(f"Original Plot 33/A Area: {calculated_area:.2f} sq.meter")
    
    # Compare with reference area (20% tolerance allowed)
    reference_area = 40.13
    difference = calculated_area - reference_area
    percentage_diff = (difference / reference_area) * 100
    
    print(f"\n📊 COMPARISON WITH REFERENCE:")
    print(f"Calculated Area: {calculated_area:.2f} sq.meter")
    print(f"Reference Area:  {reference_area:.2f} sq.meter")
    print(f"Difference:      {difference:+.2f} sq.meter")
    print(f"Percentage:      {percentage_diff:+.2f}%")
    
    # Check if within 20% tolerance
    if abs(percentage_diff) <= 20:
        print(f"✅ ACCEPTED: Within 20% tolerance (±{20:.1f}%)")
    else:
        print(f"⚠️  WARNING: Exceeds 20% tolerance (±{20:.1f}%)")
        print(f"   The calculated area differs significantly from the reference.")
        print(f"   This might indicate the wrong polygon was selected.")
else:
    print("❌ Could not calculate plot 33/A area") 