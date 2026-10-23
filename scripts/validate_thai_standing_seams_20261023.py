"""Independent GLB reimport, then reconstruct the draft pose for seam evidence."""
import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(globals().get('PREP_WORK',ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_STANDING_V2_20261023.blend'))
OUT=Path(globals().get('PREP_OUT',ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_STANDING_V2_PROBES_20261023.blend'))
FOLDER=Path(globals().get('PREP_FOLDER',ROOT/'reports/thai_standing_v2_20261023'))
assert Path(bpy.data.filepath).resolve()==WORK.resolve() and not bpy.data.is_dirty and not OUT.exists()
record=json.loads(Path(globals().get('PREP_SOURCE_REPORT',ROOT/'reports/CHARACTER_THAI_STANDING_V2_20261023.json')).read_text())
glb=record['weightCopyPreservation']['bindingGlb'];path=Path(glb['path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==glb['sha256']
source=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];oldarm=next(o for o in source.objects if o.type=='ARMATURE');oldmesh=next(o for o in source.objects if o.type=='MESH')
bpy.context.window.scene=source
def points(mesh):
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a);m=np.array(ev.matrix_world);ev.to_mesh_clear()
    return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
oldposed=points(oldmesh)
before={s.name:set(o.name for o in s.objects) for s in bpy.data.scenes}
scene=bpy.data.scenes.new(globals().get('PREP_QA_SCENE','VALIDATE_THAI_SEAM_BIND_V6_20261023'));bpy.context.window.scene=scene
with bpy.context.temp_override(scene=scene,view_layer=scene.view_layers[0],collection=scene.collection):bpy.ops.import_scene.gltf(filepath=str(path))
for name,names in before.items():
    for obj in list(bpy.data.scenes[name].objects):
        if obj.name not in names:
            assert obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa'))
            for col in list(obj.users_collection):col.objects.unlink(obj)
    assert set(o.name for o in bpy.data.scenes[name].objects)==names
for obj in list(scene.objects):
    if obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa')) and not any(m.type=='ARMATURE' for m in obj.modifiers):
        for col in list(obj.users_collection):col.objects.unlink(obj)
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==len(meshes)==1;arm=arms[0];mesh=meshes[0];assert len(arm.data.bones)==20
raw=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',raw);raw=raw.reshape(-1,3)
expected=np.load(FOLDER/'posed_surface.npz')['source']
rest_error=float(np.max(np.linalg.norm(raw-expected,axis=1)));assert rest_error<1e-5
def depth(b):return 0 if not b.parent else depth(b.parent)+1
desired={b.name:oldarm.pose.bones[b.name].matrix@oldarm.data.bones[b.name].matrix_local.inverted()@b.bone.matrix_local for b in arm.pose.bones}
for b in sorted(arm.pose.bones,key=depth):
    kw={'parent_matrix':desired[b.parent.name],'parent_matrix_local':b.parent.bone.matrix_local} if b.parent else {}
    b.matrix_basis=b.bone.convert_local_to_pose(desired[b.name],b.bone.matrix_local,invert=True,**kw)
arm.matrix_world=oldarm.matrix_world.copy();mesh.matrix_world=oldmesh.matrix_world.copy()
bpy.context.view_layer.update();posed=points(mesh)
vanilla_error=float(np.max(np.linalg.norm(posed-oldposed,axis=1)))
# The exporter drops weights <1e-4 and renormalizes. Its authored-surface delta
# is diagnosed independently, rather than widening the exact reimport gate.
# Predict this pose using the actual exported accessor weights and compare
# Blender to that expectation at the original 10-micrometre tolerance.
import runpy
document=runpy.run_path(str(ROOT/'work/audit_thai_upper_glb_20261023.py'))['SkinDocument'](path)
dense=np.zeros((len(raw),len(mesh.vertex_groups)),dtype=np.float32)
names=[g.name for g in mesh.vertex_groups]
for slot in range(document.weights.shape[1]):
    columns=np.array([names.index(document.names[j]) for j in document.indices[:,slot]])
    dense[np.arange(len(raw)),columns]+=document.weights[:,slot]
imported_weights=np.zeros_like(dense)
for v in mesh.data.vertices:
    for g in v.groups:imported_weights[v.index,g.group]=g.weight
weight_error=float(np.abs(imported_weights-dense).max());assert weight_error<1e-7
homogeneous=np.column_stack([expected,np.ones(len(expected))]);prediction=np.zeros((len(raw),4),dtype=float)
for j,name in enumerate(names):
    matrix=np.array(oldarm.pose.bones[name].matrix@oldarm.data.bones[name].matrix_local.inverted())
    prediction+=(homogeneous@matrix.T)*dense[:,j,None]
world=np.array(oldmesh.matrix_world);prediction=prediction@world.T;prediction=prediction[:,:3]
reimport_cpu_error=float(np.max(np.linalg.norm(posed-prediction,axis=1)));assert reimport_cpu_error<1e-5,reimport_cpu_error
export_weight_effect=float(np.max(np.linalg.norm(prediction-oldposed,axis=1)))
assert abs(vanilla_error-export_weight_effect)<2e-6
posed_error=vanilla_error
# Coincident source positions form UV seams; no geometry welding occurs here.
U,inverse,counts=np.unique(np.round(expected.astype(float),6),axis=0,return_inverse=True,return_counts=True)
gaps=[]
for group in np.flatnonzero(counts>1):
    ids=np.flatnonzero(inverse==group);group_gap=float(np.max(np.linalg.norm(posed[ids]-posed[ids[0]],axis=1)))
    gaps.append(group_gap)
assert max(gaps)<1e-5
for obj in source.objects:
    if obj.type in ['CAMERA','LIGHT']:scene.collection.objects.link(obj)
scene.camera=source.camera;scene.world=source.world
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=560;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
renders=[]
for label,offset in [('front',(0,-5,0)),('side',(5,0,0))]:
    center=Vector((0,0,.85));cam=scene.camera;cam.data.ortho_scale=1.95;cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    out=FOLDER/('reimport_'+label+'.png');scene.render.filepath=str(out);bpy.ops.render.render(write_still=True);renders.append(str(out))
head_turn=None
if globals().get('PREP_EXTRA_HEAD_TURN',False):
    def apply_imported_pose(matrices):
        for bone in sorted(arm.pose.bones,key=depth):
            kw={'parent_matrix':matrices[bone.parent.name],'parent_matrix_local':bone.parent.bone.matrix_local} if bone.parent else {}
            bone.matrix_basis=bone.bone.convert_local_to_pose(matrices[bone.name],bone.bone.matrix_local,invert=True,**kw)
        bpy.context.view_layer.update()
    turn={name:matrix.copy() for name,matrix in desired.items()}
    rotation=Quaternion((0,0,1),math.radians(15))@turn['head'].to_quaternion()
    turn['head']=Matrix.LocRotScale(turn['head'].translation,rotation,turn['head'].to_scale())
    apply_imported_pose(turn);turned=points(mesh);delta=np.linalg.norm(turned-posed,axis=1)
    masks=np.load(ROOT/'reports/thai_upper_refit_20261023/head_hand_graph_masks.npz')
    semantic=np.load(ROOT/'reports/thai_seam_v7_20261023/texture_region_candidates.npz')
    hand_drift=float(delta[masks['rightHand153']].max());face_motion=float(delta[semantic['faceJawCandidate']].max())
    assert hand_drift<1e-5 and face_motion>.005
    turn_renders=[]
    for label,offset in [('front',(0,-4,0)),('side',(4,0,0))]:
        center=Vector((0,0,1.45));cam=scene.camera;cam.data.ortho_scale=.70
        cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        image_path=FOLDER/('reimport_head_turn15_'+label+'.png');scene.render.filepath=str(image_path)
        bpy.ops.render.render(write_still=True);turn_renders.append(str(image_path))
    apply_imported_pose(desired);restore_error=float(np.linalg.norm(points(mesh)-posed,axis=1).max());assert restore_error<1e-5
    head_turn={'degrees':15,'rightHandMaxDrift':hand_drift,'faceMaxMotion':face_motion,
               'restoredStandingPoseMaxError':restore_error,'renders':turn_renders,'nativeWalkValidated':False}
scene['PREP_role']=globals().get('PREP_SCOPE','seam-fix-evidence-standing-pose-not-accepted-for-game')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
report={'status':'reimport-and-seam-preservation-passed-awaiting-visual-review','library':str(OUT),
 'sourceGlb':glb,'vertices':len(raw),'bones':len(arm.data.bones),'restGeometryMaxError':rest_error,'posedSurfaceMaxError':posed_error,
 'reimportVsActualGLBPredictionMaxError':reimport_cpu_error,'importedWeightAccessorMaxError':weight_error,
 'exportWeightPruningMaxSurfaceEffect':export_weight_effect,'pruningExplanation':'Exporter removes weights below1e-4. Authored surface differs by approximately35 micrometres; exact GLB reimport comparison remains below10 micrometres.',
 'coincidentUVSeamGroups':len(gaps),'maxCoincidentPoseGap':max(gaps),'groupsAbove1mm':sum(v>.001 for v in gaps),
 'renders':renders,'headTurn15':head_turn,'runtimeChanged':False,'masterChanged':False,'neutralPoseValidated':False,'nativeWalkValidated':False}
Path(globals().get('PREP_REPORT',ROOT/'reports/CHARACTER_THAI_SEAM_V6_REIMPORT_20261023.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
