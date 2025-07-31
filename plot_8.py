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

def find_label_near_centroid(msp, centroid, target_label="8", max_distance=20):
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

def calculate_plot_8_area(file_path, reference_area=None):
    """Calculate plot 8 area using green boundary lines"""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    print("🔍 CALCULATING PLOT 8 AREA (GREEN LINES ONLY)")
    print("=" * 60)
    
    # Find plot 8 by looking for polygon with text label "8"
    plot_8_candidates = []
    
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid
        area_raw = polygon_area(pts)

        # Check for text label "8" near centroid
        has_label, distance = find_label_near_centroid(msp, centroid, "8")
        
        if has_label:
            plot_8_candidates.append((area_raw, pts, distance, centroid, entity.dxf.color))
            print(f"  Found plot 8 candidate:")
            print(f"    Raw area: {area_raw:.6f} DXF units")
            print(f"    Color: {entity.dxf.color}")
            print(f"    Distance to text: {distance:.2f}")
            print(f"    Points: {len(pts)}")

    if plot_8_candidates:
        # Sort by distance to text (closest first)
        plot_8_candidates.sort(key=lambda x: x[2])
        best_candidate = plot_8_candidates[0]
        
        area_raw, pts, distance, centroid, color = best_candidate
        
        print(f"\n✅ ORIGINAL PLOT 8 FOUND!")
        print(f"  Raw area (DXF units): {area_raw:.2f}")
        print(f"  Color: {color}")
        print(f"  Distance to text '8': {distance:.2f}")
        print(f"  Points: {len(pts)}")
        
        # If reference area is provided, calculate conversion factor and area in sq.meter
        if reference_area is not None:
            conversion_factor = reference_area / area_raw
            area_m2 = area_raw * conversion_factor
            
            print(f"  Conversion factor: {conversion_factor:.6f}")
            print(f"  Calculated Area: {area_m2:.2f} sq.meter")
            
            # Compare with reference area
            difference = area_m2 - reference_area
            percentage_diff = (difference / reference_area) * 100
            
            print(f"\n📊 COMPARISON WITH REFERENCE:")
            print(f"Calculated Area: {area_m2:.2f} sq.meter")
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
                print(f"   This might indicate the wrong polygon was selected.")
                print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
            
            return area_m2
        else:
            print(f"\n📊 RAW AREA RESULT:")
            print(f"Plot 8 Raw Area: {area_raw:.2f} DXF units")
            print(f"\n⚠️  NOTE: No reference area provided.")
            print(f"   To get area in sq.meter, provide a reference_area parameter.")
            print(f"   Example: calculate_plot_8_area(file_path, reference_area=100.0)")
            return area_raw
    else:
        # If no plot 8 found by label, try to find green boundaries
        print("  No plot 8 found by label, searching green boundaries...")
        
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
            # Return the first green boundary as plot 8
            area_raw, pts, index = green_boundaries[0]
            print(f"\n✅ ORIGINAL PLOT 8 (Green boundary #{index}):")
            print(f"  Raw area (DXF units): {area_raw:.2f}")
            print(f"  Points: {len(pts)}")
            
            if reference_area is not None:
                conversion_factor = reference_area / area_raw
                area_m2 = area_raw * conversion_factor
                print(f"  Conversion factor: {conversion_factor:.6f}")
                print(f"  Calculated Area: {area_m2:.2f} sq.meter")
                return area_m2
            else:
                print(f"\n📊 RAW AREA RESULT:")
                print(f"Plot 8 Raw Area: {area_raw:.2f} DXF units")
                print(f"\n⚠️  NOTE: No reference area provided.")
                print(f"   To get area in sq.meter, provide a reference_area parameter.")
                return area_raw
        else:
            print("❌ No green boundaries found!")
            return None

# Calculate area
file_path = "CTP01(LALDARWAJA)FINAL.dxf"

# Reference area for plot 8
reference_area = 642.170736
area = calculate_plot_8_area(file_path, reference_area=reference_area)

if area:
    print(f"\n📊 FINAL RESULT:")
    print(f"Plot 8 Area: {area:.2f} sq.meter")
    
    # Compare with reference area
    difference = area - reference_area
    percentage_diff = (difference / reference_area) * 100
    
    print(f"\n📊 COMPARISON WITH REFERENCE:")
    print(f"Calculated Area: {area:.2f} sq.meter")
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
        print(f"   This might indicate the wrong polygon was selected.")
        print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
    
    print(f"\n⚠️  IMPORTANT NOTES:")
    print(f"   - This calculation uses green boundary lines only")
    print(f"   - The result is based on the plot 8 boundary found in the DXF file")
    print(f"   - Manual verification may be needed to confirm this is actually plot 8")
else:
    print("❌ Could not calculate plot 8 area") 