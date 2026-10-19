import bpy,json
from pathlib import Path
from mathutils import Vector
rows=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.hide_get():continue
    corners=[o.matrix_world@Vector(v) for v in o.bound_box]
    minimum=[min(v[i] for v in corners) for i in range(3)]
    maximum=[max(v[i] for v in corners) for i in range(3)]
    size=[maximum[i]-minimum[i] for i in range(3)]
    if max(size)>40:
        rows.append({'name':o.name,'size':[round(v,2) for v in size],'center':[round((minimum[i]+maximum[i])/2,2) for i in range(3)],'parent':o.parent.name if o.parent else None,'collections':[c.name for c in o.users_collection]})
active=bpy.context.active_object
chain=[]
while active:
    chain.append({'name':active.name,'type':active.type,'location':list(active.location),'scale':list(active.scale),'collections':[c.name for c in active.users_collection]})
    active=active.parent
report={'largeMeshes':rows,'activeChain':chain}
Path(bpy.data.filepath).parents[2].joinpath('reports/scene_bounds_inspection_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
