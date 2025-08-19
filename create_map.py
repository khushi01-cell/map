#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redraw complete map from a source DXF into a clean TP-style scheme:
- Extracts plots (closed polylines/circles), roads (by layer), and text (TEXT/MTEXT)
- Merges road polylines, clusters them, estimates road widths (parallel-aware fallback)
- Rebuilds geometry into a new DXF with tidy layers & optional labels

Usage:
    python redraw_map.py input.dxf output.dxf
"""

import sys
import math
import ezdxf
import numpy as np
from ezdxf.document import Drawing
from typing import List, Tuple, Dict, Optional, Set

# =========================
# Configuration (tweak me!)
# =========================

# Layers that indicate roads in the input DXF
ROAD_LAYERS: Set[str] = {"0", "1F8CE10"}  # change if your roads are on different layers

# Colors used in the input for "original" vs "final" plots (kept from your earlier setup)
ORIGINAL_PLOT_COLOR = 3  # green
FINAL_PLOT_COLOR = 1     # red

# New DXF layer names & colors (output)
LAYER_PLOTS_ORIG = ("PLOTS_ORIGINAL", 3)  # green
LAYER_PLOTS_FINAL = ("PLOTS_FINAL", 1)    # red
LAYER_ROADS = ("ROADS", 7)                # white
LAYER_TEXT = ("TEXT", 2)                  # yellow
LAYER_GUIDES = ("GUIDES", 8)              # gray

# Road processing
MERGE_TOLERANCE = 0.2          # drawing units
CLUSTER_DISTANCE = 10.0        # drawing units
PARALLEL_ANGLE_TOL = 60.0      # degrees
MIN_ROAD_LENGTH_UNITS = 30.0   # ignore tiny road fragments
MAX_ROADS_OUTPUT = 99999       # or clip if you want

# Plot processing
MIN_PLOT_AREA_UNITS2 = 1e-6    # ignore microscopic polygons

# Labeling controls
ADD_PLOT_AREA_LABELS = True
ADD_ROAD_DIM_LABELS = True
TEXT_HEIGHT = 2.5              # drawing units (change if too big/small)

# Optional scaling to meters for road dimension labels (if you know the factor)
# If you want "native drawing units" to show in labels, set this to 1.0
SCALE_TO_METERS = 1.0

# =========================
# Geometry helpers
# =========================

def dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def polyline_length(points: List[Tuple[float, float]]) -> float:
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))

def polygon_area(points: List[Tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        area += points[i][0] * points[j][1] - points[j][0] * points[i][1]
    return abs(area) / 2.0

def centroid(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    # Centroid for polygon (assumes closed polygon)
    A = 0.0
    Cx = 0.0
    Cy = 0.0
    for i in range(len(points)):
        j = (i + 1) % len(points)
        cross = points[i][0] * points[j][1] - points[j][0] * points[i][1]
        A += cross
        Cx += (points[i][0] + points[j][0]) * cross
        Cy += (points[i][1] + points[j][1]) * cross
    A *= 0.5
    if abs(A) < 1e-12:
        # Fallback to mean of vertices
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    Cx /= (6.0 * A)
    Cy /= (6.0 * A)
    return (Cx, Cy)

def bearing(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    ang = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    return (ang + 360) % 360

def angle_difference(a1: float, a2: float) -> float:
    diff = abs(a1 - a2) % 360
    return diff if diff <= 180 else 360 - diff

def ensure_layer(doc: Drawing, name: str, color: int) -> None:
    if name not in doc.layers:
        doc.layers.add(name, color=color)

# =========================
# Road merging & width calc
# =========================

def merge_polylines(polylines: List[List[Tuple[float, float]]], tolerance: float) -> List[List[Tuple[float, float]]]:
    merged = []
    pool = [list(pl) for pl in polylines]
    while pool:
        current = pool.pop()
        changed = True
        while changed:
            changed = False
            for i, other in enumerate(pool):
                if dist(current[-1], other[0]) < tolerance:
                    current.extend(other[1:])
                    pool.pop(i)
                    changed = True
                    break
                elif dist(current[0], other[-1]) < tolerance:
                    current = other[:-1] + current
                    pool.pop(i)
                    changed = True
                    break
                elif dist(current[0], other[0]) < tolerance:
                    current = list(reversed(other))[:-1] + current
                    pool.pop(i)
                    changed = True
                    break
                elif dist(current[-1], other[-1]) < tolerance:
                    current.extend(list(reversed(other))[1:])
                    pool.pop(i)
                    changed = True
                    break
        merged.append(current)
    return merged

def cluster_roads(roads: List[List[Tuple[float, float]]], cluster_distance: float) -> List[List[Tuple[float, float]]]:
    out = []
    pool = [list(r) for r in roads]
    while pool:
        base = pool.pop()
        changed = True
        while changed:
            changed = False
            kill = []
            for i, other in enumerate(pool):
                if any(dist(p1, p2) < cluster_distance
                       for p1 in [base[0], base[-1]]
                       for p2 in [other[0], other[-1]]):
                    base += [pt for pt in other if pt not in base]
                    kill.append(i)
                    changed = True
            for k in sorted(kill, reverse=True):
                pool.pop(k)
        out.append(base)
    return out

def average_polyline_distance(pl1: List[Tuple[float, float]], pl2: List[Tuple[float, float]], samples: int = 10) -> float:
    if not pl1 or not pl2:
        return 0.0
    tot_len = polyline_length(pl1)
    if tot_len <= 0:
        return 0.0
    dists = []
    step = tot_len / samples
    seg_i = 0
    acc = 0.0
    p = pl1[0]
    for s in range(samples):
        target = step * (s + 1)
        while seg_i < len(pl1) - 1 and acc < target:
            seg_len = dist(pl1[seg_i], pl1[seg_i + 1])
            acc += seg_len
            p = pl1[seg_i + 1]
            seg_i += 1
        dists.append(min(dist(p, q) for q in pl2))
    return float(np.mean(dists)) if dists else 0.0

def find_parallel_edge(target: List[Tuple[float, float]],
                       all_roads: List[List[Tuple[float, float]]],
                       angle_tol: float) -> Tuple[Optional[List[Tuple[float, float]]], float]:
    if not target or len(target) < 2:
        return None, 0.0
    main_ang = bearing(target[0], target[-1])
    best_d = None
    best = None
    for other in all_roads:
        if other is target or len(other) < 2:
            continue
        ang = bearing(other[0], other[-1])
        if angle_difference(main_ang, ang) <= angle_tol:
            d = average_polyline_distance(target, other)
            if d > 0 and (best_d is None or d < best_d):
                best_d = d
                best = other
    return best, (best_d if best_d is not None else 0.0)

# =========================
# Extraction from source DXF
# =========================

def extract_roads(msp: ezdxf.layouts.Modelspace, road_layers: Set[str]) -> Tuple[List[List[Tuple[float, float]]], List[float]]:
    polylines = []
    widths = []
    for e in msp.query("LWPOLYLINE"):
        try:
            if e.dxf.layer in road_layers:
                pts = [(v[0], v[1]) for v in e.get_points()]  # list of (x, y)
                vws = [((v[2] or 0.0) + (v[3] or 0.0)) / 2.0 for v in e.get_points()]
                avg_w = float(np.mean(vws)) if vws else 0.0
                if polyline_length(pts) > 1.0:  # keep small; filter later
                    polylines.append(pts)
                    widths.append(avg_w)
        except Exception:
            continue
    return polylines, widths

def is_closed_polyline(e) -> bool:
    if e.dxftype() == "LWPOLYLINE":
        try:
            return bool(e.closed)
        except Exception:
            pass
    if e.dxftype() == "POLYLINE":
        try:
            return bool(e.is_closed)
        except Exception:
            pass
    return False

def entity_points(e) -> List[Tuple[float, float]]:
    pts = []
    if e.dxftype() == "LWPOLYLINE":
        try:
            pts = [(p[0], p[1]) for p in e.get_points()]
        except Exception:
            pts = []
    elif e.dxftype() == "POLYLINE":
        try:
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        except Exception:
            pts = []
    return pts

def extract_plots(msp: ezdxf.layouts.Modelspace) -> Dict[str, List[List[Tuple[float, float]]]]:
    """Return dict with 'original', 'final', and 'other' plot polygons."""
    plots = {"original": [], "final": [], "other": []}
    for e in msp:
        try:
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE") and is_closed_polyline(e):
                pts = entity_points(e)
                if len(pts) >= 3 and polygon_area(pts) >= MIN_PLOT_AREA_UNITS2:
                    col = getattr(e.dxf, "color", 7)
                    if col == ORIGINAL_PLOT_COLOR:
                        plots["original"].append(pts)
                    elif col == FINAL_PLOT_COLOR:
                        plots["final"].append(pts)
                    else:
                        plots["other"].append(pts)
            elif e.dxftype() == "CIRCLE":
                # Approximate circle as polygon (for redraw)
                cx = float(e.dxf.center.x)
                cy = float(e.dxf.center.y)
                r = float(e.dxf.radius)
                if r > 0:
                    steps = 64
                    pts = [(cx + r * math.cos(2 * math.pi * k / steps),
                            cy + r * math.sin(2 * math.pi * k / steps)) for k in range(steps)]
                    col = getattr(e.dxf, "color", 7)
                    if col == ORIGINAL_PLOT_COLOR:
                        plots["original"].append(pts)
                    elif col == FINAL_PLOT_COLOR:
                        plots["final"].append(pts)
                    else:
                        plots["other"].append(pts)
        except Exception:
            continue
    return plots

def extract_texts(msp: ezdxf.layouts.Modelspace) -> List[Dict]:
    """Copy over TEXT and MTEXT (content, insert, height, rotation)."""
    items = []
    # Single line TEXT
    for t in msp.query("TEXT"):
        try:
            items.append({
                "type": "TEXT",
                "text": t.dxf.text,
                "insert": (float(t.dxf.insert.x), float(t.dxf.insert.y)),
                "height": float(getattr(t.dxf, "height", TEXT_HEIGHT) or TEXT_HEIGHT),
                "rotation": float(getattr(t.dxf, "rotation", 0.0) or 0.0),
            })
        except Exception:
            continue
    # MTEXT
    for m in msp.query("MTEXT"):
        try:
            items.append({
                "type": "MTEXT",
                "text": m.text,  # full string (MTEXT handles own formatting)
                "insert": (float(m.dxf.insert.x), float(m.dxf.insert.y)),
                "height": float(getattr(m.dxf, "char_height", TEXT_HEIGHT) or TEXT_HEIGHT),
                "rotation": float(getattr(m.dxf, "rotation", 0.0) or 0.0),
                "width": float(getattr(m.dxf, "width", 0.0) or 0.0)
            })
        except Exception:
            continue
    return items

# =========================
# Redraw into a new DXF
# =========================

def redraw_map(src_path: str, dst_path: str):
    # Load input
    try:
        src_doc = ezdxf.readfile(src_path)
    except Exception as e:
        print(f"Failed to read input: {e}")
        sys.exit(1)
    msp_in = src_doc.modelspace()

    # Extract data
    plots = extract_plots(msp_in)
    road_polys, road_widths = extract_roads(msp_in, ROAD_LAYERS)
    texts = extract_texts(msp_in)

    # Process roads: merge, cluster, filter
    merged = merge_polylines(road_polys, MERGE_TOLERANCE)
    clustered = cluster_roads(merged, CLUSTER_DISTANCE)
    final_roads = [r for r in clustered if polyline_length(r) >= MIN_ROAD_LENGTH_UNITS]
    if MAX_ROADS_OUTPUT is not None:
        final_roads = final_roads[:MAX_ROADS_OUTPUT]

    # Determine global avg width from explicit widths (if present)
    explicit_w = [w for w in road_widths if w > 0]
    global_avg_width_units = float(np.mean(explicit_w)) if explicit_w else 0.0

    # Create output doc
    out_doc = ezdxf.new("R2018")
    out_doc.layers.new(name=LAYER_PLOTS_ORIG[0], dxfattribs={"color": LAYER_PLOTS_ORIG[1]})
    out_doc.layers.new(name=LAYER_PLOTS_FINAL[0], dxfattribs={"color": LAYER_PLOTS_FINAL[1]})
    out_doc.layers.new(name=LAYER_ROADS[0], dxfattribs={"color": LAYER_ROADS[1]})
    out_doc.layers.new(name=LAYER_TEXT[0], dxfattribs={"color": LAYER_TEXT[1]})
    out_doc.layers.new(name=LAYER_GUIDES[0], dxfattribs={"color": LAYER_GUIDES[1]})
    msp_out = out_doc.modelspace()

    # Helper: add closed polyline
    def add_poly(points: List[Tuple[float, float]], layer_name: str):
        if not points:
            return
        # LWPOLYLINE closed
        msp_out.add_lwpolyline(points + [points[0]], dxfattribs={"layer": layer_name, "closed": True})

    # Draw plots
    for pts in plots["original"]:
        add_poly(pts, LAYER_PLOTS_ORIG[0])
        if ADD_PLOT_AREA_LABELS:
            try:
                c = centroid(pts)
                a_units2 = polygon_area(pts)
                a_m2 = a_units2 * (SCALE_TO_METERS ** 2)
                msp_out.add_text(f"{a_m2:.2f} m²",
                                 dxfattribs={"height": TEXT_HEIGHT, "layer": LAYER_TEXT[0]}
                                 ).set_placement(c, align="MIDDLE_CENTER")
            except Exception:
                pass

    for pts in plots["final"]:
        add_poly(pts, LAYER_PLOTS_FINAL[0])
        if ADD_PLOT_AREA_LABELS:
            try:
                c = centroid(pts)
                a_units2 = polygon_area(pts)
                a_m2 = a_units2 * (SCALE_TO_METERS ** 2)
                msp_out.add_text(f"{a_m2:.2f} m²",
                                 dxfattribs={"height": TEXT_HEIGHT, "layer": LAYER_TEXT[0]}
                                 ).set_placement(c, align="MIDDLE_CENTER")
            except Exception:
                pass

    # If there were "other" colored plots, put them on GUIDES
    for pts in plots["other"]:
        add_poly(pts, LAYER_GUIDES[0])

    # Draw roads + optional width labels
    # If no explicit width in DXF, fall back to parallel-edge distance
    for idx, r in enumerate(final_roads, 1):
        # road geometry
        msp_out.add_lwpolyline(r, dxfattribs={"layer": LAYER_ROADS[0]})

        # length & width estimation for labeling
        length_units = polyline_length(r)
        length_m = length_units * SCALE_TO_METERS

        if global_avg_width_units > 0:
            w_units = global_avg_width_units
        else:
            # Estimate from the nearest parallel road
            _, w_units = find_parallel_edge(r, final_roads, PARALLEL_ANGLE_TOL)

        width_m = w_units * SCALE_TO_METERS

        if ADD_ROAD_DIM_LABELS:
            try:
                mid_i = len(r) // 2
                mid_pt = r[mid_i]
                label = f"L={length_m:.2f} m  W={width_m:.2f} m"
                msp_out.add_text(label,
                                 dxfattribs={"height": TEXT_HEIGHT, "layer": LAYER_TEXT[0]}
                                 ).set_placement(mid_pt, align="MIDDLE_CENTER")
            except Exception:
                pass

    # Copy text & mtext
    for t in texts:
        try:
            if t["type"] == "TEXT":
                tx = msp_out.add_text(
                    t["text"],
                    dxfattribs={"height": t["height"], "rotation": t["rotation"], "layer": LAYER_TEXT[0]}
                )
                tx.set_placement(t["insert"])
            elif t["type"] == "MTEXT":
                mt = msp_out.add_mtext(
                    t["text"],
                    dxfattribs={"char_height": t["height"], "rotation": t["rotation"], "layer": LAYER_TEXT[0]}
                )
                mt.set_location(t["insert"])
                if t.get("width", 0) > 0:
                    mt.dxf.width = t["width"]
        except Exception:
            continue

    # Save output
    try:
        out_doc.saveas(dst_path)
        print(f"✅ Clean map written to: {dst_path}")
        print(f"   Plots: {len(plots['original'])} original, {len(plots['final'])} final, {len(plots['other'])} other")
        print(f"   Roads: {len(final_roads)}")
        print(f"   Texts: {len(texts)}")
    except Exception as e:
        print(f"Failed to save output: {e}")
        sys.exit(2)

# =========================
# CLI
# =========================

def main():
    src = "CTP01(LALDARWAJA)FINAL.dxf"
    dst = "clean_map.dxf"
    redraw_map(src, dst)

if __name__ == "__main__":
    main()
