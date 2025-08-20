import ezdxf
import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Set


class PlotAnalyzer:
    # ---------- Road Analysis Settings (you can change these) ----------
    MERGE_TOLERANCE = 0.2         # drawing units
    CLUSTER_DISTANCE = 10.0       # drawing units
    ROAD_LAYERS: Set[str] = {"0", "1F8CE10"}  # layers considered as roads
    PARALLEL_ANGLE_TOL = 60       # degrees

    def __init__(self, dxf_file_path: str):
        self.dxf_file_path = dxf_file_path
        self.doc = None
        self.msp = None
        # Start with 1mm = 0.001 m (common), then auto-adjust via find_correct_scale_factor()
        self.scale_factor = 0.001

        # Colors you used
        self.ORIGINAL_COLOR = 3  # Green
        self.FINAL_COLOR = 1     # Red

        self.load_dxf_file()

    # ---------- DXF Loading ----------
    def load_dxf_file(self):
        try:
            self.doc = ezdxf.readfile(self.dxf_file_path)
            self.msp = self.doc.modelspace()
        except Exception as e:
            print(f"Error loading DXF file: {e}")
            raise

    # ---------- Small Geometry Utilities ----------
    @staticmethod
    def _dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    @staticmethod
    def _polyline_length(points: List[Tuple[float, float]]) -> float:
        return sum(math.hypot(points[i + 1][0] - points[i][0],
                              points[i + 1][1] - points[i][1])
                   for i in range(len(points) - 1))

    @staticmethod
    def _bearing(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        ang = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
        return (ang + 360) % 360

    @staticmethod
    def _angle_difference(a1: float, a2: float) -> float:
        diff = abs(a1 - a2) % 360
        return diff if diff <= 180 else 360 - diff

    # ---------- Road Polyline Extraction & Post-processing ----------
    def _extract_road_polylines(self, road_layers: Set[str]) -> Tuple[List[List[Tuple[float, float]]], List[float]]:
        """
        Extract polylines + their explicit widths (avg of vertex start/end width).
        Returns:
            polylines: list of [ (x,y), ... ]
            widths:    list of avg width per original LWPOLYLINE (drawing units)
        """
        polylines: List[List[Tuple[float, float]]] = []
        widths: List[float] = []

        for e in self.msp.query("LWPOLYLINE"):
            try:
                if e.dxf.layer in road_layers:
                    pts = [(v[0], v[1]) for v in e.get_points()]
                    # avg start/end width per vertex; if missing, treat as 0
                    vertex_widths = [((v[2] or 0.0) + (v[3] or 0.0)) / 2.0 for v in e.get_points()]
                    avg_width = float(np.mean(vertex_widths)) if len(vertex_widths) else 0.0

                    if self._polyline_length(pts) > 10:  # ignore tiny polylines
                        polylines.append(pts)
                        widths.append(avg_width)
            except Exception:
                # Skip malformed entities
                continue

        return polylines, widths

    def _merge_polylines(self, polylines: List[List[Tuple[float, float]]],
                         tolerance: float) -> List[List[Tuple[float, float]]]:
        """Merge polylines whose ends are close within 'tolerance'."""
        pls = [list(pl) for pl in polylines]
        merged: List[List[Tuple[float, float]]] = []

        while pls:
            current = pls.pop()
            merged_flag = True
            while merged_flag:
                merged_flag = False
                for i, other in enumerate(pls):
                    if self._dist(current[-1], other[0]) < tolerance:
                        current.extend(other[1:])
                        pls.pop(i)
                        merged_flag = True
                        break
                    elif self._dist(current[0], other[-1]) < tolerance:
                        current = other[:-1] + current
                        pls.pop(i)
                        merged_flag = True
                        break
                    elif self._dist(current[0], other[0]) < tolerance:
                        current = list(reversed(other))[:-1] + current
                        pls.pop(i)
                        merged_flag = True
                        break
                    elif self._dist(current[-1], other[-1]) < tolerance:
                        current.extend(list(reversed(other))[1:])
                        pls.pop(i)
                        merged_flag = True
                        break
            merged.append(current)

        return merged

    def _cluster_roads(self, roads: List[List[Tuple[float, float]]],
                       cluster_distance: float) -> List[List[Tuple[float, float]]]:
        """
        Very simple clustering: if endpoints of two polylines are within cluster_distance,
        they get grouped (concatenated) together.
        """
        working = [list(r) for r in roads]
        clustered: List[List[Tuple[float, float]]] = []

        while working:
            base = working.pop()
            changed = True
            while changed:
                changed = False
                to_remove = []
                for i, other in enumerate(working):
                    if any(self._dist(p1, p2) < cluster_distance
                           for p1 in [base[0], base[-1]]
                           for p2 in [other[0], other[-1]]):
                        # extend with unique points only
                        base += [pt for pt in other if pt not in base]
                        to_remove.append(i)
                        changed = True
                for idx in sorted(to_remove, reverse=True):
                    working.pop(idx)
            clustered.append(base)

        return clustered

    def _average_polyline_distance(self,
                                   pl1: List[Tuple[float, float]],
                                   pl2: List[Tuple[float, float]],
                                   samples: int = 10) -> float:
        """Average min distance from sampled points on pl1 to vertices of pl2."""
        if not pl1 or not pl2:
            return 0.0

        total_len = self._polyline_length(pl1)
        if total_len == 0:
            return 0.0

        dists: List[float] = []
        step = total_len / samples
        seg_index = 0
        acc_len = 0.0
        p_cur = pl1[0]

        # Walk along pl1 and sample at equal-length steps
        for s in range(samples):
            target_len = step * (s + 1)
            while seg_index < len(pl1) - 1 and acc_len < target_len:
                seg_len = self._dist(pl1[seg_index], pl1[seg_index + 1])
                acc_len += seg_len
                p_cur = pl1[seg_index + 1]
                seg_index += 1
            # distance from sample point to all vertices of pl2
            min_d = min(self._dist(p_cur, q) for q in pl2)
            dists.append(min_d)

        return float(np.mean(dists)) if dists else 0.0

    def _find_parallel_edge(self,
                            target: List[Tuple[float, float]],
                            all_roads: List[List[Tuple[float, float]]],
                            angle_tol: float) -> Tuple[Optional[List[Tuple[float, float]]], float]:
        """Find nearest polyline with similar direction (within angle_tol)."""
        if not target or len(target) < 2:
            return None, 0.0

        main_angle = self._bearing(target[0], target[-1])
        closest_dist: Optional[float] = None
        closest_edge: Optional[List[Tuple[float, float]]] = None

        for other in all_roads:
            if other is target or len(other) < 2:
                continue
            other_angle = self._bearing(other[0], other[-1])
            if self._angle_difference(main_angle, other_angle) <= angle_tol:
                avg_d = self._average_polyline_distance(target, other)
                if avg_d > 0 and (closest_dist is None or avg_d < closest_dist):
                    closest_dist = avg_d
                    closest_edge = other

        return closest_edge, (closest_dist if closest_dist is not None else 0.0)

    # ---------- Plot Helpers ----------
    def _get_entity_center(self, entity) -> Tuple[float, float]:
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                points = []
                if hasattr(entity, 'get_points'):
                    points = list(entity.get_points())
                elif hasattr(entity, 'vertices'):
                    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]

                if points:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    return (sum(xs) / len(xs), sum(ys) / len(ys))

            elif entity.dxftype() == 'CIRCLE':
                return (entity.dxf.center.x, entity.dxf.center.y)

            elif entity.dxftype() == 'INSERT':
                return (entity.dxf.insert.x, entity.dxf.insert.y)
        except Exception:
            pass

        return (0.0, 0.0)

    def _calculate_entity_area_perimeter(self, entity) -> Tuple[float, float]:
        try:
            if entity.dxftype() in ['LWPOLYLINE', 'POLYLINE', 'RECTANGLE']:
                return self._calculate_polygon_area_perimeter(entity)
            elif entity.dxftype() == 'CIRCLE':
                radius = float(entity.dxf.radius)
                area = math.pi * radius * radius
                perimeter = 2 * math.pi * radius
                return area, perimeter
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0

    def _calculate_polygon_area_perimeter(self, entity) -> Tuple[float, float]:
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
                x1, y1 = points[i][0], points[i][1]
                x2, y2 = points[j][0], points[j][1]
                area += x1 * y2 - x2 * y1
                dx = x2 - x1
                dy = y2 - y1
                perimeter += math.hypot(dx, dy)

            return abs(area) / 2.0, perimeter
        except Exception:
            return 0.0, 0.0

    # ---------- Plot Extraction (as you had) ----------
    def _extract_plots_by_numbers(self, plot_numbers: List[str], color: int, plot_type: str) -> Dict:
        entities = []
        total_area = 0.0
        total_perimeter = 0.0

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
                entity_data['plot_number'] = f"UNASSIGNED_{i + 1}"

        return {
            'plot_type': plot_type,
            'total_entities': len(entities),
            'total_area_sq_meters': self.convert_to_square_meters(total_area),
            'total_perimeter_meters': self.convert_to_meters(total_perimeter),
            'plot_numbers': [p for p in plot_numbers if p != "NIL"],
            'entities': entities
        }

    def get_original_plots(self) -> Dict:
        original_plot_numbers = [
            "1", "2", "2/A", "3", "4", "5", "5/A", "6", "35", "24", "7", "8", "9", "10",
            "11", "11/A", "12", "13", "14", "15", "15/A", "16", "16/A", "17", "17/A",
            "18", "19", "20", "21", "21/A", "21/B", "22", "23", "24", "25", "26", "27",
            "28", "28/A", "28/B", "29", "29/A", "30", "31", "31/A", "32", "33", "33/A",
            "34", "34/A", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"
        ]
        return self._extract_plots_by_numbers(original_plot_numbers, self.ORIGINAL_COLOR, "Original")

    def get_final_plots(self) -> Dict:
        final_plot_numbers = [
            "1", "2", "NIL", "3", "4", "NIL", "5", "31", "34", "6", "7", "8", "8/A", "9", "10",
            "11", "12", "12/A", "NIL", "14", "15", "15/A", "16", "17", "18", "19", "19/A", "19/B",
            "20", "21", "22", "22/A", "23", "24", "NIL", "25", "32", "25/A", "26", "27", "27/A",
            "28", "29", "29/A", "30", "30/A", "NIL", "NIL", "NIL", "36", "37", "NIL", "NIL", "NIL",
            "NIL", "13", "33", "35", "38", "39"
        ]
        return self._extract_plots_by_numbers(final_plot_numbers, self.FINAL_COLOR, "Final")

    # ---------- Unit Conversions ----------
    def convert_to_square_meters(self, area_raw: float) -> float:
        return area_raw * (self.scale_factor ** 2)

    def convert_to_meters(self, distance_raw: float) -> float:
        return distance_raw * self.scale_factor

    @staticmethod
    def convert_to_square_yards(area_sq_meters: float) -> float:
        return area_sq_meters * 1.19599

    # ---------- Reporting (as you had) ----------
    def generate_report(self):
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

        print("\nDETAILED PLOT INFORMATION:")
        print(f"{'Plot No.':<8} {'Type':<10} {'Area (sq m)':<12} {'Area (sq yd)':<12} {'Perimeter (m)':<12}")
        print("-" * 60)

        for plot in original['entities']:
            area_sq_m = self.convert_to_square_meters(plot['area'])
            area_sq_yd = self.convert_to_square_yards(area_sq_m)
            print(f"{plot['plot_number']:<8} {'Original':<10} "
                  f"{area_sq_m:<12.2f} {area_sq_yd:<12.2f} "
                  f"{self.convert_to_meters(plot['perimeter']):<12.2f}")

        for plot in final['entities']:
            if plot['plot_number'] != "NIL":
                area_sq_m = self.convert_to_square_meters(plot['area'])
                area_sq_yd = self.convert_to_square_yards(area_sq_m)
                print(f"{plot['plot_number']:<8} {'Final':<10} "
                      f"{area_sq_m:<12.2f} {area_sq_yd:<12.2f} "
                      f"{self.convert_to_meters(plot['perimeter']):<12.2f}")

    def calculate_pending_area(self):
        original = self.get_original_plots()
        final = self.get_final_plots()

        original_total = original['total_area_sq_meters']
        final_total = final['total_area_sq_meters']
        pending_area = original_total - final_total

        percentage_change = ((final_total - original_total) / original_total) * 100 if original_total > 0 else 0

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

    # ---------- Scale Calibration & Validation (as you had) ----------
    def find_correct_scale_factor(self):
        reference_areas_sq_yds = [
            389, 2925, 3286, 38, 638, 1745, 72, 21780, 16443, 24, 4284, 768, 95, 9054, 1302,
            27395, 47080, 903, 2901, 2728, 2567, 2162, 572, 372, 5673, 1138, 466, 185, 207,
            1264, 2613, 7502, 22119, 16129, 54519, 30090, 41140, 465, 43368, 1765, 16950,
            13688, 700, 1082, 14472, 48, 10005, 5083, 70, 885, 889, 1969, 334, 124, 42, 22,
            178, 228, 79, 44
        ]
        reference_areas_sq_m = [area / 1.19599 for area in reference_areas_sq_yds]

        original = self.get_original_plots()

        print("\n=== FINDING CORRECT SCALE FACTOR ===")
        print("Reference areas converted from sq yards to sq meters")
        print("Comparing calculated areas with reference areas...")

        scale_factors = []
        for i, plot in enumerate(original['entities']):
            if i < len(reference_areas_sq_m):
                ref_area_sq_m = reference_areas_sq_m[i]
                ref_area_sq_yd = reference_areas_sq_yds[i]
                raw_area = plot['area']
                if ref_area_sq_m > 0 and raw_area > 0:
                    scale_factor = math.sqrt(ref_area_sq_m / raw_area)
                    scale_factors.append(scale_factor)
                    print(f"Plot {plot['plot_number']}: Ref={ref_area_sq_yd} sq yd "
                          f"({ref_area_sq_m:.2f} sq m), Raw={raw_area:.6f}, Scale={scale_factor:.6f}")

        if scale_factors:
            scale_factors.sort()
            median_scale = scale_factors[len(scale_factors) // 2]
            mean_scale = sum(scale_factors) / len(scale_factors)
            print(f"\nCalculated scale factors:")
            print(f"Median scale factor: {median_scale:.6f}")
            print(f"Mean scale factor: {mean_scale:.6f}")
            print(f"Current scale factor: {self.scale_factor}")
            self.scale_factor = median_scale
            print(f"Updated scale factor to: {self.scale_factor}")
            return median_scale
        else:
            print("No valid scale factors found!")
            return None

    def validate_original_plots(self):
        reference_areas_sq_yds = [
            389, 2925, 3286, 38, 638, 1745, 72, 21780, 16443, 24, 4284, 768, 95, 9054, 1302,
            27395, 47080, 903, 2901, 2728, 2567, 2162, 572, 372, 5673, 1138, 466, 185, 207,
            1264, 2613, 7502, 22119, 16129, 54519, 30090, 41140, 465, 43368, 1765, 16950,
            13688, 700, 1082, 14472, 48, 10005, 5083, 70, 885, 889, 1969, 334, 124, 42, 22,
            178, 228, 79, 44
        ]
        original = self.get_original_plots()

        print("\n=== ORIGINAL PLOTS VALIDATION (20% Threshold) ===")
        print(f"{'Plot No.':<8} {'Ref (sq yd)':<12} {'Calc (sq m)':<12} "
              f"{'Calc (sq yd)':<12} {'Diff %':<10} {'Status':<10}")
        print("-" * 70)

        valid_plots, invalid_plots = [], []
        valid_count = invalid_count = 0

        for i, plot in enumerate(original['entities']):
            if i < len(reference_areas_sq_yds):
                ref_area_sq_yd = reference_areas_sq_yds[i]
                calc_area_sq_m = self.convert_to_square_meters(plot['area'])
                calc_area_sq_yd = self.convert_to_square_yards(calc_area_sq_m)
                diff_percent = (abs((calc_area_sq_yd - ref_area_sq_yd) / ref_area_sq_yd) * 100
                                if ref_area_sq_yd > 0 else 100.0)

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

                print(f"{plot['plot_number']:<8} {ref_area_sq_yd:<12.0f} "
                      f"{calc_area_sq_m:<12.2f} {calc_area_sq_yd:<12.2f} "
                      f"{diff_percent:<10.2f} {status:<10}")

        print("-" * 70)
        print(f"Total plots compared: {len(reference_areas_sq_yds)}")
        print(f"Valid plots (≤20% diff): {valid_count}")
        print(f"Invalid plots (>20% diff): {invalid_count}")
        print(f"Validation rate: {(valid_count / len(reference_areas_sq_yds) * 100):.1f}%")

        print("\n=== VALID ORIGINAL PLOTS (≤20% difference) ===")
        if valid_plots:
            for p in valid_plots:
                print(f"Plot {p['plot_number']}: Ref={p['ref_area']} sq yd, "
                      f"Calc={p['calc_area_sq_yd']:.2f} sq yd, Diff={p['diff_percent']:.2f}%")
        else:
            print("No valid plots found!")

        print("\n=== INVALID ORIGINAL PLOTS (>20% difference) ===")
        if invalid_plots:
            for p in invalid_plots:
                print(f"Plot {p['plot_number']}: Ref={p['ref_area']} sq yd, "
                      f"Calc={p['calc_area_sq_yd']:.2f} sq yd, Diff={p['diff_percent']:.2f}%")
        else:
            print("No invalid plots found!")

        return {
            'total_plots': len(reference_areas_sq_yds),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'validation_rate': valid_count / len(reference_areas_sq_yds) * 100,
            'valid_plots': valid_plots,
            'invalid_plots': invalid_plots
        }

    def validate_final_plots(self):
        reference_areas_sq_yds = [
            480, 3212, 462, 1751, 10921, 4435, 30981, 4971, 8360, 14495, 42961, 944, 2969, 2808,
            2674, 2205, 372, 5673, 9440, 466, 5496, 88184, 132786, 698, 5824, 22107, 49629, 27973,
            43414, 37553, 2054, 16009, 13638, 700, 1082, 14466, 65, 10013, 6804, 124, 67, 565,
            4083, 10316, 22, 236
        ]
        final = self.get_final_plots()

        print("\n=== FINAL PLOTS VALIDATION (20% Threshold) ===")
        print(f"{'Plot No.':<8} {'Ref (sq yd)':<12} {'Calc (sq m)':<12} "
              f"{'Calc (sq yd)':<12} {'Diff %':<10} {'Status':<10}")
        print("-" * 70)

        valid_plots, invalid_plots = [], []
        valid_count = invalid_count = 0

        for i, plot in enumerate(final['entities']):
            if plot['plot_number'] != "NIL" and i < len(reference_areas_sq_yds):
                ref_area_sq_yd = reference_areas_sq_yds[i]
                calc_area_sq_m = self.convert_to_square_meters(plot['area'])
                calc_area_sq_yd = self.convert_to_square_yards(calc_area_sq_m)
                diff_percent = (abs((calc_area_sq_yd - ref_area_sq_yd) / ref_area_sq_yd) * 100
                                if ref_area_sq_yd > 0 else 100.0)

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

                print(f"{plot['plot_number']:<8} {ref_area_sq_yd:<12.0f} "
                      f"{calc_area_sq_m:<12.2f} {calc_area_sq_yd:<12.2f} "
                      f"{diff_percent:<10.2f} {status:<10}")

        print("-" * 70)
        print(f"Total plots compared: {len(reference_areas_sq_yds)}")
        print(f"Valid plots (≤20% diff): {valid_count}")
        print(f"Invalid plots (>20% diff): {invalid_count}")
        print(f"Validation rate: {(valid_count / len(reference_areas_sq_yds) * 100):.1f}%")

        print("\n=== VALID FINAL PLOTS (≤20% difference) ===")
        if valid_plots:
            for p in valid_plots:
                print(f"Plot {p['plot_number']}: Ref={p['ref_area']} sq yd, "
                      f"Calc={p['calc_area_sq_yd']:.2f} sq yd, Diff={p['diff_percent']:.2f}%")
        else:
            print("No valid plots found!")

        print("\n=== INVALID FINAL PLOTS (>20% difference) ===")
        if invalid_plots:
            for p in invalid_plots:
                print(f"Plot {p['plot_number']}: Ref={p['ref_area']} sq yd, "
                      f"Calc={p['calc_area_sq_yd']:.2f} sq yd, Diff={p['diff_percent']:.2f}%")
        else:
            print("No invalid plots found!")

        return {
            'total_plots': len(reference_areas_sq_yds),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'validation_rate': valid_count / len(reference_areas_sq_yds) * 100,
            'valid_plots': valid_plots,
            'invalid_plots': invalid_plots
        }

    # ---------- NEW: Road Analysis ----------
    def analyze_roads(self,
                      road_layers: Optional[Set[str]] = None,
                      max_roads: int = 15,
                      min_length_units: float = 30.0):
        """
        Detect roads from specified layers, merge/cluster, and compute
        length & width for each road. Widths come from explicit LWPOLYLINE widths
        if present (averaged), otherwise estimated from nearest parallel edge.
        Prints a table and also returns structured data.
        """
        if road_layers is None:
            road_layers = self.ROAD_LAYERS

        # Step 1: extract
        road_polys, road_widths_raw = self._extract_road_polylines(road_layers)

        # Step 2: merge & cluster
        merged = self._merge_polylines(road_polys, tolerance=self.MERGE_TOLERANCE)
        clustered = self._cluster_roads(merged, cluster_distance=self.CLUSTER_DISTANCE)

        # Step 3: filter sizable
        final_roads = [r for r in clustered if self._polyline_length(r) > min_length_units][:max_roads]

        # Precompute a global average explicit width (drawing units)
        explicit_widths = [w for w in road_widths_raw if w > 0]
        global_avg_width_units = float(np.mean(explicit_widths)) if explicit_widths else 0.0

        print("\nLength and Width (DXF-based, parallel-aware) for each road:\n")
        results = []
        for i, road in enumerate(final_roads, 1):
            length_units = self._polyline_length(road)
            length_m = self.convert_to_meters(length_units)

            # If any explicit width existed in the file, use global avg as fallback;
            # else, estimate via parallel edge distance
            if global_avg_width_units > 0:
                w_units = global_avg_width_units
            else:
                _, w_units = self._find_parallel_edge(road, final_roads, self.PARALLEL_ANGLE_TOL)

            width_m = self.convert_to_meters(w_units)

            start_pt = (round(float(road[0][0]), 2), round(float(road[0][1]), 2))
            end_pt = (round(float(road[-1][0]), 2), round(float(road[-1][1]), 2))

            print(f"Road {i}: Start {start_pt}, End {end_pt}, "
                  f"Length {length_units:.2f} units ({length_m:.2f} m), "
                  f"Width {w_units:.2f} units ({width_m:.2f} m)")

            results.append({
                "index": i,
                "start": start_pt,
                "end": end_pt,
                "length_units": length_units,
                "length_m": length_m,
                "width_units": w_units,
                "width_m": width_m,
                "points": road
            })

        if not results:
            print("No roads found that pass the size filters. Try loosening the thresholds or check layers.")
        return results


def main():
    analyzer = PlotAnalyzer("CTP01(LALDARWAJA)FINAL.dxf")

    # 1) Calibrate scale so meters are correct everywhere (plots + roads)
    analyzer.find_correct_scale_factor()

    # 2) Plot reports
    analyzer.generate_report()
    analyzer.calculate_pending_area()
    analyzer.validate_original_plots()
    analyzer.validate_final_plots()

    # 3) Road analysis (uses the same scale_factor for meters)
    analyzer.analyze_roads(
        road_layers=PlotAnalyzer.ROAD_LAYERS,   # change if your road layers differ
        max_roads=15,
        min_length_units=30.0
    )


if __name__ == "__main__":
    main()
