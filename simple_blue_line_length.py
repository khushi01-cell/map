import ezdxf
import math

def calculate_distance(point1, point2):
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def find_longest_blue_line(dxf_file_path):
    try:
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        
        blue_lines = []
        
        for entity in msp:
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                start_point = (start.x, start.y)
                end_point = (end.x, end.y)
                
                length = calculate_distance(start_point, end_point)
                
                # Check if it's a blue line (color 5 or layer contains 'blue')
                if getattr(entity.dxf, 'color', 'BYLAYER') == 5 or 'blue' in entity.dxf.layer.lower():
                    blue_lines.append(length)
                    
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.get_points())
                if len(points) > 1:
                    total_length = 0
                    for i in range(len(points) - 1):
                        total_length += calculate_distance(points[i], points[i + 1])
                    
                    if getattr(entity.dxf, 'color', 'BYLAYER') == 5 or 'blue' in entity.dxf.layer.lower():
                        blue_lines.append(total_length)
        
        if blue_lines:
            longest = max(blue_lines)
            print(f"{longest:.2f} m")
        else:
            print("No blue lines found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_longest_blue_line("CTP01(LALDARWAJA)FINAL.dxf") 