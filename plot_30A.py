import ezdxf
from shapely.geometry import Polygon
import numpy as np
from pathlib import Path

print("loading dxf file")
path = Path('CTP01(LALDARWAJA)FINAL.dxf')
doc = ezdxf.readfile(path)
ms = doc.modelspace()
print("iterating polylines")

polys = []
for e in ms:
    if e.dxftype() == 'LWPOLYLINE' and e.dxf.color == 1:
        pts = [(p[0], p[1]) for p in e]
        if e.closed: # ensure closed
            poly = Polygon(pts)
            if poly.is_valid and poly.area>0:
                polys.append((poly.area, pts))
print("found" , len(polys), "closed red polylines")
areas = [a for a,_ in polys]

print("areas", areas)
max_idx = int(np.argmax(areas))
max_area = areas[max_idx]
print("largest area", max_area)

# perimeter and bbox dims
poly_pts = polys[max_idx][1]
poly = Polygon(poly_pts)
perim = poly.length
minx,miny,maxx,maxy = poly.bounds
width = maxx-minx
height = maxy-miny
print("perimeter", perim)
print("bbox width", width)
print("bbox height", height)