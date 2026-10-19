"""Hide the localized auxiliary sphere, keeping its original geometry intact."""
import bpy,json,re,unicodedata
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
scene=bpy.context.scene
if scene.name!='PREP_JALECO_QA_20261014':
    raise RuntimeError('Expected dedicated QA scene, not another scene')
hidden=[]
actors=[]
for key,x in [('ROMARIO',-.9),('ANA',.9)]:
    root=bpy.data.objects[f'CHAR_{key}_DEMO_ROOT']
    root.scale=(1,1,1)
    root.location=(0,0,0)
    members=[o for o in scene.objects if o.name.startswith(key+'_')]
    for obj in members:
        name=unicodedata.normalize('NFKD',obj.get('asset_node_name',''))
        name=re.sub('[^a-z0-9]','',name.lower())
        if obj.type=='MESH' and not any(m.type=='ARMATURE' for m in obj.modifiers) and re.fullmatch(r'(icosphere|esferaicosaedrica)\d*(mesh)?',name):
            obj.hide_render=True
            obj.hide_set(True)
            obj['character_helper_hidden']=True
            hidden.append(obj.name)
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    visible=[o for o in members if o.type=='MESH' and not o.hide_render]
    points=[o.evaluated_get(depsgraph).matrix_world@Vector(v) for o in visible for v in o.evaluated_get(depsgraph).bound_box]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    scale=1.7/(high.z-low.z)
    root.scale=(scale,)*3
    root.location=(x-(low.x+high.x)*scale/2,-(low.y+high.y)*scale/2,-low.z*scale)
    bpy.context.view_layer.update()
    points=[o.evaluated_get(depsgraph).matrix_world@Vector(v) for o in visible for v in o.evaluated_get(depsgraph).bound_box]
    final_height=max(p.z for p in points)-min(p.z for p in points)
    if abs(final_height-1.7)>.0001:
        raise RuntimeError(f'Height mismatch: {final_height}')
    actors.append({'root':root.name,'height_m':final_height,'scale':scale})
for obj in scene.objects:
    if obj.type=='FONT' and obj.data.body=='55 ossos | 1,70 m':
        obj.location.z=.04
if len(hidden)!=2:
    raise RuntimeError(f'Expected two auxiliary spheres, found {hidden}')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/PREPARATORIO_PROJETO_20261014.blend'))
bpy.ops.render.render(write_still=True)
report_path=ROOT/'reports/blender_jaleco_live_20261014.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
report['localized_auxiliary_helpers_hidden']=hidden
report['actual_visible_actor_measurements']=actors
report['helper_geometry_preserved']=True
report['preview_after_helper_correction']=scene.render.filepath
report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'helpers_hidden':hidden,'actual_actor_measurements':actors,'preview':scene.render.filepath}))
