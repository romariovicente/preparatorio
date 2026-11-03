"""Import a separately rebuilt cloth-fit study; preserve every earlier avatar."""
import bpy,json,hashlib,shutil,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_PATCH_V14_20261026.json').read_text())
ANNOT=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
SOURCE=Path(PREVIOUS['library'])
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COLLAR_SURFACE_V15_20261026.blend'
CHECKPOINT=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_SURFACE_V15_20261026.blend'
F=ROOT/'reports/thai_collar_surface_v15_20261026'
OUT=ROOT/'reports/CHARACTER_THAI_COLLAR_SURFACE_V15_20261026.json'
CANDIDATE=Path(globals()['PREP_CANDIDATE'])
QA_PATH=Path(globals()['PREP_QA']);BVH_PATH=Path(globals()['PREP_BVH'])
QA=json.loads(QA_PATH.read_text());BVH=json.loads(BVH_PATH.read_text())
CANDIDATE_SHA=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
assert QA['sha256']==BVH['sha256']==CANDIDATE_SHA
assert all(QA['checks'].values()) and all(BVH['checks'].values())
SOURCE_AUDIT=json.loads((ROOT/'work/qa_thai_collar_fit_v15_20261026/live_v14_saved_state_audit.json').read_text())
SOURCE_SHA=SOURCE_AUDIT['currentSha256']
assert all(SOURCE_AUDIT['checks'].values()) and not SOURCE_AUDIT['dirty']
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve() and not bpy.data.is_dirty
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
assert not any(p.exists() for p in (WORK,OUT,F/'blender_surface.npz'))
assert not bpy.data.scenes.get('REVIEW_THAI_COLLAR_SURFACE_V15_20261026')
if CHECKPOINT.exists():assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()==SOURCE_SHA
if F.exists():assert {p.name for p in F.iterdir()} <= {'candidate_surface.npz','source_saved_state_audit.json','independent_surface_qa.json','actual_surface_bvh.json','candidate_construction.json'}
with np.load(CANDIDATE) as data: d={k:data[k].copy() for k in data.files}
P=d['vertices'].astype(np.float32);T=d['triangles'].astype(np.int32);W=d['weights'].astype(np.float32)
names=[str(n) for n in d['group_names']]
assert P.ndim==2 and P.shape[1]==3 and T.shape[1]==3 and W.shape==(len(P),20)
assert np.isfinite(P).all() and np.isfinite(W).all() and (W>=0).all()
assert np.abs(W.sum(1)-1).max()<2e-6 and (W>0).sum(1).max()<=4
assert not W[:,[names.index('head'),names.index('neck')]].any()
assert (T>=0).all() and (T<len(P)).all() and len(np.unique(T))==len(P)
original_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023']
bpy.context.window.scene=original_scene
source=bpy.data.objects[ANNOT['sourceMesh']];source_arm=source.parent
old_patch=bpy.data.objects[PREVIOUS['patchObject']]
assert names==[g.name for g in old_patch.vertex_groups]
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
source_snapshot=helper['_snapshot'](source.data)
source_weights=helper['_weights'](source.data,len(source.vertex_groups))
old_patch_snapshot=helper['_snapshot'](old_patch.data)
old_patch_weights=helper['_weights'](old_patch.data,len(old_patch.vertex_groups))

def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    values=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',values)
    matrix=np.array(ev.matrix_world);ev.to_mesh_clear()
    return values.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]

source_points=points(source)
def freeze_file(src,dst):
    if dst.exists():assert hashlib.sha256(src.read_bytes()).hexdigest()==hashlib.sha256(dst.read_bytes()).hexdigest()
    else:shutil.copy2(src,dst)
freeze_file(SOURCE,CHECKPOINT);F.mkdir(exist_ok=True)
freeze_file(CANDIDATE,F/'candidate_surface.npz')
freeze_file(ROOT/'work/qa_thai_collar_fit_v15_20261026/live_v14_saved_state_audit.json',F/'source_saved_state_audit.json')
freeze_file(QA_PATH,F/'independent_surface_qa.json');freeze_file(BVH_PATH,F/'actual_surface_bvh.json')
freeze_file(CANDIDATE.with_suffix('.json'),F/'candidate_construction.json')
edit=bpy.data.scenes.new('REVIEW_THAI_COLLAR_SURFACE_V15_20261026')
edit['PREP_role']='Independent continuous white cloth fit study, shown with complete unchanged avatar. Not an accepted replacement or game export.'
edit.world=original_scene.world
arm=source_arm.copy();arm.data=source_arm.data.copy();arm.name='STUDY_V15_Cloth_Rig';edit.collection.objects.link(arm)
context=source.copy();context.data=source.data.copy();context.name='CONTEXT_V15_Unchanged_Avatar';edit.collection.objects.link(context)
context.parent=arm;context.matrix_parent_inverse=source.matrix_parent_inverse.copy();context.matrix_basis=source.matrix_basis.copy()
next(m for m in context.modifiers if m.type=='ARMATURE').object=arm
mesh=bpy.data.meshes.new('STUDY_V15_Continuous_White_Cloth_Mesh');mesh.from_pydata(P.tolist(),[],T.tolist());mesh.update()
mesh.polygons.foreach_set('use_smooth',np.ones(len(T),bool))
uv=mesh.uv_layers.new(name='ClothStudyUV')
assert d['uv'].shape==(len(T)*3,2);uv.data.foreach_set('uv',d['uv'].astype(np.float32).reshape(-1))
material=bpy.data.materials.new('STUDY_V15_White_Cloth');material.use_nodes=True
principled=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
principled.inputs['Base Color'].default_value=(.86,.86,.86,1);principled.inputs['Roughness'].default_value=.85
if 'Sheen Weight' in principled.inputs:principled.inputs['Sheen Weight'].default_value=.16
material.diffuse_color=(.86,.86,.86,1);mesh.materials.append(material)
cloth=bpy.data.objects.new('STUDY_V15_Continuous_Fitted_White_Cloth',mesh);edit.collection.objects.link(cloth)
cloth.parent=arm;cloth.matrix_parent_inverse=Matrix.Identity(4);cloth.matrix_basis=Matrix.Identity(4)
for name in names:cloth.vertex_groups.new(name=name)
for v in range(len(P)):
    for g in np.flatnonzero(W[v]>0):cloth.vertex_groups[int(g)].add([v],float(W[v,g]),'REPLACE')
mod=cloth.modifiers.new('Armature','ARMATURE');mod.object=arm
for key in ('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):
    setattr(mod,key,getattr(old_patch.modifiers[0],key))
cloth['PREP_candidate_only']=True
cloth['PREP_scope']='New supported surface fitted in pose space and bound back to the existing rig. Original scan and shirt are fully retained for context and comparison; no holes are claimed repaired by covering.'
if 'boundary_vertex_indices' in d:
    boundary=np.zeros(len(P),np.int32);boundary[d['boundary_vertex_indices']]=1
    attr=mesh.attributes.new('prep_fit_boundary','INT','POINT');attr.data.foreach_set('value',boundary)
for light in (o for o in original_scene.objects if o.type=='LIGHT'):edit.collection.objects.link(light)
camera=bpy.data.objects.new('STUDY_V15_Camera',original_scene.camera.data.copy());edit.collection.objects.link(camera);edit.camera=camera
edit.render.engine='BLENDER_EEVEE';edit.render.resolution_x=660;edit.render.resolution_y=740;edit.render.resolution_percentage=100
edit.render.image_settings.file_format='PNG';edit.view_settings.view_transform='AgX';camera.data.type='ORTHO';camera.data.ortho_scale=.74
bpy.context.window.scene=edit;bpy.context.view_layer.update()
fitted=points(cloth);prediction_error=float(np.linalg.norm(fitted-d['expected_posed'],axis=1).max());assert prediction_error<1e-5
context_error=float(np.linalg.norm(points(context)-source_points,axis=1).max());assert context_error<1e-5
np.savez_compressed(F/'blender_surface.npz',vertices=P,triangles=T,weights=W,group_names=np.array(names),posed=fitted)
center=Vector((0,0,1.36));renders=[]
for angle,offset in [('front',(0,-3,0)),('back',(0,3,0)),('side',(3,0,0))]:
    camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    for state in ('reference','with_study'):
        cloth.hide_render=(state=='reference')
        path=F/(angle+'_'+state+'.png');edit.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
cloth.hide_render=False
# Independent rig head-motion samples; the source rig is never edited.
bone=arm.pose.bones['head'];old_mode=bone.rotation_mode;old_basis=bone.matrix_basis.copy()
motion=[]
for degrees in (-15,15):
    from mathutils import Matrix
    from math import radians
    bone.matrix_basis=old_basis @ Matrix.Rotation(radians(degrees),4,'Y');bpy.context.view_layer.update()
    q=points(cloth);delta=float(np.linalg.norm(q-fitted,axis=1).max())
    motion.append({'headDegrees':degrees,'maxClothMovementMeters':delta,'finite':bool(np.isfinite(q).all())})
    camera.location=center+Vector((3,0,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    path=F/('side_head_'+str(degrees)+'.png');edit.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
    bone.matrix_basis=old_basis;bpy.context.view_layer.update()
bone.rotation_mode=old_mode
# An explicitly isolated close-up documents only the new study surface.
context.hide_render=True;patch_center=Vector(fitted.mean(0));camera.data.ortho_scale=.165
camera.location=patch_center+Vector((0,3,0));camera.rotation_euler=(patch_center-camera.location).to_track_quat('-Z','Y').to_euler()
path=F/'isolated_new_cloth_surface.png';edit.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
context.hide_render=False;camera.data.ortho_scale=.74
camera.location=center+Vector((0,3,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.window.scene=original_scene;bpy.context.view_layer.update()
assert not helper['_differences'](source_snapshot,helper['_snapshot'](source.data))
assert np.array_equal(source_weights,helper['_weights'](source.data,len(source.vertex_groups)))
assert not helper['_differences'](old_patch_snapshot,helper['_snapshot'](old_patch.data))
assert np.array_equal(old_patch_weights,helper['_weights'](old_patch.data,len(old_patch.vertex_groups)))
assert float(np.linalg.norm(points(source)-source_points,axis=1).max())==0
bpy.context.window.scene=edit;bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_overlays=False
            space.region_3d.view_location=Vector((0,0,1.35));space.region_3d.view_distance=1.30
            space.region_3d.view_rotation=(Vector((0,0,1.35))-Vector((2,3,1.65))).to_track_quat('-Z','Y')
            space.region_3d.view_perspective='PERSP'
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
report={'status':'independent-continuous-cloth-fit-study-saved-awaiting-boundary-replacement-review',
 'library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'sourceLibrary':str(SOURCE),
 'sourceSha256':SOURCE_SHA,'originalV14ReportSha256':PREVIOUS['sha256'],'sourceSavedStateAudit':str(F/'source_saved_state_audit.json'),
 'checkpoint':str(CHECKPOINT),'candidateSha256':hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
 'candidate':str(F/'candidate_surface.npz'),'scene':edit.name,'clothObject':cloth.name,'contextObject':context.name,
 'vertices':len(P),'triangles':len(T),'predictionMaxErrorMeters':prediction_error,'contextPoseMaxErrorMeters':context_error,
 'independentSurfaceQA':str(F/'independent_surface_qa.json'),'actualSurfaceBVH':str(F/'actual_surface_bvh.json'),
 'sourceMeshUnchanged':True,'sourceWeightsUnchanged':True,'sourcePoseUnchanged':True,'V14PatchUnchanged':True,
 'clothHasHeadWeights':bool((W[:,names.index('head')]>0).any()),'headMotion':motion,'renders':renders,
 'runtimeChanged':False,'masterChanged':False,'GLBExported':False,'remoteOperations':False,
 'limit':'The study has full-avatar reference/context renders and a labelled isolated close-up. The original avatar is unchanged, and its complete context copy remains visible in the saved scene. Continuity of the study does not prove closed seams, collision-free full clothing, a neutral pose or native Walk.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
