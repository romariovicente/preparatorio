"""Refine a verified newly-created monument, preserving its first revision."""
from pathlib import Path
import bpy, json, hashlib, struct, shutil, math
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT/'art/blender/PREPARATORIO_FLORENCE_20261005.blend'
GLB = ROOT/'frontend/public/assets/monuments/PROP_Florence_Nightingale_Real_20261005.glb'
REPORT = ROOT/'reports/florence_monument_validation_20261005.json'
FRONT = ROOT/'reports/florence_monument_front_20261005.png'
REVERSE = ROOT/'reports/florence_monument_reverse_20261005.png'
CHECKPOINT = ROOT/'art/blender/checkpoints/FLORENCE_BEFORE_BRONZE_REPAIR_20261005'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bounds(objects):
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(p) for o in objects if o.type=='MESH' for p in o.bound_box]
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))

report=json.loads(REPORT.read_text(encoding='utf-8'))
if report['glb']['sha256']!=sha(GLB) or report['blend']['sha256']!=sha(BLEND):
    raise RuntimeError('Existing revision changed unexpectedly; preserve it and stop')
if CHECKPOINT.exists():raise FileExistsError(str(CHECKPOINT))
CHECKPOINT.mkdir(parents=True)
for path in (BLEND,GLB,REPORT,FRONT,REVERSE):
    target=CHECKPOINT/path.name
    assert target.resolve().is_relative_to(ROOT.resolve())
    shutil.copy2(path,target)

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene
collection=bpy.data.collections['PREP_FLORENCE_REAL_MONUMENT']
review=bpy.data.collections.get('PREP_FLORENCE_REVIEW_COLLECTION')
if review is None:
    review=bpy.data.collections.new('PREP_FLORENCE_REVIEW_COLLECTION')
    scene.collection.children.link(review)
for obj in list(collection.objects):
    if obj.name.startswith('REVIEW_'):
        collection.objects.unlink(obj)
        review.objects.link(obj)

for mat in bpy.data.materials:
    if mat.name.startswith('MAT_Florence_Real_Bronze_'):
        pbr=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for socket in ('Base Color','Metallic','Roughness'):
            for link in list(pbr.inputs[socket].links):mat.node_tree.links.remove(link)
        pbr.inputs['Base Color'].default_value=(.055,.045,.031,1)
        pbr.inputs['Metallic'].default_value=.80
        pbr.inputs['Roughness'].default_value=.59
        mat.diffuse_color=(.055,.045,.031,1)
ink=bpy.data.materials.new('MAT_Florence_Inscription_Dark_Bronze')
ink.use_nodes=True
ink.diffuse_color=(.020,.015,.007,1)
pbr=ink.node_tree.nodes['Principled BSDF']
pbr.inputs['Base Color'].default_value=ink.diffuse_color
pbr.inputs['Metallic'].default_value=.2
pbr.inputs['Roughness'].default_value=.65
for name in ('FLORENCE_Name','FLORENCE_Lifetime','FLORENCE_Tribute','FLORENCE_Game_Author'):
    obj=bpy.data.objects[name]
    obj.data.materials.clear()
    obj.data.materials.append(ink)

objects=list(collection.objects)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['PROP_Florence_Nightingale_Real_20261005']
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,
    export_yup=True,export_apply=True,export_animations=False,export_cameras=False,
    export_lights=False,export_extras=True,export_materials='EXPORT',
    export_draco_mesh_compression_enable=False)
scene.camera=bpy.data.objects['REVIEW_Camera_Front']
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
for camera_name,path in (('REVIEW_Camera_Front',FRONT),('REVIEW_Camera_Reverse',REVERSE)):
    scene.camera=bpy.data.objects[camera_name]
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)

validation=bpy.data.scenes.new('VALIDATE_FLORENCE_REFINED_GLB')
bpy.context.window.scene=validation
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(GLB))
new=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
low,high=bounds(new)
finite=all(math.isfinite(value) for o in new for v in o.data.vertices for value in v.co)
if len(new)!=43 or abs(low.z)>0.005 or abs(high.z-6.6)>0.005 or not finite:
    raise RuntimeError('Refined monument reimport invalid')
blob=GLB.read_bytes()
jslength,_=struct.unpack_from('<II',blob,12)
doc=json.loads(blob[20:20+jslength].rstrip(b'\x00 \t\r\n'))
report['blend'].update(bytes=BLEND.stat().st_size,sha256=sha(BLEND))
report['glb'].update(bytes=len(blob),sha256=sha(GLB),materials=len(doc.get('materials',[])),embeddedImages=len(doc.get('images',[])))
report['created']['materials']=6
report['actualGlbReimport'].update(materials=len(set(mat for o in new for mat in o.data.materials)),allVerticesFinite=finite)
report['refinement']={'checkpoint':str(CHECKPOINT),'bronzeMetallic':.8,'bronzeRoughness':.59,
    'sourceOrmLinksRemovedFromBronzeControls':True,'darkPortugueseInscriptions':True,'reviewFloorExcludedFromAssetCollection':True}
report['render']['visualReviewPending']=True
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
