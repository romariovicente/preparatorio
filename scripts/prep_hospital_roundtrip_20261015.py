"""Preserve first GLB, export rounded geometry, then import it into its own QA scene."""
import bpy,contextlib,hashlib,io,json,shutil,struct,sys
from pathlib import Path
ROOT=Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
OUT=ROOT/'frontend/public/assets/environments/ENV_Hospital_Reception_Module_20261015.glb'
REPORT=ROOT/'reports/HOSPITAL_RECEPTION_20261015.json'
scene=bpy.data.scenes['PREP_HOSPITAL_RECEPTION_20261015']
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert 'PREP_HOSPITAL_GLB_QA_20261015' not in bpy.data.scenes
report=json.loads(REPORT.read_text(encoding='utf-8'))
assert hashlib.sha256(OUT.read_bytes()).hexdigest()==report['glbSha256']
backup=ROOT/'art/blender/checkpoints/HOSPITAL_FIRST_EXPORT_20261015.glb'
assert not backup.exists();shutil.copy2(OUT,backup)
assert hashlib.sha256(backup.read_bytes()).hexdigest()==report['glbSha256']
for window in bpy.context.window_manager.windows:window.scene=scene
for obj in scene.objects:obj.select_set(False)
for obj in scene.objects:
    if obj.type in ('MESH','EMPTY') and not obj.get('preview_reference') and not obj.name.startswith('HSP15_CHAIR_COLLIDER_'):
        obj.select_set(True)
scene.frame_set(1)
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):
    result=bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,
        export_yup=True,export_apply=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=True,
        export_cameras=False,export_lights=False,export_skins=False,export_extras=True)
assert 'FINISHED' in result
(ROOT/'reports/hospital_final_export_20261015.log').write_text(buffer.getvalue(),encoding='utf-8')
raw=OUT.read_bytes();length,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+length])
assert kind==0x4e4f534a
node=next(n for n in doc['nodes'] if n.get('name')=='HSP15_RECEPTION_BASE')
primitive=doc['meshes'][node['mesh']]['primitives'][0]
rounded_count=doc['accessors'][primitive['attributes']['POSITION']]['count']
assert rounded_count>24,'Reception desk must include its bevel geometry.'
clips=[a.get('name') for a in doc.get('animations',[])]
assert 'Door_Open' in clips and all('Room_Open_'+str(i).zfill(2) in clips for i in range(1,5))

qa=bpy.data.scenes.new('PREP_HOSPITAL_GLB_QA_20261015');qa.unit_settings.system='METRIC';qa.unit_settings.scale_length=1;qa.render.fps=30
qa['purpose']='Roundtrip QA of the exported hospital module; not another city building.'
for window in bpy.context.window_manager.windows:window.scene=qa
before_import=set(bpy.data.objects)
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):
    imported_result=bpy.ops.import_scene.gltf(filepath=str(OUT))
assert 'FINISHED' in imported_result
(ROOT/'reports/hospital_roundtrip_import_20261015.log').write_text(buffer.getvalue(),encoding='utf-8')
imported=list(set(bpy.data.objects)-before_import)
assert len(imported)>=len(doc['nodes'])
doors=[o for o in imported if o.name.startswith('HSP15_DOOR_PUBLIC_') and o.type=='MESH' and 'HANDLE' not in o.name and 'EDGE' not in o.name]
assert len(doors)==2
for obj in imported:
    obj['roundtrip_source_node']=obj.name;obj.name='QA_'+obj.name
qa.frame_set(1)
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
baseline=json.loads((ROOT/'art/blender/checkpoints/HOSPITAL_BEFORE_OBJECTS_20261015.json').read_text(encoding='utf-8'))
original=[bpy.data.objects[name] for name in baseline['state']]
assert state_hash(object_state(original))==baseline['hash'],'An earlier object changed.'
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report['firstExportPreserved']=str(backup)
report['firstExportBytes']=report['glbBytes'];report['firstExportSha256']=report['glbSha256']
report['glbBytes']=OUT.stat().st_size;report['glbSha256']=hashlib.sha256(OUT.read_bytes()).hexdigest()
report['modifiersAppliedOnExport']=True;report['roundedReceptionPositionCount']=rounded_count
report['animationClips']=clips
report['roundtrip']={'scene':qa.name,'objects':len(imported),'publicDoorMeshes':len(doors),'passed':True}
report['allScenes']=len(bpy.data.scenes);report['allObjects']=len(bpy.data.objects);report['savedMasterBytes']=MASTER.stat().st_size
report['status']='saved-render-reviewed-exported-and-reimported; separate prototype'
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PREP_HOSPITAL_ROUNDTRIP '+json.dumps({key:report[key] for key in ('glbBytes','glbSha256','roundedReceptionPositionCount','animationClips','roundtrip','allScenes','allObjects','savedMasterBytes','status')}))
