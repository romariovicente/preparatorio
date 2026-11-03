"""Stitch a reviewed replacement panel into an avatar COPY, sharing seam IDs."""
import bpy,bmesh,json,hashlib,runpy,shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from math import radians
ROOT=Path(__file__).resolve().parents[1]
V15=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_SURFACE_V15_20261026.json').read_text())
A=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
C=Path(globals()['PREP_CANDIDATE']);QA_PATH=Path(globals()['PREP_QA'])
QA=json.loads(QA_PATH.read_text());candidate_sha=hashlib.sha256(C.read_bytes()).hexdigest()
assert QA['sha256']==candidate_sha and all(QA['checks'].values())
SOURCE=Path(V15['library']);WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_STITCHED_PANEL_V16_20261026.blend'
CHECKPOINT=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_STITCH_V16_20261026.blend'
F=ROOT/'reports/thai_stitched_panel_v16_20261026';OUT=ROOT/'reports/CHARACTER_THAI_STITCHED_PANEL_V16_20261026.json'
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==V15['sha256']
assert not any(p.exists()for p in (WORK,F,OUT))
if CHECKPOINT.exists():assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest()==V15['sha256']
with np.load(C)as n:d={k:n[k].copy()for k in n.files}
P=d['vertices'].astype(np.float32);T=d['triangles'].astype(np.int32);W=d['weights'].astype(np.float32)
ids=d['panel_vertex_source_indices'].astype(np.int32);removed=d['replacement_source_faces'].astype(np.int32);uv=d['uv'].astype(np.float32)
names=d['group_names'].tolist();assert uv.shape==(len(T)*3,2) and len(ids)==len(P)
original_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=original_scene;bpy.context.view_layer.update()
source=bpy.data.objects[A['sourceMesh']];helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
snapshot=helper['_snapshot'](source.data);sp=snapshot['arrays']['coordinates'];st=snapshot['arrays']['triangles'];sw=helper['_weights'](source.data,len(source.vertex_groups))
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in snapshot['arrays'].items()}==A['sourceArraysSha256']
assert hashlib.sha256(sw.tobytes()).hexdigest()==A['sourceWeightSha256']
assert names==[g.name for g in source.vertex_groups]
assert len(st)==len(source.data.polygons) and all(len(p.vertices)==3 for p in source.data.polygons)
reused=ids>=0;assert np.array_equal(P[reused],sp[ids[reused]]) and np.array_equal(W[reused],sw[ids[reused]])
old_uv=snapshot['arrays']['uv:'+source.data.uv_layers[0].name]
loop_vertices=snapshot['arrays']['loopVertices'].reshape(-1);vertex_uv=np.full((len(sp),2),np.nan,np.float32);vertex_uv[loop_vertices]=old_uv
reused_corners=reused[T.reshape(-1)];seam_uv_error=float(np.abs(uv[reused_corners]-vertex_uv[ids[T.reshape(-1)[reused_corners]]]).max());assert seam_uv_error<1e-7
assert (W>=0).all() and np.isfinite(W).all() and np.abs(W.sum(1)-1).max()<2e-6 and (W>0).sum(1).max()<=4
keep=np.ones(len(st),bool);keep[removed]=False;kept_ids=np.flatnonzero(keep)
mapping=ids.copy();mapping[~reused]=len(sp)+np.arange((~reused).sum())
fullP=np.concatenate([sp,P[~reused]]);fullW=np.concatenate([sw,W[~reused]]);fullT=np.concatenate([st[keep],mapping[T]])
loop_ids=np.concatenate([np.arange(source.data.polygons[int(i)].loop_start,source.data.polygons[int(i)].loop_start+3)for i in kept_ids])
def points(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();v=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
source_points=points(source)
if not CHECKPOINT.exists():shutil.copy2(SOURCE,CHECKPOINT)
F.mkdir();shutil.copy2(C,F/'panel_candidate.npz');shutil.copy2(QA_PATH,F/'independent_panel_qa.json')
scene=bpy.data.scenes.new('REVIEW_THAI_STITCHED_PANEL_V16_20261026');scene.world=original_scene.world
scene['PREP_role']='Actual shared-vertex garment panel replacement in an independent avatar copy. Original source and runtime remain unchanged.'
arm=source.parent.copy();arm.data=source.parent.data.copy();arm.name='REVIEW_V16_Rig';scene.collection.objects.link(arm)
reference=source.copy();reference.name='REFERENCE_V16_Original_Avatar';scene.collection.objects.link(reference)
reference.parent=arm;reference.matrix_parent_inverse=source.matrix_parent_inverse.copy();reference.matrix_basis=source.matrix_basis.copy()
next(m for m in reference.modifiers if m.type=='ARMATURE').object=arm
mesh=bpy.data.meshes.new('REVIEW_V16_Stitched_Body_Mesh');mesh.from_pydata(fullP.tolist(),[],fullT.tolist());mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
for v in bm.verts:
 for g in np.flatnonzero(fullW[v.index]>0):v[deform][int(g)]=float(fullW[v.index,g])
bm.to_mesh(mesh);bm.free();mesh.update()
for mat in source.data.materials:mesh.materials.append(mat)
smooth=np.r_[snapshot['arrays']['polygonSmooth'].reshape(-1)[keep],np.ones(len(T),bool)];mesh.polygons.foreach_set('use_smooth',smooth)
mesh.polygons.foreach_set('material_index',np.r_[snapshot['arrays']['polygonMaterial'].reshape(-1)[keep],np.zeros(len(T),np.int32)])
first_uv=snapshot['arrays']['uv:'+source.data.uv_layers[0].name]
for layer in source.data.uv_layers:
 old_uv=snapshot['arrays']['uv:'+layer.name];assert np.array_equal(first_uv,old_uv)
 new=mesh.uv_layers.new(name=layer.name);new.data.foreach_set('uv',np.concatenate([old_uv[loop_ids],uv]).reshape(-1));new.active_render=layer.active_render
mesh.uv_layers.active_index=source.data.uv_layers.active_index
normals=np.empty(len(mesh.loops)*3,np.float32);mesh.corner_normals.foreach_get('vector',normals);normals=normals.reshape(-1,3)
normals[:len(loop_ids)]=snapshot['arrays']['cornerNormals'][loop_ids]
# Blender averages custom normals across the same smooth fan. Seed new seam
# corners with the identical original boundary normal so outside shading stays.
vertex_normal=np.zeros((len(sp),3),np.float32)
for si in ids[reused]:
 copies=snapshot['arrays']['cornerNormals'][loop_vertices==si]
 assert np.array_equal(copies,np.broadcast_to(copies[0],copies.shape))
 vertex_normal[si]=copies[0]
normals[len(loop_ids)+np.flatnonzero(reused_corners)]=vertex_normal[ids[T.reshape(-1)[reused_corners]]]
mesh.normals_split_custom_set(normals.tolist())
obj=bpy.data.objects.new('REVIEW_V16_Avatar_With_Stitched_Panel',mesh);scene.collection.objects.link(obj)
for name in names:obj.vertex_groups.new(name=name)
obj.parent=arm;obj.matrix_parent_inverse=source.matrix_parent_inverse.copy();obj.matrix_basis=source.matrix_basis.copy()
mod=obj.modifiers.new('Armature','ARMATURE');mod.object=arm
source_mod=next(m for m in source.modifiers if m.type=='ARMATURE')
for key in ('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):setattr(mod,key,getattr(source_mod,key))
attr=mesh.attributes.new('prep_source_face_index','INT','FACE');attr.data.foreach_set('value',np.r_[kept_ids,np.full(len(T),-1,np.int32)])
attr=mesh.attributes.new('prep_source_vertex_index','INT','POINT');attr.data.foreach_set('value',np.r_[np.arange(len(sp),dtype=np.int32),np.full((~reused).sum(),-1,np.int32)])
actual=helper['_snapshot'](mesh)
assert np.array_equal(actual['arrays']['coordinates'],fullP) and np.array_equal(actual['arrays']['triangles'],fullT)
assert np.array_equal(helper['_weights'](mesh,len(names)),fullW)
for layer in source.data.uv_layers:assert np.array_equal(actual['arrays']['uv:'+layer.name][:len(loop_ids)],snapshot['arrays']['uv:'+layer.name][loop_ids])
normal_error=float(np.abs(actual['arrays']['cornerNormals'][:len(loop_ids)]-snapshot['arrays']['cornerNormals'][loop_ids]).max());assert normal_error<5e-4
for light in (o for o in original_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
camera=bpy.data.objects.new('REVIEW_V16_Camera',original_scene.camera.data.copy());scene.collection.objects.link(camera);scene.camera=camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=680;scene.render.resolution_y=760;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
camera.data.type='ORTHO';camera.data.ortho_scale=.74
bpy.context.window.scene=scene;bpy.context.view_layer.update()
q=points(obj);qref=points(reference);outside_error=float(np.linalg.norm(q[:len(sp)]-qref,axis=1).max());panel_error=float(np.linalg.norm(q[mapping]-d['expected_posed'],axis=1).max());assert outside_error<1e-6 and panel_error<1e-5
# Seam topology must use one shared vertex per corner, not coincident duplicates.
edge_faces={}
edge_directions={}
for fi,t in enumerate(fullT):
 for a,b in zip(t,np.roll(t,-1)):
  key=tuple(sorted((int(a),int(b))));edge_faces.setdefault(key,[]).append(fi);edge_directions.setdefault(key,[]).append((int(a),int(b)))
panel_boundary=d['boundary_edges'].astype(np.int32);seam_edges=np.sort(mapping[panel_boundary],axis=1)
assert all(len(edge_faces[tuple(e)])==2 and sum(fi>=len(kept_ids)for fi in edge_faces[tuple(e)])==1 for e in seam_edges)
assert all(edge_directions[tuple(e)][0]==tuple(reversed(edge_directions[tuple(e)][1])) for e in seam_edges)
old_edges={}
for t in st:
 for a,b in zip(t,np.roll(t,-1)):
  key=tuple(sorted((int(a),int(b))));old_edges[key]=old_edges.get(key,0)+1
old_boundary={e for e,count in old_edges.items()if count==1};new_boundary={e for e,faces in edge_faces.items()if len(faces)==1}
assert not(new_boundary-old_boundary)
closed_source_boundary_edges=sorted(old_boundary-new_boundary)
def panel_normals_areas(Q):
 tri=Q[mapping[T]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(cross,axis=1);return cross/np.maximum(length[:,None],1e-20),length*.5
base_normals,base_areas=panel_normals_areas(q)
motion=[]
for bone_name,degrees in [('head',-15),('head',15),('chest',-10),('chest',10),('L_clavicle',-10),('L_clavicle',10),('L_upper_arm',-15),('L_upper_arm',15)]:
 bone=arm.pose.bones[bone_name];basis=bone.matrix_basis.copy();bone.matrix_basis=basis @ Matrix.Rotation(radians(degrees),4,'Y'if bone_name=='head'else'X');bpy.context.view_layer.update()
 qp=points(obj);rp=points(reference);err=float(np.linalg.norm(qp[:len(sp)]-rp,axis=1).max());assert err<1e-6 and np.isfinite(qp).all()
 normals,areas=panel_normals_areas(qp);ratios=areas/base_areas;normal_dot=(normals*base_normals).sum(1)
 assert (areas>1e-10).all() and (ratios>.25).all() and (ratios<4).all() and (normal_dot>0).all()
 motion.append({'bone':bone_name,'degrees':degrees,'preservedSourceVerticesPoseMaxErrorMeters':err,'seamGapMeters':0.0,
  'minimumPanelAreaRatioToStanding':float(ratios.min()),'maximumPanelAreaRatioToStanding':float(ratios.max()),'minimumNormalDotToStanding':float(normal_dot.min())})
 bone.matrix_basis=basis;bpy.context.view_layer.update()
np.savez_compressed(F/'blender_integrated_surface.npz',vertices=fullP,triangles=fullT,weights=fullW,panel_to_body_vertex=mapping,source_faces_kept=kept_ids,posed=points(obj))
center=Vector((0,0,1.36));renders=[]
for angle,offset in [('front',(0,-3,0)),('back',(0,3,0)),('side',(3,0,0))]:
 camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
 for state in ('reference','stitched'):
  obj.hide_render=state=='reference';reference.hide_render=state!='reference'
  path=F/(angle+'_'+state+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
# Close-up uses the actual integrated avatar, not an isolated overlay.
panel_center=Vector(q[mapping].mean(0));camera.data.ortho_scale=.23;camera.location=panel_center+Vector((1,2,.2));camera.rotation_euler=(panel_center-camera.location).to_track_quat('-Z','Y').to_euler()
for state in ('reference','stitched'):
 obj.hide_render=state=='reference';reference.hide_render=state!='reference';path=F/('closeup_'+state+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
obj.hide_render=False;reference.hide_render=True;reference.hide_set(True)
bpy.context.window.scene=original_scene;bpy.context.view_layer.update()
assert not helper['_differences'](snapshot,helper['_snapshot'](source.data));assert np.array_equal(sw,helper['_weights'](source.data,len(names)))
assert np.linalg.norm(points(source)-source_points,axis=1).max()==0
bpy.context.window.scene=scene;bpy.context.view_layer.update()
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_overlays=False;space.region_3d.view_location=Vector((0,0,1.35));space.region_3d.view_distance=1.3;space.region_3d.view_rotation=(Vector((0,0,1.35))-Vector((2,3,1.65))).to_track_quat('-Z','Y');space.region_3d.view_perspective='PERSP'
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
record={'status':'actual-shared-vertex-panel-in-independent-avatar-copy-saved-awaiting-reopen-and-visual-review',
 'library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'sourceLibrary':str(SOURCE),'sourceSha256':V15['sha256'],'checkpoint':str(CHECKPOINT),'candidateSha256':candidate_sha,
 'scene':scene.name,'bodyObject':obj.name,'referenceObject':reference.name,'sourceObject':source.name,'sourceVertexCount':len(sp),'sourceFaceCount':len(st),
 'removedSourceFaces':removed.tolist(),'retainedSourceFaces':len(kept_ids),'panelVertices':len(P),'panelTriangles':len(T),'addedVertices':int((~reused).sum()),'sharedSeamEdges':len(seam_edges),
 'closedOriginalBoundaryEdges':closed_source_boundary_edges,'newBoundaryEdgesIntroduced':0,'seamWindingOpposite':True,
 'panelPredictionMaxErrorMeters':panel_error,'originalVerticesPoseMaxErrorMeters':outside_error,'outsideUVExact':True,'outsideNormalMaxComponentTransferError':normal_error,
 'sharedSeamUVMaxComponentError':seam_uv_error,'unreferencedOriginalVertexCount':int(len(fullP)-len(np.unique(fullT))),
 'standingMaximumInternalDihedralDegrees':QA['candidateStandingMaxDihedralDegrees'],'sourceMaximumInternalDihedralDegrees':QA['referenceSourcePanelMaxDihedralDegrees'],'dihedralTradeoff':QA['explicitTradeoff'],
 'originalAuthoringSourcePreserved':True,'originalWeightsPreserved':True,'motionSamples':motion,'renders':renders,
 'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,
 'limit':'Only the reviewed garment panel is reconstructed and actually stitched in a separate avatar copy. Other scan holes, high collar, full neutral posture, fingers and native Walk remain outside this increment. Original interior vertices are retained as unused reference vertices when their old faces are replaced.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==V15['sha256'];OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
