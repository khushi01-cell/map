import ezdxf
import math
import numpy as np

# Settings
MERGE_TOLERANCE = 0.2
CLUSTER_DISTANCE = 10.0
ROAD_LAYERS = {"0", "1F8CE10"}  # DXF layers for roads
PARALLEL_ANGLE_TOL = 60  # degrees

# ---------- Utility Functions ----------

def dist(p1, p2):
    """Euclidean distance between 2 points"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def polyline_length(points):
    """Total length of a polyline"""
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))

def bearing(p1, p2):
    """Return angle in degrees of line from p1 to p2"""
    ang = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    return (ang + 360) % 360

def angle_difference(a1, a2):
    """Smallest difference between two angles (degrees)"""
    diff = abs(a1 - a2) % 360
    return diff if diff <= 180 else 360 - diff

def merge_polylines(polylines, tolerance=MERGE_TOLERANCE):
    """Merge polylines if their ends are closer than tolerance."""
    merged = []
    while polylines:
        current = polylines.pop()
        merged_flag = True
        while merged_flag:
            merged_flag = False
            for i, other in enumerate(polylines):
                if dist(current[-1], other[0]) < tolerance:
                    current.extend(other[1:])
                    polylines.pop(i)
                    merged_flag = True
                    break
                elif dist(current[0], other[-1]) < tolerance:
                    current = other[:-1] + current
                    polylines.pop(i)
                    merged_flag = True
                    break
                elif dist(current[0], other[0]) < tolerance:
                    current = list(reversed(other))[:-1] + current
                    polylines.pop(i)
                    merged_flag = True
                    break
                elif dist(current[-1], other[-1]) < tolerance:
                    current.extend(list(reversed(other))[1:])
                    polylines.pop(i)
                    merged_flag = True
                    break
        merged.append(current)
    return merged

def cluster_roads(roads, cluster_distance=CLUSTER_DISTANCE):
    """Cluster roads that are within a certain distance of each other."""
    clustered = []
    while roads:
        base = roads.pop()
        changed = True
        while changed:
            changed = False
            to_remove = []
            for i, other in enumerate(roads):
                if any(dist(p1, p2) < cluster_distance
                       for p1 in [base[0], base[-1]]
                       for p2 in [other[0], other[-1]]):
                    base += [pt for pt in other if pt not in base]
                    to_remove.append(i)
                    changed = True
            for index in sorted(to_remove, reverse=True):
                roads.pop(index)
        clustered.append(base)
    return clustered

# ---------- DXF Polyline Extraction ----------

def extract_polylines(msp, road_layers):
    """Extract polylines from certain layers along with explicit DXF widths."""
    polylines = []
    widths = []
    for e in msp.query("LWPOLYLINE"):
        if e.dxf.layer in road_layers:
            pts = [(v[0], v[1]) for v in e.get_points()]
            vertex_widths = [((v[2] or 0) + (v[3] or 0)) / 2 for v in e.get_points()]
            avg_width = np.mean(vertex_widths) if vertex_widths else 0
            if polyline_length(pts) > 10:  # Ignore tiny polylines
                polylines.append(pts)
                widths.append(avg_width)
    return polylines, widths

# ---------- Parallel-Aware Geometry Width ----------

def average_polyline_distance(pl1, pl2, samples=10):
    """Average shortest distance from pl1 sample points to pl2 vertices."""
    if not pl1 or not pl2:
        return 0
    dists = []
    total_len = polyline_length(pl1)
    if total_len == 0:
        return 0
    step = total_len / samples
    seg_accum = 0
    seg_index = 0
    p_start = pl1[0]
    for s in range(samples):
        while seg_index < len(pl1) - 1 and seg_accum < step * (s + 1):
            seg_len = dist(pl1[seg_index], pl1[seg_index + 1])
            seg_accum += seg_len
            p_start = pl1[seg_index + 1]
            seg_index += 1
        min_d = min(dist(p_start, q) for q in pl2)
        dists.append(min_d)
    return np.mean(dists) if dists else 0

def find_parallel_edge(target_road, all_roads, angle_tol=PARALLEL_ANGLE_TOL):
    """Find nearest road edge that is parallel to the target road."""
    # Estimate target road direction from its endpoints
    main_angle = bearing(target_road[0], target_road[-1])
    closest_dist = None
    closest_edge = None
    for other in all_roads:
        if other is target_road:
            continue
        other_angle = bearing(other[0], other[-1])
        if angle_difference(main_angle, other_angle) <= angle_tol:
            avg_dist = average_polyline_distance(target_road, other)
            if avg_dist > 0 and (closest_dist is None or avg_dist < closest_dist):
                closest_dist = avg_dist
                closest_edge = other
    return closest_edge, closest_dist if closest_dist else 0

# ---------- Main ----------

def main():
    dxf_path = "CTP01(LALDARWAJA)FINAL.dxf"  # Change to your DXF file path
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Step 1: Extract polylines & explicit widths
    road_polylines, road_widths = extract_polylines(msp, ROAD_LAYERS)

    # Step 2: Merge & cluster
    merged = merge_polylines(road_polylines, tolerance=MERGE_TOLERANCE)
    clustered = cluster_roads(merged, cluster_distance=CLUSTER_DISTANCE)

    # Step 3: Filter final roads
    final_roads = [road for road in clustered if polyline_length(road) > 30][:15]

    # Step 4: Report with per-road widths
    print("Length and Width (DXF-based, parallel-aware) for each road:\n")
    for i, road in enumerate(final_roads, 1):
        length_units = polyline_length(road)
        length_meters = length_units * 0.3048

        if any(road_widths) and any(w > 0 for w in road_widths):
            w_units = np.mean([w for w in road_widths if w > 0])
        else:
            # Find a parallel opposite edge for this road
            _, w_units = find_parallel_edge(road, final_roads)
        width_meters = w_units * 0.3048

        start_pt = tuple(round(float(c), 2) for c in road[0])
        end_pt = tuple(round(float(c), 2) for c in road[-1])

        print(f"Road {i}: Start {start_pt}, End {end_pt}, "
              f"Length {length_units:.2f} units ({length_meters:.2f} m), "
              f"Width {w_units:.2f} units ({width_meters:.2f} m)")

if __name__ == "__main__":
    main()
