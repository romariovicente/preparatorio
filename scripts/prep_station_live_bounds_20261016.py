import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
def scan(s):
 pts=[];allpts=[];meshcount=0;tris=0
 for o in s.objects:
  if o.type!='MESH':continue
  meshcount+=1;o.data.calc_loop_triangles();tris+=len(o.data.loop_triangles)
  used={i for p in o.data.polygons for i in p.vertices}
  pts.extend(o.matrix_world@o.data.vertices[i].co for i in used)
  allpts.extend(o.matrix_world@v.co for v in o.data.vertices)
 def bb(points):return [[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
 return {'meshes':meshcount,'triangles':tris,'faceBounds':bb(pts),'allBounds':bb(allpts)}
r={n:scan(bpy.data.scenes[n]) for n in ['PREP_STATION_SOURCE_20261016','PREP_STATION_LOD_20261016','PREP_STATION_QA_20261016']}
(ROOT/'reports/STATION_LIVE_BOUNDS_20261016.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
