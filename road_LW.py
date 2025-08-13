import ezdxf
import math
import numpy as np

# Increased tolerance for merging segments that are nearly connected (units)
MERGE_TOLERANCE = 0.2  # Increased tolerance for merging

def dist(p1, p2):
    """Calculate the Euclidean distance between two points."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def polyline_length(points):
    """Calculate the total length of a polyline given its points."""
    return sum(dist(points[i], points[i+1]) for i in range(len(points) - 1))

def merge_polylines(polylines, tolerance=MERGE_TOLERANCE):
    """Merge polylines that are within a certain distance of each other."""
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

def cluster_roads(roads, cluster_distance=10.0):
    """Cluster roads that are within a certain distance of each other."""
    clustered = []
    while roads:
        base = roads.pop()
        changed = True
        while changed:
            changed = False
            to_remove = []
            for i, other in enumerate(roads):
                if any(dist(p1, p2) < cluster_distance for p1 in [base[0], base[-1]] for p2 in [other[0], other[-1]]):
                    combined = base + [pt for pt in other if pt not in base]
                    base = combined
                    to_remove.append(i)
                    changed = True
            for index in sorted(to_remove, reverse=True):
                roads.pop(index)
        clustered.append(base)
    return clustered

def main():
    dxf_path = "CTP01(LALDARWAJA)FINAL.dxf"  # Update to your file path
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    layers_in_dxf = {e.dxf.layer for e in msp if hasattr(e.dxf, "layer")}
    print("Layers in DXF:")
    for l in layers_in_dxf:
        print(" -", l)

    road_layers = {"0", "1F8CE10"}

    road_polylines = []
    for e in msp.query("LWPOLYLINE"):
        if e.dxf.layer in road_layers:
            pts = [(v[0], v[1]) for v in e.get_points()]
            if polyline_length(pts) > 10:  # Adjust length cutoff if needed
                road_polylines.append(pts)

    merged = merge_polylines(road_polylines, tolerance=MERGE_TOLERANCE)
    print(f"Merged into {len(merged)} road segments after initial merging.")

    clustered = cluster_roads(merged, cluster_distance=10.0)  # Cluster within 10 units approx
    print(f"Clustered into {len(clustered)} roads after proximity clustering.")

    # Filter out very short roads/noise
    final_roads = [road for road in clustered if polyline_length(road) > 30]  # Filter threshold adjustable
    final_roads = final_roads[:15]  # Limit to 15 roads

    print(f"Filtered to {len(final_roads)} final roads with length > 30 units.")

    for i, road in enumerate(final_roads, 1):
        length_units = polyline_length(road)
        length_meters = length_units * 0.3048  # Convert length from feet to meters
        print(f"Road {i}: Start {road[0]}, End {road[-1]}, Length {length_units:.2f} units ({length_meters:.2f} meters)")

if __name__ == "__main__":
    main()
