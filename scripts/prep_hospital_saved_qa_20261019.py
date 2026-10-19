"""Independent Blender readback: no live UI, no writes to the saved blend files."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
standalone=ROOT/'art/blender/PREPARATORIO_HOSPITAL_CITY_20261019.blend'
master=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
original=json.loads(Path(json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())['stateSnapshot']).read_text())
with bpy.data.libraries.load(str(master),link=False) as (source,target):
    master_scenes=list(source.scenes);master_objects=set(source.objects)
assert 'PREP_HOSPITAL_CITY_20261019' in master_scenes and set(original)<=master_objects
bpy.ops.wm.open_mainfile(filepath=str(standalone),load_ui=False,use_scripts=False)
assert len(bpy.data.scenes)==1 and bpy.data.scenes[0].name=='PREP_HOSPITAL_CITY_20261019'
scene=bpy.data.scenes[0]
rigs=[o for o in scene.objects if o.type=='ARMATURE']
assert len(rigs)==2 and all(len(o.data.bones)==55 for o in rigs)
assert all(len(bpy.data.objects['HSC19_'+key+'_CHAR_'+key+'_DEMO_ROOT'].children_recursive)==30 for key in ('ANA','ROMARIO'))
missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert not missing, 'Standalone contains missing external image dependencies'
qa=bpy.data.scenes.new('PLATFORM_READBACK_QA');bpy.context.window.scene=qa
gltf=ROOT/'frontend/public/assets/environments/ENV_Hospital_Entrance_Platform_20261019.glb'
bpy.ops.import_scene.gltf(filepath=str(gltf));bpy.context.view_layer.update()
meshes=[o for o in qa.objects if o.type=='MESH'];assert len(meshes)==2
points=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
assert abs(low[2]+.26)<1e-5 and abs(high[2]-.012)<1e-5
report={'passed':True,'blenderVersion':bpy.app.version_string,'autoexecDisabled':True,
        'masterSceneCount':len(master_scenes),'masterObjectCount':len(master_objects),'originalObjectNamesPresent':len(original),
        'standaloneScenes':1,'standaloneObjects':len(scene.objects),'independentRigs':[{'name':o.name,'bones':55} for o in rigs],
        'standaloneBytes':standalone.stat().st_size,'standaloneSha256':hashlib.sha256(standalone.read_bytes()).hexdigest(),
        'missingExternalImages':missing,'platformReimportMeshCount':len(meshes),'platformBoundsBlender':{'min':low,'max':high},
        'savedBlendsModifiedByReadback':False}
(ROOT/'reports/HOSPITAL_SAVED_QA_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
