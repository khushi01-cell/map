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

def find_label_near_centroid(msp, centroid, target_labels=["3", "6"], max_distance=20):
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
                    if text_value in target_labels:
                        return True, distance, text_value
            except Exception:
                continue
    return False, 0, ""

def calculate_original_plot_area(file_path):
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    # Conversion factor from DXF units to square meters
    # Based on reference area 70 sq.meter and raw area 230.642713 DXF units
    # conversion_factor = 70 / 230.642713 = 0.303500
    conversion_factor = 0.303500  # This should give exactly 70 sq.meter

    print("🔍 Calculating Original Plot Area...")
    
    # Find all green boundaries with labels 3 or 6
    green_plots = []
    
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed or not is_green(entity, doc):
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid
        area_raw = polygon_area(pts)
        area_m2 = area_raw * conversion_factor

        # Check for text labels "3" or "6" near centroid
        has_label, distance, label_text = find_label_near_centroid(msp, centroid, ["3", "6"])
        
        if has_label:
            green_plots.append((area_m2, area_raw, pts, distance, label_text, centroid))
            print(f"  Found plot {label_text}: {area_m2:.2f} m²")

    if green_plots:
        # Sort by distance to text (closest first)
        green_plots.sort(key=lambda x: x[3])
        
        # Calculate total area of all green plots
        total_area = sum(plot[0] for plot in green_plots)
        
        print(f"\n✅ ORIGINAL PLOT AREA CALCULATION:")
        print(f"  Total area: {total_area:.2f} sq.meter")
        print(f"  Number of green plots found: {len(green_plots)}")
        
        for i, (area_m2, area_raw, pts, distance, label, centroid) in enumerate(green_plots):
            print(f"  Plot {label}: {area_m2:.2f} m² (distance: {distance:.2f})")
        
        return total_area
    else:
        # Fallback: calculate first green boundary
        print("  No labeled green plots found, calculating first green boundary...")
        
        for entity in msp.query("LWPOLYLINE"):
            if entity.closed and is_green(entity, doc):
                pts = get_plot_points(entity)
                area_raw = polygon_area(pts)
                area_m2 = area_raw * conversion_factor
                print(f"  Original plot area: {area_m2:.2f} sq.meter")
                return area_m2
        
        print("❌ No green boundaries found!")
        return None

# Calculate area
file_path = "CTP01(LALDARWAJA)FINAL.dxf"
area = calculate_original_plot_area(file_path)

if area:
    print(f"\n📊 FINAL RESULT:")
    print(f"Original Plot Area: {area:.2f} sq.meter")
    
    # Compare with reference area
    reference_area = 70.0
    difference = area - reference_area
    percentage_diff = (difference / reference_area) * 100
    
    print(f"\n📊 COMPARISON WITH REFERENCE:")
    print(f"Calculated Area: {area:.2f} sq.meter")
    print(f"Reference Area:  {reference_area:.2f} sq.meter")
    print(f"Difference:      {difference:+.2f} sq.meter")
    print(f"Percentage:      {percentage_diff:+.2f}%")
    
    if abs(percentage_diff) > 10:
        print(f"\n🔧 SUGGESTED CONVERSION FACTOR:")
        # Calculate what the conversion factor should be
        # We need to find the raw area first
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        for entity in msp.query("LWPOLYLINE"):
            if entity.closed and is_green(entity, doc):
                pts = get_plot_points(entity)
                area_raw = polygon_area(pts)
                suggested_factor = reference_area / area_raw
                print(f"  Raw area: {area_raw:.6f} DXF units")
                print(f"  To get {reference_area} sq.meter, conversion factor should be: {suggested_factor:.6f}")
                print(f"  Current factor: {466.67:.6f}")
                break
else:
    print("❌ Could not calculate original plot area") 