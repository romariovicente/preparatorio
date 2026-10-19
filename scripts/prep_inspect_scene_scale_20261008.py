import bpy,json
from pathlib import Path
from mathutils import Vector
scene=bpy.context.scene
rows=[]
for o in scene.objects:
    if o.type not in {'MESH','EMPTY'}:continue
    if o.name.startswith(('SUP_','REAL_','BLD_','INTERACTIVE_')) or o.instance_collection:
        rows.append({'name':o.name,'type':o.type,'dimensions':[round(v,3) for v in o.dimensions],'location':[round(v,3) for v in o.location],'scale':[round(v,4) for v in o.scale],'collections':[c.name for c in o.users_collection],'hidden':o.hide_get(),'hide_render':o.hide_render,'instance':o.instance_collection.name if o.instance_collection else None})
large=[r for r in rows if max(r['dimensions'])>40 and r['name'].startswith('SUP_')]
Path(bpy.data.filepath).parents[2].joinpath('reports/scene_scale_inspection_20261008.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'largeSuppliedObjects':large,'suppliedInstances':[r for r in rows if r['instance']],'active':bpy.context.active_object.name if bpy.context.active_object else None},ensure_ascii=False))
