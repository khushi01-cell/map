# Re-run analysis to list red polylines areas and centroids
import ezdxf
from shapely.geometry import Polygon
import pandas as pd

file_path = 'CTP01(LALDARWAJA)FINAL.dxf'

doc = ezdxf.readfile(file_path)
ms = doc.modelspace()

records = []

for ent in ms:
    if ent.dxftype() == 'LWPOLYLINE' and ent.dxf.color == 1 and ent.closed:
        pts = [tuple(v[:2]) for v in ent.get_points('xy')]
        if len(pts) < 3:
            continue
        poly = Polygon(pts)
        if poly.is_valid and poly.area>0:
            cx, cy = poly.centroid.x, poly.centroid.y
            records.append({'handle': ent.dxf.handle, 'area_m2': poly.area, 'centroid_x': cx, 'centroid_y': cy})

red_df = pd.DataFrame(records).sort_values('area_m2', ascending=False).reset_index(drop=True)
print(red_df.head(10))