"""Run through the live Blender MCP. Preserve previous art and append validated assets."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
for window in bpy.context.window_manager.windows:window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
parent=bpy.data.collections.get('ARAP_13_REAL_MONUMENTS_20261007')
if not parent:
    parent=bpy.data.collections.new('ARAP_13_REAL_MONUMENTS_20261007');scene.collection.children.link(parent)
records=json.loads((ROOT/'frontend/src/config/monumentAssets.json').read_text(encoding='utf-8'))
libraries={'PROP_Brain_Real_20261005':('PREPARATORIO_BRAIN_20261005.blend','PREP_Brain_Anatomical_20261005'),'PROP_Florence_Nightingale_Real_20261005':('PREPARATORIO_FLORENCE_20261005.blend','PREP_FLORENCE_REAL_MONUMENT')}
created=[]
for record in records:
    assert record['reimportValidated']
    filename,name=libraries[record['id']]
    collection=bpy.data.collections.get(name)
    if not collection:
        with bpy.data.libraries.load(str(ROOT/'art/blender'/filename),link=False) as (available,loaded):
            assert name in available.collections,(name,available.collections)
            loaded.collections=[name]
        collection=loaded.collections[0]
    for i,point in enumerate(record['positions']):
        instanceName=record['id']+'_CITY_'+str(i)
        if bpy.data.objects.get(instanceName):continue
        instance=bpy.data.objects.new(instanceName,None);parent.objects.link(instance)
        instance.instance_type='COLLECTION';instance.instance_collection=collection
        instance.location=(point[0],-point[2],point[1]);instance['verified_glb']=record['url'];instance['sha256']=record['sha256'];created.append(instanceName)
    for obj in scene.objects:
        if any(obj.name.startswith(p) for p in record['hidePrefixes']):obj.hide_set(True);obj.hide_render=True
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.shading.type='MATERIAL';space.clip_end=3000
            space.region_3d.view_distance=175;space.region_3d.view_location=Vector((0,0,8))
dest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261007.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'file':str(dest),'version':bpy.app.version_string,'scene':scene.name,'sceneObjects':len(scene.objects),'created':created,'metricScale':scene.unit_settings.scale_length,'collections':[c.name for c in scene.collection.children]}
(ROOT/'reports/live_resume_20261007.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
