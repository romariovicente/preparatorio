"""Finish the staged hierarchy and author the shared hospital entrance platform."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
OUT=ROOT/'frontend/public/assets/environments/ENV_Hospital_Entrance_Platform_20261019.glb'
assert not OUT.exists()
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
scene=bpy.data.scenes['PREP_HOSPITAL_CITY_20261019']
attempt=bpy.data.scenes['PREP_HOSPITAL_CITY_20261019_ATTEMPT1']
checkpoint=json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())
original=json.loads(Path(checkpoint['stateSnapshot']).read_text())
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
assert state_hash(object_state([o for o in bpy.data.objects if o.name in original]))==checkpoint['stateHash']
for window in bpy.context.window_manager.windows:window.scene=scene
# An interrupted copy retained source parents. Confine those generated objects
# to the retained attempt, and remove their duplicate descendants from the final stage.
fixed=[]
for obj in list(attempt.objects):
    if obj.parent and obj.parent.name in original:
        basis=obj.matrix_basis.copy();inverse=obj.matrix_parent_inverse.copy()
        parent=bpy.data.objects.get('HSC19_ATTEMPT1_HSC19_ROMARIO_'+obj.parent.name)
        assert parent and parent in set(attempt.objects)
        obj.parent=parent;obj.matrix_parent_inverse=inverse;obj.matrix_basis=basis;fixed.append(obj.name)
retained=bpy.data.collections.new('HSC19_ATTEMPT1_RETAINED_DUPLICATES');attempt.collection.children.link(retained)
duplicates=[]
for obj in list(scene.objects):
    if obj.name.startswith('HSC19_ROMARIO_HSC19_ATTEMPT1_'):
        matrix=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=matrix
        for col in list(obj.users_collection):col.objects.unlink(obj)
        retained.objects.link(obj);obj['retained_from_incomplete_attempt']=True;duplicates.append(obj.name)
anchor=bpy.data.objects['HSC19_HOSPITAL_ANCHOR']
lift=.26-anchor.location.z
# Raise only newly authored/staged roots; a resumed export never raises them twice.
for obj in list(scene.objects):
    if obj.parent is not None:continue
    action=obj.animation_data.action if obj.animation_data else None
    shifted=False
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        if curve.data_path=='location' and curve.array_index==2:
                            for point in curve.keyframe_points:
                                point.co.y+=lift;point.handle_left.y+=lift;point.handle_right.y+=lift
                            shifted=True
    if not shifted:obj.location.z+=lift
assert abs(anchor.location.z-.26)<1e-5
platform=bpy.data.collections.new('HSC19_ENTRANCE_PLATFORM');scene.collection.children.link(platform)
mat=bpy.data.materials.new('HSC19_Entrance_Concrete');mat.use_nodes=True
node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node.inputs['Base Color'].default_value=(.40,.45,.44,1)
node.inputs['Roughness'].default_value=.78
def mesh(name,vertices,faces):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);platform.objects.link(obj);obj.parent=anchor;data.materials.append(mat)
    obj['walkable']=True;obj['hospital_entrance_platform']=True
    return obj
faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]
ramp=mesh('HSC19_ENTRY_RAMP',[(-1.6,-16.10,-.26),(1.6,-16.10,-.26),(1.6,-12.10,-.26),(-1.6,-12.10,-.26),
              (-1.6,-16.10,-.25),(1.6,-16.10,-.25),(1.6,-12.10,.012),(-1.6,-12.10,.012)],faces)
footing=mesh('HSC19_FOUNDATION',[(-18.075,-12.075,-.26),(18.075,-12.075,-.26),(18.075,12.075,-.26),(-18.075,12.075,-.26),
              (-18.075,-12.075,-.012),(18.075,-12.075,-.012),(18.075,12.075,-.012),(-18.075,12.075,-.012)],faces)
# Export a local-coordinate companion asset, excluding all rigs and scene anchors.
export_scene=bpy.data.scenes.new('PREP_HOSPITAL_PLATFORM_EXPORT_20261019')
for window in bpy.context.window_manager.windows:window.scene=export_scene
for obj in (ramp,footing):
    copy=obj.copy();copy.parent=None;copy.matrix_parent_inverse.identity();copy.matrix_basis=obj.matrix_basis.copy()
    export_scene.collection.objects.link(copy);copy.select_set(True)
bpy.context.view_layer.update()
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,
    export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
assert OUT.exists()
for window in bpy.context.window_manager.windows:window.scene=scene
scene.frame_set(180);bpy.context.view_layer.update()
config_path=ROOT/'frontend/src/config/hospitalReception.json'
config=json.loads(config_path.read_text(encoding='utf-8'));config['position']=[48,.26,-38]
config['entrancePlatform']={'asset':'/assets/environments/'+OUT.name,'rampWidth':3.2,'rampLength':4,
    'innerZ':12.10,'outerZ':16.10,'innerTopY':.012,'outerTopY':-.25,'foundationTopY':-.012,
    'reason':'Raised foundation covers legacy road surfaces up to 0.23m; ramp joins base ground at 0.01m'}
config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert state_hash(object_state([o for o in bpy.data.objects if o.name in original]))==checkpoint['stateHash']
standalone=ROOT/'art/blender/PREPARATORIO_HOSPITAL_CITY_20261019.blend'
assert not standalone.exists()
bpy.data.libraries.write(str(standalone),{scene},fake_user=True,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report={'scene':scene.name,'anchorBlenderXYZ':list(anchor.location),'runtimePositionThreeXYZ':config['position'],
        'platformGlb':str(OUT),'bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'foundationTopAbsoluteY':.26-.012,'floorAbsoluteY':.272,'rampOuterAbsoluteY':.01,
        'rampLengthMeters':4,'rampWidthMeters':3.2,'originalObjectsPreserved':len(original),
        'attemptParentLinksConfinedThisRun':len(fixed),'duplicateAttemptMeshesRetainedOutsideFinalScene':sum(len(c.objects) for c in attempt.collection.children if c.name.startswith('HSC19_ATTEMPT1_RETAINED_DUPLICATES')),
        'standalone':str(standalone),'standaloneBytes':standalone.stat().st_size,
        'master':str(MASTER),'masterBytes':MASTER.stat().st_size,
        'status':'saved-and-exported-awaiting-render-and-roundtrip',
        'architecturalOrAccessibilityCertification':False}
(ROOT/'reports/HOSPITAL_PLATFORM_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
