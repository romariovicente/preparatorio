"""Fix the verified classroom labels facing and save an interior review camera."""
from pathlib import Path
import bpy,json,math,hashlib,struct,shutil
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
BLEND=ROOT/'art/blender/PREPARATORIO_CLASSROOM_FUTURISTIC_20261007.blend'
ARCH=ROOT/'frontend/public/assets/environments/ENV_Classroom_Futuristic_20261007.glb'
REPORT=ROOT/'reports/classroom_futuristic_validation_20261007.json'
PREVIEW=ROOT/'reports/classroom_futuristic_20261007.png'
CLOSE=ROOT/'reports/classroom_student_pose_20261007.png'
checkpoint=ROOT/'art/blender/checkpoints/CLASSROOM_BEFORE_LABEL_FACING_REPAIR_20261007'
if checkpoint.exists():raise FileExistsError('Prior refinement preserved; inspect before repeating')
checkpoint.mkdir(parents=True)
for path in (BLEND,ARCH,REPORT):shutil.copy2(path,checkpoint/path.name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads(REPORT.read_text(encoding='utf8'))
bpy.ops.wm.open_mainfile(filepath=str(BLEND));scene=bpy.context.scene
for o in scene.objects:
    if o.type=='FONT':o.rotation_euler=(math.pi/2,0,math.pi)
camera=scene.camera;camera.location=(5.6,5.0,3.3);camera.data.lens=22
camera.rotation_euler=(Vector((0,-1.2,1.1))-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
collections=[bpy.data.collections[name] for name in ('PREP_CLASSROOM_ARCHITECTURE','PREP_CLASSROOM_FURNITURE','PREP_CLASSROOM_EDUCATIONAL')]
bpy.ops.object.select_all(action='DESELECT')
objects=[o for c in collections for o in c.objects]
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.gltf(filepath=str(ARCH),export_format='GLB',use_selection=True,use_active_scene=True,export_extras=True,
    export_animations=False,export_current_frame=True,export_apply=True,export_cameras=False,export_lights=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ARCH));bpy.context.view_layer.update()
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
finite=all(math.isfinite(v) for o in meshes for p in o.data.vertices for v in p.co)
if not finite or len(meshes)!=389:raise RuntimeError('Refined architecture reimport failed')
asset=report['assets'][0];asset['bytes']=ARCH.stat().st_size;asset['sha256']=sha(ARCH)
asset['actualReimport']['passed']=True;asset['actualReimport']['meshObjects']=len(meshes)
asset['actualReimport']['triangles']=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
bpy.ops.wm.open_mainfile(filepath=str(BLEND));scene=bpy.context.scene
scene.render.filepath=str(PREVIEW);bpy.ops.render.render(write_still=True)
camera=scene.camera;original_position=camera.location.copy();original_rotation=camera.rotation_euler.copy();original_lens=camera.data.lens
camera.location=(1.3,-1.08,1.9);camera.data.lens=48
camera.rotation_euler=(Vector((0,.1,.8))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.filepath=str(CLOSE)
bpy.ops.render.render(write_still=True)
camera.location=original_position;camera.rotation_euler=original_rotation;camera.data.lens=original_lens
scene.render.resolution_x=768;scene.render.resolution_y=576;scene.render.filepath=str(PREVIEW)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
report['blend'].update(bytes=BLEND.stat().st_size,sha256=sha(BLEND))
report['render']['studentCloseup']=str(CLOSE);report['render']['labelFacingRepaired']=True
report['checkpointBeforeLabelRepair']=str(checkpoint)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('CLASSROOM_REFINED_SAVED',flush=True)
