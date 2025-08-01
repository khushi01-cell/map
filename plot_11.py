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

def find_label_near_centroid(msp, centroid, target_label="11", max_distance=20):
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
                    # Check for "11", "11", etc.
                    if text_value in ["11", "11"]:
                        return True, distance
            except Exception:
                continue
    return False, 0

def calculate_plot_11_area(file_path):
    """Calculate plot 11 area using green boundary lines"""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    # Reference area for plot 11
    reference_area = 22901.20

    print("🔍 CALCULATING PLOT 11 AREA (GREEN LINES ONLY)")
    print("=" * 60)
    
    # Find plot 11 by looking for polygon with text label "11"
    plot_11_candidates = []
    
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid
        area_raw = polygon_area(pts)

        # Check for text label "11" near centroid
        has_label, distance = find_label_near_centroid(msp, centroid, "11")
        
        if has_label:
            plot_11_candidates.append((area_raw, pts, distance, centroid, entity.dxf.color))
            print(f"  Found plot 11 candidate:")
            print(f"    Raw area: {area_raw:.6f} DXF units")
            print(f"    Color: {entity.dxf.color}")
            print(f"    Distance to text: {distance:.2f}")
            print(f"    Points: {len(pts)}")

    if plot_11_candidates:
        # Sort by distance to text (closest first)
        plot_11_candidates.sort(key=lambda x: x[2])
        best_candidate = plot_11_candidates[0]
        
        area_raw, pts, distance, centroid, color = best_candidate
        
        print(f"\n✅ ORIGINAL PLOT 11 FOUND!")
        print(f"  Raw area (DXF units): {area_raw:.2f}")
        print(f"  Color: {color}")
        print(f"  Distance to text '11': {distance:.2f}")
        print(f"  Points: {len(pts)}")
        
        return area_raw
    else:
        # If no plot 11 found by label, try to find green boundaries
        print("  No plot 11 found by label, searching green boundaries...")
        
        green_boundaries = []
        index = 1
        for entity in msp.query("LWPOLYLINE"):
            if entity.closed and is_green(entity, doc):
                pts = get_plot_points(entity)
                area_raw = polygon_area(pts)
                green_boundaries.append((area_raw, pts, index))
                print(f"  Green boundary #{index}: {area_raw:.2f} DXF units")
                index += 1
        
        if green_boundaries:
            # Return the first green boundary as plot 11
            area_raw, pts, index = green_boundaries[0]
            print(f"\n✅ ORIGINAL PLOT 11 (Green boundary #{index}):")
            print(f"  Raw area (DXF units): {area_raw:.2f}")
            print(f"  Points: {len(pts)}")
            return area_raw
        else:
            print("❌ No green boundaries found!")
            return None

# Calculate area
file_path = "CTP01(LALDARWAJA)FINAL.dxf"
raw_area = calculate_plot_11_area(file_path)

if raw_area:
    print(f"\n📊 FINAL RESULT:")
    print(f"Original Plot 11 Raw Area: {raw_area:.2f} DXF units")
    
    # For comparison, let's calculate what the area would be if we assume
    # a reasonable conversion factor (this is just for reference)
    # We'll use a typical conversion factor based on common DXF scales
    # 1 DXF unit = 1 meter is a common assumption
    assumed_conversion = 1.0  # 1 DXF unit = 1 meter
    calculated_area = raw_area * assumed_conversion
    
    print(f"Calculated Area (assuming 1 DXF unit = 1 meter): {calculated_area:.2f} sq.meter")
    
    # Compare with reference area
    reference_area = 22901.20
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
        print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
    else:
        print(f"⚠️  WARNING: Exceeds 20% tolerance (±{20:.1f}%)")
        print(f"   The calculated area differs significantly from the reference.")
        print(f"   This might indicate the wrong polygon was selected or different scale.")
        print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
        
    # Calculate the actual conversion factor needed
    actual_conversion = reference_area / raw_area
    print(f"\n📏 CONVERSION FACTOR ANALYSIS:")
    print(f"To match reference area of {reference_area:.2f} sq.meter:")
    print(f"Conversion factor needed: {actual_conversion:.6f}")
    print(f"This means: 1 DXF unit = {actual_conversion:.6f} meters")
    
    # Show different conversion scenarios
    print(f"\n📏 ALTERNATIVE CONVERSION SCENARIOS:")
    print(f"1. If 1 DXF unit = 1 meter:")
    print(f"   Area = {raw_area:.2f} × 1.0 = {raw_area:.2f} sq.meter")
    
    print(f"2. If 1 DXF unit = 0.1 meter (10 DXF units = 1 meter):")
    print(f"   Area = {raw_area:.2f} × 0.01 = {raw_area * 0.01:.2f} sq.meter")
    
    print(f"3. If 1 DXF unit = 0.01 meter (100 DXF units = 1 meter):")
    print(f"   Area = {raw_area:.2f} × 0.0001 = {raw_area * 0.0001:.2f} sq.meter")
    
    print(f"4. To match reference area of {reference_area:.2f} sq.meter:")
    print(f"   Area = {raw_area:.2f} × {actual_conversion:.6f} = {raw_area * actual_conversion:.2f} sq.meter")
    
else:
    print("❌ Could not calculate plot 11 area") 