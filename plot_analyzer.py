import ezdxf
import numpy as np
from typing import Dict, List, Tuple

class PlotAnalyzer:
    def __init__(self, dxf_file_path: str):
        self.dxf_file_path = dxf_file_path
        self.doc = None
        self.msp = None
        self.scale_factor = 20.0  # 1CM = 20M conversion factor
        self.ORIGINAL_COLOR = 3  # Green for original plots
        self.FINAL_COLOR = 1     # Red for final plots
        self.load_dxf_file()
    
    def load_dxf_file(self):
        try:
            self.doc = ezdxf.readfile(self.dxf_file_path)
            self.msp = self.doc.modelspace()
        except Exception as e:
            print(f"Error loading DXF file: {e}")
            raise
    
    def _get_entity_center(self, entity) -> Tuple[float, float]:
        """Get the center point of an entity."""
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                points = []
                if hasattr(entity, 'get_points'):
                    points = list(entity.get_points())
                elif hasattr(entity, 'vertices'):
                    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                
                if points:
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
                    
            elif entity.dxftype() == 'CIRCLE':
                return (entity.dxf.center.x, entity.dxf.center.y)
                
            elif entity.dxftype() == 'INSERT':
                return (entity.dxf.insert.x, entity.dxf.insert.y)
                
        except Exception:
            pass
        
        return (0.0, 0.0)
    
    def get_original_plots(self) -> Dict:
        """Extract only the original plots mentioned in the PDF"""
        original_plot_numbers = [
            "1", "2", "2/A", "3", "4", "5", "5/A", "6", "35", "24", "7", "8", "9", "10", 
            "11", "11/A", "12", "13", "14", "15", "15/A", "16", "16/A", "17", "17/A", 
            "18", "19", "20", "21", "21/A", "21/B", "22", "23", "24", "25", "26", "27", 
            "28", "28/A", "28/B", "29", "29/A", "30", "31", "31/A", "32", "33", "33/A", 
            "34", "34/A", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"
        ]
        
        return self._extract_plots_by_numbers(original_plot_numbers, self.ORIGINAL_COLOR, "Original")
    
    def get_final_plots(self) -> Dict:
        """Extract only the final plots mentioned in the PDF"""
        final_plot_numbers = [
            "1", "2", "NIL", "3", "4", "NIL", "5", "31", "34", "6", "7", "8", "8/A", "9", "10", 
            "11", "12", "12/A", "NIL", "14", "15", "15/A", "16", "17", "18", "19", "19/A", "19/B", 
            "20", "21", "22", "22/A", "23", "24", "NIL", "25", "32", "25/A", "26", "27", "27/A", 
            "28", "29", "29/A", "30", "30/A", "NIL", "NIL", "NIL", "36", "37", "NIL", "NIL", "NIL", 
            "NIL", "13", "33", "35", "38", "39"
        ]
        
        return self._extract_plots_by_numbers(final_plot_numbers, self.FINAL_COLOR, "Final")
    
    def _extract_plots_by_numbers(self, plot_numbers: List[str], color: int, plot_type: str) -> Dict:
        """Helper function to extract plots by their numbers"""
        entities = []
        total_area = 0.0
        total_perimeter = 0.0
        
        # Find all entities with the specified color
        for entity in self.msp:
            if getattr(entity.dxf, 'color', 7) == color:
                entity_type = entity.dxftype()
                if entity_type in ['LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'RECTANGLE']:
                    area, perimeter = self._calculate_entity_area_perimeter(entity)
                    total_area += area
                    total_perimeter += perimeter
                    
                    entities.append({
                        'type': entity_type,
                        'layer': entity.dxf.layer,
                        'area': area,
                        'perimeter': perimeter,
                        'center': self._get_entity_center(entity),
                        'entity': entity
                    })
        
        # Assign plot numbers to entities
        for i, entity_data in enumerate(entities):
            if i < len(plot_numbers):
                entity_data['plot_number'] = plot_numbers[i]
            else:
                entity_data['plot_number'] = f"UNASSIGNED_{i+1}"
        
        # Convert to square meters
        area_sq_meters = self.convert_to_square_meters(total_area)
        perimeter_meters = self.convert_to_meters(total_perimeter)
        
        return {
            'plot_type': plot_type,
            'total_entities': len(entities),
            'total_area_sq_meters': area_sq_meters,
            'total_perimeter_meters': perimeter_meters,
            'plot_numbers': [p for p in plot_numbers if p != "NIL"],
            'entities': entities
        }
    
    def _calculate_entity_area_perimeter(self, entity) -> Tuple[float, float]:
        """Calculate area and perimeter of an entity"""
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                return self._calculate_polygon_area_perimeter(entity)
            elif entity.dxftype() == 'CIRCLE':
                radius = entity.dxf.radius
                area = np.pi * radius * radius
                perimeter = 2 * np.pi * radius
                return area, perimeter
            elif entity.dxftype() == 'RECTANGLE':
                return self._calculate_polygon_area_perimeter(entity)
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0
    
    def _calculate_polygon_area_perimeter(self, entity) -> Tuple[float, float]:
        """Calculate area and perimeter of a polygon"""
        try:
            points = []
            if hasattr(entity, 'get_points'):
                points = list(entity.get_points())
            elif hasattr(entity, 'vertices'):
                points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            
            if len(points) < 3:
                return 0.0, 0.0
            
            area = 0.0
            perimeter = 0.0
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
                dx = points[j][0] - points[i][0]
                dy = points[j][1] - points[i][1]
                perimeter += np.sqrt(dx*dx + dy*dy)
            
            return abs(area) / 2.0, perimeter
        except Exception:
            return 0.0, 0.0
    
    def convert_to_square_meters(self, area_raw: float) -> float:
        """Convert raw DXF area to square meters"""
        return area_raw * (self.scale_factor ** 2)
    
    def convert_to_meters(self, distance_raw: float) -> float:
        """Convert raw DXF distance to meters"""
        return distance_raw * self.scale_factor
    
    def generate_report(self):
        """Generate a clean report of the plots mentioned in the PDF"""
        original = self.get_original_plots()
        final = self.get_final_plots()
        
        print("\nORIGINAL PLOTS:")
        print(f"Total plots: {original['total_entities']}")
        print(f"Total area: {original['total_area_sq_meters']:.2f} sq meters")
        print(f"Plot numbers: {', '.join(original['plot_numbers'])}")
        
        print("\nFINAL PLOTS:")
        print(f"Total plots: {final['total_entities']}")
        print(f"Total area: {final['total_area_sq_meters']:.2f} sq meters")
        print(f"Plot numbers: {', '.join(final['plot_numbers'])}")
        
        # Generate detailed table
        print("\nDETAILED PLOT INFORMATION:")
        print(f"{'Plot No.':<8} {'Type':<10} {'Area (sq m)':<12} {'Perimeter (m)':<12}")
        print("-" * 40)
        
        for plot in original['entities']:
            print(f"{plot['plot_number']:<8} {'Original':<10} "
                  f"{self.convert_to_square_meters(plot['area']):<12.2f} "
                  f"{self.convert_to_meters(plot['perimeter']):<12.2f}")
        
        for plot in final['entities']:
            if plot['plot_number'] != "NIL":
                print(f"{plot['plot_number']:<8} {'Final':<10} "
                      f"{self.convert_to_square_meters(plot['area']):<12.2f} "
                      f"{self.convert_to_meters(plot['perimeter']):<12.2f}")

def main():
    analyzer = PlotAnalyzer("CTP01(LALDARWAJA)FINAL.dxf")
    analyzer.generate_report()

if __name__ == "__main__":
    main()