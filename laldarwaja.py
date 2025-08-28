import ezdxf
import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Set


class PlotAnalyzer:
    MERGE_TOLERANCE = 0.2
    CLUSTER_DISTANCE = 10.0

    # Set your known colors for original and final (you can change to match your file)
    ORIGINAL_COLOR = 3
    FINAL_COLOR = 1

    # Or known layers, replace these with actual layer names if known
    ORIGINAL_LAYERS = {"OriginalLayerName"}  # Change accordingly
    FINAL_LAYERS = {"FinalLayerName"}        # Change accordingly

    def __init__(self, dxf_file_path: str):
        self.dxf_file_path = dxf_file_path
        self.doc = None
        self.msp = None
        self.scale_factor = 1.0
        self.load_dxf_file()
        self.auto_detect_units()

    def load_dxf_file(self):
        try:
            self.doc = ezdxf.readfile(self.dxf_file_path)
            self.msp = self.doc.modelspace()
        except Exception as e:
            print(f"Error loading DXF file: {e}")
            raise

    def auto_detect_units(self):
        units = self.doc.header.get('$INSUNITS', 0)
        unit_scale = {
            0: 1.0,
            1: 0.0254,
            2: 0.3048,
            3: 1609.344,
            4: 0.001,
            5: 0.001,
            6: 0.01,
            7: 1.0,
            8: 1000.0,
            13: 0.9144,
        }
        self.scale_factor = unit_scale.get(units, 1.0)
        print(f"[INFO] DXF units code {units}, using scale factor {self.scale_factor}")

    def dump_entities_info(self):
        print("DXF Entities in Modelspace:")
        for entity in self.msp:
            try:
                etype = entity.dxftype()
                layer = getattr(entity.dxf, "layer", "N/A")
                color = getattr(entity.dxf, "color", "N/A")
                print(f"Type: {etype}, Layer: {layer}, Color: {color}")
            except Exception:
                continue

    def _close_polyline(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(points) > 2 and points[0] != points[-1]:
            points.append(points[0])
        return points

    def _calculate_polygon_area_perimeter(self, entity) -> Tuple[float, float]:
        points = list(entity.get_points()) if hasattr(entity, 'get_points') else []
        points = self._close_polyline(points)
        if len(points) < 3:
            return 0.0, 0.0
        area = 0.0
        perimeter = 0.0
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            area += x1 * y2 - x2 * y1
            perimeter += math.dist(points[i], points[i + 1])
        return abs(area) / 2.0, perimeter

    def _calculate_entity_area_perimeter(self, entity) -> Tuple[float, float]:
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                return self._calculate_polygon_area_perimeter(entity)
            elif entity.dxftype() == 'CIRCLE':
                r = entity.dxf.radius
                area = math.pi * r * r
                perimeter = 2 * math.pi * r
                return area, perimeter
        except Exception:
            pass
        return 0.0, 0.0

    def convert_to_square_meters(self, area_raw: float) -> float:
        return area_raw * (self.scale_factor ** 2)

    def convert_to_square_yards(self, area_sq_meters: float) -> float:
        return area_sq_meters * 1.19599

    def convert_to_meters(self, distance_raw: float) -> float:
        return distance_raw * self.scale_factor

    def _extract_plots_by_layer(self, plot_numbers: List[str], layers: Set[str], plot_type: str) -> Dict:
        entities = []
        total_area = 0.0
        total_perimeter = 0.0
        for entity in self.msp:
            ent_layer = getattr(entity.dxf, "layer", None)
            if ent_layer in layers and entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE', 'CIRCLE']:
                area, perimeter = self._calculate_entity_area_perimeter(entity)
                total_area += area
                total_perimeter += perimeter
                entities.append({
                    'type': entity.dxftype(),
                    'layer': ent_layer,
                    'area': area,
                    'perimeter': perimeter,
                    'plot_number': None,
                    'entity': entity,
                })
        for i, ent in enumerate(entities):
            ent['plot_number'] = plot_numbers[i] if i < len(plot_numbers) else f"UNASSIGNED_{i+1}"
        return {
            'plot_type': plot_type,
            'total_entities': len(entities),
            'total_area_sq_meters': self.convert_to_square_meters(total_area),
            'total_perimeter_meters': self.convert_to_meters(total_perimeter),
            'plot_numbers': [p for p in plot_numbers if p != "NIL"],
            'entities': entities,
        }

    def get_original_plots(self) -> Dict:
        original_plot_numbers = [
            "1", "2", "2/A", "3", "4", "5", "5/A", "6", "35", "24", "7", "8", "9", "10",
            "11", "11/A", "12", "13", "14", "15", "15/A", "16", "16/A", "17", "17/A",
            "18", "19", "20", "21", "21/A", "21/B", "22", "23", "24", "25", "26", "27",
            "28", "28/A", "28/B", "29", "29/A", "30", "31", "31/A", "32", "33", "33/A",
            "34", "34/A", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"
        ]
        return self._extract_plots_by_layer(original_plot_numbers, self.ORIGINAL_LAYERS, "Original")

    def get_final_plots(self) -> Dict:
        final_plot_numbers = [
            "1", "2", "NIL", "3", "4", "NIL", "5", "31", "34", "6", "7", "8", "8/A", "9", "10",
            "11", "12", "12/A", "NIL", "14", "15", "15/A", "16", "17", "18", "19", "19/A", "19/B",
            "20", "21", "22", "22/A", "23", "24", "NIL", "25", "32", "25/A", "26", "27", "27/A",
            "28", "29", "29/A", "30", "30/A", "NIL", "NIL", "NIL", "36", "37", "NIL", "NIL", "NIL",
            "NIL", "13", "33", "35", "38", "39"
        ]
        return self._extract_plots_by_layer(final_plot_numbers, self.FINAL_LAYERS, "Final")

    def run(self):
        # Run this method for debugging before extraction
        self.dump_entities_info()

        original = self.get_original_plots()
        final = self.get_final_plots()

        print(f"Original total plots: {original['total_entities']}, total area (m²): {original['total_area_sq_meters']:.2f}")
        print(f"Final total plots: {final['total_entities']}, total area (m²): {final['total_area_sq_meters']:.2f}")

        # Further processing like validation, reports can be added here


def main():
    dxf_file_path = "CTP01(LALDARWAJA)FINAL.dxf"  # Update with your DXF file path
    analyzer = PlotAnalyzer(dxf_file_path)

    # Adjust these sets as per the layers you find in the DXF file (from dump_entities_info output)
    analyzer.ORIGINAL_LAYERS = {"YourOriginalPlotLayerName"}
    analyzer.FINAL_LAYERS = {"YourFinalPlotLayerName"}

    analyzer.run()


if __name__ == "__main__":
    main()
