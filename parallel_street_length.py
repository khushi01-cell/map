import ezdxf
import math
import numpy as np

DXF_PATH = 'CTP01(LALDARWAJA)FINAL.dxf'
RED_COLOR_CODE = 1  # Red color code in DXF

def calculate_line_length(start_point, end_point):
    """Calculate the length of a line segment"""
    dx = end_point[0] - start_point[0]
    dy = end_point[1] - start_point[1]
    return math.sqrt(dx*dx + dy*dy)

def find_parallel_lines(lines, tolerance=0.1):
    """Find pairs of parallel lines"""
    parallel_pairs = []
    
    for i, line1 in enumerate(lines):
        for j, line2 in enumerate(lines[i+1:], i+1):
            # Calculate direction vectors
            dx1 = line1['end'][0] - line1['start'][0]
            dy1 = line1['end'][1] - line1['start'][1]
            length1 = math.sqrt(dx1*dx1 + dy1*dy1)
            
            dx2 = line2['end'][0] - line2['start'][0]
            dy2 = line2['end'][1] - line2['start'][1]
            length2 = math.sqrt(dx2*dx2 + dy2*dy2)
            
            if length1 > 0 and length2 > 0:
                # Normalize direction vectors
                dir1 = (dx1/length1, dy1/length1)
                dir2 = (dx2/length2, dy2/length2)
                
                # Check if lines are parallel (dot product close to 1 or -1)
                dot_product = dir1[0]*dir2[0] + dir1[1]*dir2[1]
                if abs(dot_product) > 0.95:  # Very close to parallel
                    # Calculate distance between lines
                    # Use point-to-line distance formula
                    p1 = line1['start']
                    p2 = line2['start']
                    
                    # Distance between parallel lines
                    # |(p2-p1) · n| where n is normal vector
                    normal = (-dir1[1], dir1[0])  # Perpendicular to direction
                    distance = abs((p2[0]-p1[0])*normal[0] + (p2[1]-p1[1])*normal[1])
                    
                    parallel_pairs.append({
                        'line1': line1,
                        'line2': line2,
                        'distance': distance,
                        'length1': length1,
                        'length2': length2,
                        'avg_length': (length1 + length2) / 2
                    })
    
    return parallel_pairs

def main():
    doc = ezdxf.readfile(DXF_PATH)
    msp = doc.modelspace()
    
    # Collect all red lines
    red_lines = []
    
    print("Finding parallel red lines (thin street boundaries)...")
    print("=" * 60)
    
    # Find all LINE entities with red color
    for e in msp.query('LINE'):
        if e.dxf.color == RED_COLOR_CODE:
            start_point = (e.dxf.start.x, e.dxf.start.y)
            end_point = (e.dxf.end.x, e.dxf.end.y)
            length = calculate_line_length(start_point, end_point)
            
            red_lines.append({
                'start': start_point,
                'end': end_point,
                'length': length,
                'handle': e.dxf.handle,
                'type': 'line'
            })
    
    # Find all LWPOLYLINE entities with red color
    for e in msp.query('LWPOLYLINE'):
        if e.dxf.color == RED_COLOR_CODE:
            points = e.get_points('xy')
            if len(points) >= 2:
                # Calculate total length of polyline segments
                polyline_length = 0.0
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    segment_length = calculate_line_length(start_point, end_point)
                    polyline_length += segment_length
                
                red_lines.append({
                    'start': points[0],
                    'end': points[-1],
                    'length': polyline_length,
                    'handle': e.dxf.handle,
                    'type': 'polyline',
                    'segments': len(points) - 1
                })
    
    print(f"Found {len(red_lines)} red lines")
    
    if len(red_lines) < 2:
        print("Not enough red lines to find parallel pairs!")
        return
    
    # Find parallel line pairs
    parallel_pairs = find_parallel_lines(red_lines)
    
    if not parallel_pairs:
        print("No parallel red lines found!")
        return
    
    print(f"Found {len(parallel_pairs)} parallel line pairs")
    
    # Find the longest parallel pair (main street)
    longest_pair = max(parallel_pairs, key=lambda x: x['avg_length'])
    
    print(f"\nMain thin street (longest parallel red lines):")
    print("-" * 50)
    
    line1 = longest_pair['line1']
    line2 = longest_pair['line2']
    
    print(f"Street length: {longest_pair['avg_length']:.2f} units")
    print(f"Street width (distance between lines): {longest_pair['distance']:.2f} units")
    
    # Convert to meters
    length_meters = longest_pair['avg_length']
    width_meters = longest_pair['distance']
    
    print(f"\nMeasurements in meters:")
    print(f"  Street length: {length_meters:.2f} m")
    print(f"  Street width: {width_meters:.2f} m")
    
    # Calculate street area
    street_area_m2 = length_meters * width_meters
    print(f"  Street area: {street_area_m2:.2f} m²")
    
    # Show details of both lines
    print(f"\nLine 1 details:")
    print(f"  Start: ({line1['start'][0]:.2f}, {line1['start'][1]:.2f})")
    print(f"  End: ({line1['end'][0]:.2f}, {line1['end'][1]:.2f})")
    print(f"  Length: {line1['length']:.2f} units")
    print(f"  Handle: {line1['handle']}")
    
    print(f"\nLine 2 details:")
    print(f"  Start: ({line2['start'][0]:.2f}, {line2['start'][1]:.2f})")
    print(f"  End: ({line2['end'][0]:.2f}, {line2['end'][1]:.2f})")
    print(f"  Length: {line2['length']:.2f} units")
    print(f"  Handle: {line2['handle']}")

if __name__ == '__main__':
    main() 