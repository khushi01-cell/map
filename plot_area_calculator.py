import ezdxf
import math

def calculate_polygon_area(points):
    """Calculate area of a polygon using shoelace formula"""
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0

def find_green_boundaries(dxf_file_path):
    """Find green line boundaries in the DXF file"""
    try:
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        green_boundaries = []
        
        for entity in msp:
            # Check if it's a green line (color 3 or layer contains 'green')
            is_green = False
            if hasattr(entity.dxf, 'color'):
                if entity.dxf.color == 3:  # Green color
                    is_green = True
            if 'green' in entity.dxf.layer.lower():
                is_green = True
                
            if is_green:
                if entity.dxftype() == 'LWPOLYLINE':
                    points = list(entity.get_points())
                    if len(points) > 2 and entity.closed:
                        # Convert to list of tuples
                        point_tuples = [(p[0], p[1]) for p in points]
                        area = calculate_polygon_area(point_tuples)
                        green_boundaries.append({
                            'type': 'polyline',
                            'layer': entity.dxf.layer,
                            'area': area,
                            'points': point_tuples,
                            'color': getattr(entity.dxf, 'color', 'BYLAYER')
                        })
                        
                elif entity.dxftype() == 'POLYLINE':
                    points = []
                    for vertex in entity.vertices:
                        points.append((vertex.dxf.location.x, vertex.dxf.location.y))
                    
                    if len(points) > 2 and entity.is_closed:
                        area = calculate_polygon_area(points)
                        green_boundaries.append({
                            'type': 'polyline',
                            'layer': entity.dxf.layer,
                            'area': area,
                            'points': points,
                            'color': getattr(entity.dxf, 'color', 'BYLAYER')
                        })
        
        return green_boundaries
        
    except Exception as e:
        print(f"Error reading DXF file: {e}")
        return []

def main():
    dxf_file = "CTP01(LALDARWAJA)FINAL.dxf"
    
    print("Calculating area of plot 34/A original boundaries (green lines)...")
    print("=" * 60)
    
    # Find green boundaries
    green_boundaries = find_green_boundaries(dxf_file)
    
    if not green_boundaries:
        print("No green line boundaries found in the DXF file.")
        return
    
    print(f"Found {len(green_boundaries)} green boundary areas:")
    print()
    
    total_area = 0
    for i, boundary in enumerate(green_boundaries, 1):
        area_sqm = boundary['area']  # Assuming units are in meters
        print(f"Boundary {i}:")
        print(f"  Layer: {boundary['layer']}")
        print(f"  Type: {boundary['type']}")
        print(f"  Color: {boundary['color']}")
        print(f"  Area: {area_sqm:.4f} square meters")
        print(f"  Area: {area_sqm:.2f} m²")
        print()
        total_area += area_sqm
    
    print("=" * 60)
    print(f"Total area of green boundaries: {total_area:.4f} square meters")
    print(f"Total area of green boundaries: {total_area:.2f} m²")
    
    # Save results
    with open('plot_34A_area_results.txt', 'w') as f:
        f.write("Plot 34/A Original Boundaries Area Calculation\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"File: {dxf_file}\n")
        f.write(f"Green boundaries found: {len(green_boundaries)}\n\n")
        
        for i, boundary in enumerate(green_boundaries, 1):
            f.write(f"Boundary {i}:\n")
            f.write(f"  Layer: {boundary['layer']}\n")
            f.write(f"  Area: {boundary['area']:.4f} square meters\n")
            f.write(f"  Area: {boundary['area']:.2f} m²\n\n")
        
        f.write(f"Total Area: {total_area:.4f} square meters\n")
        f.write(f"Total Area: {total_area:.2f} m²\n")
    
    print("Results saved to 'plot_34A_area_results.txt'")

if __name__ == "__main__":
    main() 