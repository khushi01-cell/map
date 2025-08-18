import ezdxf
import numpy as np
from typing import Dict, List, Tuple

class PlotAnalyzer:
    def __init__(self, dxf_file_path: str):
        self.dxf_file_path = dxf_file_path
        self.doc = None
        self.msp = None
        self.scale_factor = 0.001  # Start with 1mm = 0.001m (most likely for DXF files)
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
    
    def convert_to_square_yards(self, area_sq_meters: float) -> float:
        """Convert square meters to square yards"""
        return area_sq_meters * 1.19599
    
    def generate_report(self):
        """Generate a clean report of the plots mentioned in the PDF"""
        original = self.get_original_plots()
        final = self.get_final_plots()
        
        print("\nORIGINAL PLOTS:")
        print(f"Total plots: {original['total_entities']}")
        print(f"Total area: {original['total_area_sq_meters']:.2f} sq meters")
        print(f"Total area: {self.convert_to_square_yards(original['total_area_sq_meters']):.2f} sq yards")
        print(f"Plot numbers: {', '.join(original['plot_numbers'])}")
        
        print("\nFINAL PLOTS:")
        print(f"Total plots: {final['total_entities']}")
        print(f"Total area: {final['total_area_sq_meters']:.2f} sq meters")
        print(f"Total area: {self.convert_to_square_yards(final['total_area_sq_meters']):.2f} sq yards")
        print(f"Plot numbers: {', '.join(final['plot_numbers'])}")
        
        # Generate detailed table with both sq meters and sq yards
        print("\nDETAILED PLOT INFORMATION:")
        print(f"{'Plot No.':<8} {'Type':<10} {'Area (sq m)':<12} {'Area (sq yd)':<12} {'Perimeter (m)':<12}")
        print("-" * 60)
        
        for plot in original['entities']:
            area_sq_m = self.convert_to_square_meters(plot['area'])
            area_sq_yd = self.convert_to_square_yards(area_sq_m)
            print(f"{plot['plot_number']:<8} {'Original':<10} "
                  f"{area_sq_m:<12.2f} "
                  f"{area_sq_yd:<12.2f} "
                  f"{self.convert_to_meters(plot['perimeter']):<12.2f}")
        
        for plot in final['entities']:
            if plot['plot_number'] != "NIL":
                area_sq_m = self.convert_to_square_meters(plot['area'])
                area_sq_yd = self.convert_to_square_yards(area_sq_m)
                print(f"{plot['plot_number']:<8} {'Final':<10} "
                      f"{area_sq_m:<12.2f} "
                      f"{area_sq_yd:<12.2f} "
                      f"{self.convert_to_meters(plot['perimeter']):<12.2f}")

    def calculate_pending_area(self):
        """Calculate pending area between original and final plots"""
        original = self.get_original_plots()
        final = self.get_final_plots()
        
        # Calculate total areas
        original_total = original['total_area_sq_meters']
        final_total = final['total_area_sq_meters']
        
        # Calculate pending area (difference)
        pending_area = original_total - final_total
        
        # Calculate percentage change
        if original_total > 0:
            percentage_change = ((final_total - original_total) / original_total) * 100
        else:
            percentage_change = 0
        
        # Convert to square yards
        original_total_sq_yds = self.convert_to_square_yards(original_total)
        final_total_sq_yds = self.convert_to_square_yards(final_total)
        pending_area_sq_yds = self.convert_to_square_yards(pending_area)
        
        print("\n=== PENDING AREA ANALYSIS ===")
        print("IN SQUARE METERS:")
        print(f"Original plots total area: {original_total:.2f} sq meters")
        print(f"Final plots total area: {final_total:.2f} sq meters")
        print(f"Pending area (difference): {pending_area:.2f} sq meters")
        print(f"Percentage change: {percentage_change:.2f}%")
        
        print("\nIN SQUARE YARDS:")
        print(f"Original plots total area: {original_total_sq_yds:.2f} sq yards")
        print(f"Final plots total area: {final_total_sq_yds:.2f} sq yards")
        print(f"Pending area (difference): {pending_area_sq_yds:.2f} sq yards")
        
        if pending_area > 0:
            print("Status: Area REDUCED (final < original)")
            print(f"Area was reduced by {abs(percentage_change):.2f}%")
        elif pending_area < 0:
            print("Status: Area INCREASED (final > original)")
            print(f"Area was increased by {percentage_change:.2f}%")
        else:
            print("Status: No change in total area")
        
        return {
            'original_total': original_total,
            'final_total': final_total,
            'pending_area': pending_area,
            'percentage_change': percentage_change,
            'original_total_sq_yds': original_total_sq_yds,
            'final_total_sq_yds': final_total_sq_yds,
            'pending_area_sq_yds': pending_area_sq_yds
        }

    def find_correct_scale_factor(self):
        """Automatically find the correct scale factor by comparing with reference areas"""
        # Reference areas are in SQUARE YARDS - convert to square meters first
        reference_areas_sq_yds = [
            389, 2925, 3286, 38, 638, 1745, 72, 21780, 16443, 24, 4284, 768, 95, 9054, 1302, 27395, 47080, 903, 2901, 2728, 2567, 2162, 572, 372, 5673, 1138, 466, 185, 207, 1264, 2613, 7502, 22119, 16129, 54519, 30090, 41140, 465, 43368, 1765, 16950, 13688, 700, 1082, 14472, 48, 10005, 5083, 70, 885, 889, 1969, 334, 124, 42, 22, 178, 228, 79, 44
        ]
        
        # Convert reference areas from square yards to square meters
        reference_areas_sq_m = [area / 1.19599 for area in reference_areas_sq_yds]
        
        original = self.get_original_plots()
        
        print("\n=== FINDING CORRECT SCALE FACTOR ===")
        print("Reference areas converted from sq yards to sq meters")
        print("Comparing calculated areas with reference areas...")
        
        # Calculate scale factors for each plot
        scale_factors = []
        for i, plot in enumerate(original['entities']):
            if i < len(reference_areas_sq_m):
                ref_area_sq_m = reference_areas_sq_m[i]
                ref_area_sq_yd = reference_areas_sq_yds[i]
                raw_area = plot['area']  # Raw DXF area
                
                if ref_area_sq_m > 0 and raw_area > 0:
                    # CORRECT: Scale factor = √(reference_area_sq_m / raw_area_dxf)
                    scale_factor = (ref_area_sq_m / raw_area) ** 0.5
                    scale_factors.append(scale_factor)
                    
                    print(f"Plot {plot['plot_number']}: Ref={ref_area_sq_yd} sq yd ({ref_area_sq_m:.2f} sq m), Raw={raw_area:.6f}, Scale={scale_factor:.6f}")
        
        if scale_factors:
            # Use median scale factor to avoid outliers
            scale_factors.sort()
            median_scale = scale_factors[len(scale_factors)//2]
            mean_scale = sum(scale_factors) / len(scale_factors)
            
            print(f"\nCalculated scale factors:")
            print(f"Median scale factor: {median_scale:.6f}")
            print(f"Mean scale factor: {mean_scale:.6f}")
            print(f"Current scale factor: {self.scale_factor}")
            
            # Update the scale factor
            self.scale_factor = median_scale
            print(f"Updated scale factor to: {self.scale_factor}")
            
            return median_scale
        else:
            print("No valid scale factors found!")
            return None
    
    def validate_original_plots(self):
        """Compare calculated areas with reference areas and validate if within 20% difference"""
        # Reference areas are in SQUARE YARDS
        reference_areas_sq_yds = [
            389, 2925, 3286, 38, 638, 1745, 72, 21780, 16443, 24, 4284, 768, 95, 9054, 1302, 27395, 47080, 903, 2901, 2728, 2567, 2162, 572, 372, 5673, 1138, 466, 185, 207, 1264, 2613, 7502, 22119, 16129, 54519, 30090, 41140, 465, 43368, 1765, 16950, 13688, 700, 1082, 14472, 48, 10005, 5083, 70, 885, 889, 1969, 334, 124, 42, 22, 178, 228, 79, 44
        ]
        
        original = self.get_original_plots()
        
        print("\n=== ORIGINAL PLOTS VALIDATION (20% Threshold) ===")
        print(f"{'Plot No.':<8} {'Ref (sq yd)':<12} {'Calc (sq m)':<12} {'Calc (sq yd)':<12} {'Diff %':<10} {'Status':<10}")
        print("-" * 70)
        
        valid_plots = []
        invalid_plots = []
        valid_count = 0
        invalid_count = 0
        
        for i, plot in enumerate(original['entities']):
            if i < len(reference_areas_sq_yds):
                ref_area_sq_yd = reference_areas_sq_yds[i]
                calc_area_sq_m = self.convert_to_square_meters(plot['area'])
                calc_area_sq_yd = self.convert_to_square_yards(calc_area_sq_m)
                
                # Calculate percentage difference using square yards for comparison
                if ref_area_sq_yd > 0:
                    diff_percent = abs((calc_area_sq_yd - ref_area_sq_yd) / ref_area_sq_yd) * 100
                else:
                    diff_percent = 100.0
                
                # Determine if valid (within 20% threshold)
                if diff_percent <= 20.0:
                    status = "VALID"
                    valid_count += 1
                    valid_plots.append({
                        'plot_number': plot['plot_number'],
                        'ref_area': ref_area_sq_yd,
                        'calc_area_sq_m': calc_area_sq_m,
                        'calc_area_sq_yd': calc_area_sq_yd,
                        'diff_percent': diff_percent
                    })
                else:
                    status = "INVALID"
                    invalid_count += 1
                    invalid_plots.append({
                        'plot_number': plot['plot_number'],
                        'ref_area': ref_area_sq_yd,
                        'calc_area_sq_m': calc_area_sq_m,
                        'calc_area_sq_yd': calc_area_sq_yd,
                        'diff_percent': diff_percent
                    })
                
                print(f"{plot['plot_number']:<8} {ref_area_sq_yd:<12.0f} {calc_area_sq_m:<12.2f} {calc_area_sq_yd:<12.2f} {diff_percent:<10.2f} {status:<10}")
        
        print("-" * 70)
        print(f"Total plots compared: {len(reference_areas_sq_yds)}")
        print(f"Valid plots (≤20% diff): {valid_count}")
        print(f"Invalid plots (>20% diff): {invalid_count}")
        print(f"Validation rate: {(valid_count/len(reference_areas_sq_yds)*100):.1f}%")
        
        # Show valid plots summary
        print("\n=== VALID ORIGINAL PLOTS (≤20% difference) ===")
        if valid_plots:
            for plot in valid_plots:
                print(f"Plot {plot['plot_number']}: Ref={plot['ref_area']} sq yd, Calc={plot['calc_area_sq_yd']:.2f} sq yd, Diff={plot['diff_percent']:.2f}%")
        else:
            print("No valid plots found!")
        
        # Show invalid plots summary
        print("\n=== INVALID ORIGINAL PLOTS (>20% difference) ===")
        if invalid_plots:
            for plot in invalid_plots:
                print(f"Plot {plot['plot_number']}: Ref={plot['ref_area']} sq yd, Calc={plot['calc_area_sq_yd']:.2f} sq yd, Diff={plot['diff_percent']:.2f}%")
        else:
            print("No invalid plots found!")
        
        return {
            'total_plots': len(reference_areas_sq_yds),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'validation_rate': valid_count/len(reference_areas_sq_yds)*100,
            'valid_plots': valid_plots,
            'invalid_plots': invalid_plots
        }

    def validate_final_plots(self):
        """Compare calculated areas with reference areas for final plots and validate if within 20% difference"""
        # Reference areas for final plots in SQUARE YARDS
        reference_areas_sq_yds = [
            480, 3212, 462, 1751, 10921, 4435, 30981, 4971, 8360, 14495, 42961, 944, 2969, 2808, 2674, 2205, 372, 5673, 9440, 466, 5496, 88184, 132786, 698, 5824, 22107, 49629, 27973, 43414, 37553, 2054, 16009, 13638, 700, 1082, 14466, 65, 10013, 6804, 124, 67, 565, 4083, 10316, 22, 236
        ]
        
        final = self.get_final_plots()
        
        print("\n=== FINAL PLOTS VALIDATION (20% Threshold) ===")
        print(f"{'Plot No.':<8} {'Ref (sq yd)':<12} {'Calc (sq m)':<12} {'Calc (sq yd)':<12} {'Diff %':<10} {'Status':<10}")
        print("-" * 70)
        
        valid_plots = []
        invalid_plots = []
        valid_count = 0
        invalid_count = 0
        
        for i, plot in enumerate(final['entities']):
            if plot['plot_number'] != "NIL" and i < len(reference_areas_sq_yds):
                ref_area_sq_yd = reference_areas_sq_yds[i]
                calc_area_sq_m = self.convert_to_square_meters(plot['area'])
                calc_area_sq_yd = self.convert_to_square_yards(calc_area_sq_m)
                
                # Calculate percentage difference using square yards for comparison
                if ref_area_sq_yd > 0:
                    diff_percent = abs((calc_area_sq_yd - ref_area_sq_yd) / ref_area_sq_yd) * 100
                else:
                    diff_percent = 100.0
                
                # Determine if valid (within 20% threshold)
                if diff_percent <= 20.0:
                    status = "VALID"
                    valid_count += 1
                    valid_plots.append({
                        'plot_number': plot['plot_number'],
                        'ref_area': ref_area_sq_yd,
                        'calc_area_sq_m': calc_area_sq_m,
                        'calc_area_sq_yd': calc_area_sq_yd,
                        'diff_percent': diff_percent
                    })
                else:
                    status = "INVALID"
                    invalid_count += 1
                    invalid_plots.append({
                        'plot_number': plot['plot_number'],
                        'ref_area': ref_area_sq_yd,
                        'calc_area_sq_m': calc_area_sq_m,
                        'calc_area_sq_yd': calc_area_sq_yd,
                        'diff_percent': diff_percent
                    })
                
                print(f"{plot['plot_number']:<8} {ref_area_sq_yd:<12.0f} {calc_area_sq_m:<12.2f} {calc_area_sq_yd:<12.2f} {diff_percent:<10.2f} {status:<10}")
        
        print("-" * 70)
        print(f"Total plots compared: {len(reference_areas_sq_yds)}")
        print(f"Valid plots (≤20% diff): {valid_count}")
        print(f"Invalid plots (>20% diff): {invalid_count}")
        print(f"Validation rate: {(valid_count/len(reference_areas_sq_yds)*100):.1f}%")
        
        # Show valid plots summary
        print("\n=== VALID FINAL PLOTS (≤20% difference) ===")
        if valid_plots:
            for plot in valid_plots:
                print(f"Plot {plot['plot_number']}: Ref={plot['ref_area']} sq yd, Calc={plot['calc_area_sq_yd']:.2f} sq yd, Diff={plot['diff_percent']:.2f}%")
        else:
            print("No valid plots found!")
        
        # Show invalid plots summary
        print("\n=== INVALID FINAL PLOTS (>20% difference) ===")
        if invalid_plots:
            for plot in invalid_plots:
                print(f"Plot {plot['plot_number']}: Ref={plot['ref_area']} sq yd, Calc={plot['calc_area_sq_yd']:.2f} sq yd, Diff={plot['diff_percent']:.2f}%")
        else:
            print("No invalid plots found!")
        
        return {
            'total_plots': len(reference_areas_sq_yds),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'validation_rate': valid_count/len(reference_areas_sq_yds)*100,
            'valid_plots': valid_plots,
            'invalid_plots': invalid_plots
        }

def main():
    analyzer = PlotAnalyzer("CTP01(LALDARWAJA)FINAL.dxf")
    
    # First find the correct scale factor
    analyzer.find_correct_scale_factor()
    
    # Then generate reports with correct scale
    analyzer.generate_report()
    analyzer.calculate_pending_area()
    analyzer.validate_original_plots()
    analyzer.validate_final_plots()

if __name__ == "__main__":
    main()