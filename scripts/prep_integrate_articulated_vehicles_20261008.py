"""Append validated editable vehicle parts; preserve all previous city data."""
import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
city=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
parent=bpy.data.collections.get('ARAP_15_ARTICULATED_VEHICLES_20261008')
if not parent:
    parent=bpy.data.collections.new('ARAP_15_ARTICULATED_VEHICLES_20261008');city.collection.children.link(parent)
sources={}
for name,path in [('VEH_SLS_Interactive_20261005','PREPARATORIO_CARS_INTERACTIVE_20261005.blend'),('VEH_Atlas_Interactive_20261005','PREPARATORIO_CARS_INTERACTIVE_20261005.blend'),('PREP_KAWASAKI_INTERACTIVE','PREPARATORIO_MOTORCYCLE_INTERACTIVE_20261007.blend')]:
    library=ROOT/'art/blender'/path
    key='PARTS_'+name
    collection=bpy.data.collections.get(key)
    if not collection:
        with bpy.data.libraries.load(str(library),link=False) as (available,loaded):
            assert name in available.scenes,available.scenes
            loaded.scenes=[name]
        source=loaded.scenes[0]
        collection=bpy.data.collections.new(key)
        for obj in source.objects:
            if obj.type in {'MESH','EMPTY'}:collection.objects.link(obj)
    sources[name]=collection
world=json.loads((ROOT/'frontend/src/config/realisticWorldManifest.json').read_text(encoding='utf-8'))
placements=[]
for item in world['environmentReplacements']:
    source=item['sourceId']
    key='VEH_SLS_Interactive_20261005' if source=='SUP_2010_mercedes_sls_amg' else 'VEH_Atlas_Interactive_20261005' if source=='SUP_volkswagen_atlas_teramont_cross_sport_2025' else 'PREP_KAWASAKI_INTERACTIVE' if source=='SUP_cyberpunk_kawasaki_ninja' else None
    if key:placements.append((item['id'],key,item['position'],item.get('rotation',[0,0,0])[1]))
placements += [('car','VEH_SLS_Interactive_20261005',[20,0,44],0),('mototaxi','PREP_KAWASAKI_INTERACTIVE',[-40,0,40],0)]
created=[]
for label,key,position,yaw in placements:
    name='INTERACTIVE_'+label
    if bpy.data.objects.get(name):continue
    obj=bpy.data.objects.new(name,None);parent.objects.link(obj)
    obj.instance_type='COLLECTION';obj.instance_collection=sources[key]
    obj.location=(position[0],-position[2],position[1]);obj.rotation_euler.z=yaw
    obj['part_asset']=key;obj['original_asset_preserved']=True;created.append(name)
# Keep prototypes as data, hiding only superseded visible derivatives.
for obj in city.objects:
    if obj.name.startswith(('VEH_Mototaxi','VEH_Car_','SUPPLACE_dealer-sports','SUPPLACE_dealer-suv','SUPPLACE_hospital-suv','SUPPLACE_moto-dealer')):
        obj.hide_set(True);obj.hide_render=True
for window in bpy.context.window_manager.windows:window.scene=city
dest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261008.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'saved':str(dest),'created':created,'placements':len(placements),'sourceCollections':list(sources),'sceneObjects':len(city.objects)}
(ROOT/'reports/live_articulated_vehicles_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
