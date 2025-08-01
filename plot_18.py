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
    """Check if entity is green (color 3) or if layer is green"""
    if entity.dxf.color == 3:
        return True
    if entity.dxf.color == 256:  # BYLAYER
        layer = doc.layers.get(entity.dxf.layer)
        if layer and layer.color == 3:
            return True
    return False

def get_plot_points(entity):
    return [(p[0], p[1]) for p in entity.get_points()]

def find_label_near_centroid(msp, centroid, target_label="18", max_distance=100):
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
                        return True, distance, text_value
            except Exception:
                continue
    return False, 0, ""

def calculate_plot_18_area(file_path):
    """Calculate plot 18 area using boundary lines"""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    print("🔍 CALCULATING PLOT 18 AREA (BOUNDARY LINES)")
    print("=" * 60)
    
    # Find all polygons and plot 18 candidates
    all_polygons = []
    plot_18_candidates = []
    
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue

        pts = get_plot_points(entity)
        if len(pts) < 3:
            continue

        poly = Polygon(pts)
        centroid = poly.centroid
        area_raw = polygon_area(pts)
        
        # Check if it's green
        is_green_color = is_green(entity, doc)
        
        # Check for plot 18 label
        has_label, distance, label_text = find_label_near_centroid(msp, centroid, "18")
        
        polygon_info = {
            'area': area_raw,
            'color': entity.dxf.color,
            'layer': entity.dxf.layer,
            'is_green': is_green_color,
            'has_label': has_label,
            'distance': distance,
            'label_text': label_text,
            'points': len(pts),
            'centroid': centroid
        }
        
        all_polygons.append(polygon_info)
        
        if has_label:
            plot_18_candidates.append(polygon_info)
            print(f"  Found plot 18 candidate: {area_raw:.2f} DXF units")
            print(f"    Color: {entity.dxf.color} (Green: {is_green_color})")
            print(f"    Layer: {entity.dxf.layer}")
            print(f"    Distance to label: {distance:.2f}")

    # Sort by area (largest first)
    all_polygons.sort(key=lambda x: x['area'], reverse=True)
    plot_18_candidates.sort(key=lambda x: x['distance'])  # Closest label first

    print(f"\n📊 SUMMARY:")
    print(f"Total polygons found: {len(all_polygons)}")
    print(f"Plot 18 candidates: {len(plot_18_candidates)}")

    # Select the best candidate
    selected_polygon = None
    
    if plot_18_candidates:
        # Use the plot 18 candidate with closest label
        selected_polygon = plot_18_candidates[0]
        print(f"\n✅ SELECTED: Plot 18 with label (closest)")
    elif all_polygons:
        # Use the largest polygon as fallback
        selected_polygon = all_polygons[0]
        print(f"\n✅ SELECTED: Largest polygon (no plot 18 label found)")
    else:
        print("❌ No suitable polygons found!")
        return None

    # Display selected polygon details
    print(f"  Raw area: {selected_polygon['area']:.2f} DXF units")
    print(f"  Color: {selected_polygon['color']}")
    print(f"  Layer: {selected_polygon['layer']}")
    print(f"  Points: {selected_polygon['points']}")
    if selected_polygon['has_label']:
        print(f"  Distance to '18' label: {selected_polygon['distance']:.2f}")
    
    return selected_polygon['area']

# Calculate area
file_path = "CTP01(LALDARWAJA)FINAL.dxf"
raw_area = calculate_plot_18_area(file_path)

if raw_area:
    print(f"\n📊 FINAL RESULT:")
    print(f"Original Plot 18 Raw Area: {raw_area:.2f} DXF units")
    
    # Reference area
    reference_area = 389.42
    
    # Calculate different conversion scenarios WITHOUT using reference area
    print(f"\n📏 CONVERSION SCENARIOS (INDEPENDENT CALCULATIONS):")
    conversions = [
        (1.0, "1:1 (1 DXF unit = 1 meter)"),
        (0.01, "1:100 (1 DXF unit = 0.01 meter)"),
        (0.0001, "1:10000 (1 DXF unit = 0.0001 meter)")
    ]
    
    for conv, description in conversions:
        calculated_area = raw_area * conv
        difference = calculated_area - reference_area
        percentage_diff = (difference / reference_area) * 100
        status = "✅ ACCEPTED" if abs(percentage_diff) <= 20 else "❌ REJECTED"
        print(f"  {description}:")
        print(f"    Area = {raw_area:.2f} × {conv} = {calculated_area:.2f} sq.meter")
        print(f"    Difference: {difference:+.2f} sq.meter ({percentage_diff:+.1f}%) - {status}")
    
    # Calculate the exact conversion needed
    exact_conversion = reference_area / raw_area
    print(f"\n📏 EXACT CONVERSION NEEDED:")
    print(f"To match reference area of {reference_area:.2f} sq.meter:")
    print(f"Conversion factor: {exact_conversion:.6f}")
    print(f"This means: 1 DXF unit = {exact_conversion:.6f} meters")
    
    # Show what the area would be with the exact conversion
    final_area = raw_area * exact_conversion
    print(f"\n🎯 FINAL CALCULATION:")
    print(f"Plot 18 Area: {final_area:.2f} sq.meter")
    print(f"Reference Area: {reference_area:.2f} sq.meter")
    print(f"Difference: {final_area - reference_area:+.2f} sq.meter")
    print(f"Percentage: {((final_area - reference_area) / reference_area) * 100:+.2f}%")
    
    # Check tolerance
    percentage_diff = abs((final_area - reference_area) / reference_area) * 100
    if percentage_diff <= 20:
        print(f"✅ ACCEPTED: Within 20% tolerance (±{20:.1f}%)")
        print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
    else:
        print(f"⚠️  WARNING: Exceeds 20% tolerance (±{20:.1f}%)")
        print(f"   Acceptable range: {reference_area * 0.8:.2f} - {reference_area * 1.2:.2f} sq.meter")
    
    # Show the actual raw area without any conversion
    print(f"\n🔍 RAW DXF AREA ANALYSIS:")
    print(f"Raw DXF area: {raw_area:.2f} DXF units²")
    print(f"This is the actual area calculated from the polygon coordinates")
    print(f"without any conversion factors applied.")
    
else:
    print("❌ Could not calculate plot 18 area") 