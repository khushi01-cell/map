import re
import math
import sys
from typing import List, Tuple, Optional

import ezdxf
import numpy as np
from ezdxf.math import Vec2, Vec3, UVec, ConstructionPolyline


# -------------- CONFIG -----------------
DXF_FILE = "your_file.dxf"         # <-- change
ROAD_EDGE_LAYERS = {"ROAD_EDGE", "ROAD", "RED", "0"}  # <-- change to your edge layers
WIDTH_TEXT_LAYERS = {"DIM", "TEXT", "ANNOT", "0"}      # <-- where 25'-0" etc. live
SAMPLE_EVERY = 1.0                 # sampling step (drawing units) along edge
MAX_PAIR_GAP = 10.0                # max distance between paired edges (same units)
# --------------------------------------


# --- Helpers -------------------------------------------------

def feet_inch_to_m(text: str) -> Optional[float]:
    """
    Parse strings like 25'-0", 30' or 30’-0” and return meters.
    """
    s = text.strip().replace("’", "'").replace("”", '"').replace("′", "'").replace("″", '"')
    m = re.search(r"(\d+)\s*'\s*(\d+)?\s*\"?", s)
    if not m:
        m = re.search(r"(\d+)\s*'\s*$", s)
        if not m:
            return None
        feet = int(m.group(1))
        inches = 0
    else:
        feet = int(m.group(1))
        inches = int(m.group(2) or 0)

    meters = feet * 0.3048 + inches * 0.0254
    return meters


def get_unit_scale_to_m(doc) -> float:
    """
    Convert DXF $INSUNITS to meters.
    """
    # ezdxf units: 0=unitless, 1=inches, 2=feet, 4=mm, 5=cm, 6=m, etc.
    units = doc.header.get("$INSUNITS", 0)
    table = {
        0: 1.0,         # treat as drawing is already in meters-ish; adjust if needed
        1: 0.0254,
        2: 0.3048,
        4: 0.001,
        5: 0.01,
        6: 1.0,
    }
    return table.get(units, 1.0)


def entity_to_points(e) -> np.ndarray:
    """
    Flatten common curve types to a Nx2 array (2D).
    """
    def vecs_to_np(vecs: List[UVec]) -> np.ndarray:
        arr = np.array([[v.x, v.y] for v in vecs], dtype=float)
        # remove consecutive duplicates
        keep = [0]
        for i in range(1, len(arr)):
            if np.linalg.norm(arr[i] - arr[i-1]) > 1e-9:
                keep.append(i)
        return arr[keep]

    try:
        if e.dxftype() == "LINE":
            p = [Vec2(e.dxf.start), Vec2(e.dxf.end)]
            return vecs_to_np(p)

        if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pl = ConstructionPolyline.from_polyline(e)
            return vecs_to_np(pl.flattening(distance=0.2))  # denser if curves exist

        if e.dxftype() == "ARC":
            # approximate arc
            pl = ConstructionPolyline.from_arc(e)
            return vecs_to_np(pl.flattening(distance=0.2))

        if e.dxftype() == "SPLINE":
            return vecs_to_np(e.flattening(0.2))

    except Exception:
        pass

    return np.zeros((0, 2), dtype=float)


def cumulative_lengths(points: np.ndarray) -> np.ndarray:
    segs = np.linalg.norm(points[1:] - points[:-1], axis=1)
    return np.concatenate([[0.0], np.cumsum(segs)])


def resample_polyline(points: np.ndarray, step: float) -> np.ndarray:
    """
    Resample a polyline to equally spaced points (chord length spacing).
    """
    if len(points) < 2:
        return points.copy()
    s = cumulative_lengths(points)
    total = s[-1]
    if total == 0:
        return points[:1].copy()

    t = np.arange(0.0, total + step, step)
    t[-1] = total  # ensure last point included

    # interpolate coordinates
    x = np.interp(t, s, points[:, 0])
    y = np.interp(t, s, points[:, 1])
    return np.column_stack([x, y])


def closest_point_distance(a_pt: np.ndarray, poly: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Distance from a point to a broken polyline; returns (distance, closest_point).
    """
    best_d2 = float("inf")
    best = None
    for i in range(len(poly) - 1):
        p = poly[i]
        q = poly[i + 1]
        v = q - p
        w = a_pt - p
        L2 = v.dot(v)
        if L2 == 0:
            proj = p
        else:
            t = np.clip(w.dot(v) / L2, 0.0, 1.0)
            proj = p + t * v
        d2 = np.sum((a_pt - proj) ** 2)
        if d2 < best_d2:
            best_d2 = d2
            best = proj
    return math.sqrt(best_d2), best


def pair_two_edges(edges: List[np.ndarray]) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    Pick the pair of polylines that stay close and are the longest—heuristic but robust.
    """
    if len(edges) < 2:
        return None

    # score all pairs by average minimum distance (lower is better) and by length
    def poly_len(p):
        return float(cumulative_lengths(p)[-1])

    best = None
    best_score = float("inf")
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a, b = edges[i], edges[j]
            # sample A and measure to B
            a_s = resample_polyline(a, SAMPLE_EVERY * 2)
            dists = []
            for P in a_s:
                d, _ = closest_point_distance(P, b)
                dists.append(d)
            if not dists:
                continue
            avg_d = float(np.mean(dists))
            if avg_d > MAX_PAIR_GAP:
                continue
            score = avg_d / max(1e-6, (poly_len(a) + poly_len(b)) / 2.0)
            if score < best_score:
                best_score = score
                best = (a, b)
    return best


def build_centerline_and_widths(edge_a: np.ndarray, edge_b: np.ndarray, step: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Sample along edge_a and project to edge_b to get widths; centerline is the midpoint of pairs.
    Returns (centerline_points Nx2, widths N).
    """
    a_s = resample_polyline(edge_a, step)
    centers = []
    widths = []
    for P in a_s:
        d, Q = closest_point_distance(P, edge_b)
        if Q is None:
            continue
        mid = 0.5 * (P + Q)
        centers.append(mid)
        widths.append(d)
    if len(centers) < 2:
        return np.zeros((0, 2)), np.array([])
    return np.vstack(centers), np.array(widths)


def scan_width_texts(msp) -> List[Tuple[str, Vec3]]:
    out = []
    for e in list(msp.query("TEXT MTEXT")):
        try:
            layer = e.dxf.layer
        except Exception:
            layer = ""
        if WIDTH_TEXT_LAYERS and layer not in WIDTH_TEXT_LAYERS:
            continue
        txt = ""
        base = Vec3(0, 0, 0)
        if e.dxftype() == "TEXT":
            txt = e.dxf.text
            base = e.dxf.insert
        else:
            txt = e.text
            base = e.dxf.insert if hasattr(e.dxf, "insert") else Vec3(0, 0, 0)
        if re.search(r"\d+\s*'\s*\d*", txt):
            out.append((txt.strip(), base))
    return out


# --- Main pipeline ------------------------------------------

def main():
    doc = ezdxf.readfile(DXF_FILE)
    msp = doc.modelspace()
    unit_to_m = get_unit_scale_to_m(doc)

    # 1) collect road-edge curves
    edges: List[np.ndarray] = []
    for e in msp:
        if e.dxftype() not in ("LINE", "LWPOLYLINE", "POLYLINE", "SPLINE", "ARC"):
            continue
        if ROAD_EDGE_LAYERS and e.dxf.layer not in ROAD_EDGE_LAYERS:
            continue
        pts = entity_to_points(e)
        if len(pts) >= 2:
            edges.append(pts)

    if len(edges) < 2:
        print("❌ Not enough edge polylines found. Adjust ROAD_EDGE_LAYERS.")
        return

    pair = pair_two_edges(edges)
    if not pair:
        print("❌ Could not find a close parallel pair of edges. Tune MAX_PAIR_GAP/filters.")
        return

    edge_a, edge_b = pair

    # 2) compute centerline + widths
    centerline, widths = build_centerline_and_widths(edge_a, edge_b, SAMPLE_EVERY)
    if len(centerline) < 2:
        print("❌ Centerline too short. Increase SAMPLE_EVERY or check layers.")
        return

    # 3) compute length along centerline
    cl_len_units = cumulative_lengths(centerline)[-1]
    cl_len_m = cl_len_units * unit_to_m

    # 4) report widths (units + meters)
    w_units = widths
    w_m = widths * unit_to_m

    # 5) start & end points (in drawing units and meters)
    start_pt = centerline[0]
    end_pt = centerline[-1]
    start_pt_m = start_pt * unit_to_m
    end_pt_m = end_pt * unit_to_m

    # 6) Try reading a width text like 25'-0"
    dim_texts = scan_width_texts(msp)
    parsed_dims_m = []
    for txt, base in dim_texts:
        fm = feet_inch_to_m(txt)
        if fm is not None:
            parsed_dims_m.append((txt, fm, base))

    # ---- OUTPUT -------------------------------------------------
    print("✅ ROAD MEASURE")
    print(f"[units] $INSUNITS scale to meters: {unit_to_m:.6f} m/unit")
    print(f"Centerline length: {cl_len_units:.3f} units  |  {cl_len_m:.3f} m")
    print(f"Width (min / mean / max): "
          f"{w_units.min():.3f}/{w_units.mean():.3f}/{w_units.max():.3f} units  |  "
          f"{w_m.min():.3f}/{w_m.mean():.3f}/{w_m.max():.3f} m")
    print(f"Start point (units): {start_pt[0]:.3f}, {start_pt[1]:.3f}")
    print(f"End   point (units): {end_pt[0]:.3f}, {end_pt[1]:.3f}")
    print(f"Start point (m): {start_pt_m[0]:.3f}, {start_pt_m[1]:.3f}")
    print(f"End   point (m): {end_pt_m[0]:.3f}, {end_pt_m[1]:.3f}")

    if parsed_dims_m:
        print("\n📏 Width TEXT found (feet-inches → meters):")
        for txt, val_m, base in parsed_dims_m:
            print(f"  '{txt}'  ≈ {val_m:.3f} m at {tuple(round(c, 3) for c in base)}")
    else:
        print("\n(No width TEXT like 25'-0\" found on the configured layers.)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        DXF_FILE = sys.argv[1]
    main()
