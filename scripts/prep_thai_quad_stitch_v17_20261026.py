"""Close one reviewed duplicate-vertex cloth crack in a separate local copy."""
import bpy,bmesh,json,hashlib,runpy,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from math import radians
ROOT=Path(__file__).resolve().parents[1]
AUDIT=json.loads((ROOT/'work/v16_meeting_resume_20261026.json').read_text())
R16=json.loads((ROOT/'reports/CHARACTER_THAI_STITCHED_PANEL_V16_20261026.json').read_text())
C=Path(globals()['PREP_WELD_PAYLOAD']);QAP=Path(globals()['PREP_WELD_QA']);QA=json.loads(QAP.read_text())
candidate_sha=hashlib.sha256(C.read_bytes()).hexdigest();assert QA['sha256']==candidate_sha and all(type(v)is bool and v for v in QA['checks'].values())
SOURCE=Path(AUDIT['library']);WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_QUAD_STITCH_V17_20261026.blend'
CP=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_QUAD_STITCH_V17_20261026.blend'
F=ROOT/'reports/thai_quad_stitch_v17_20261026';OUT=ROOT/'reports/CHARACTER_THAI_QUAD_STITCH_V17_20261026.json'
assert Path(bpy.data.filepath)==SOURCE and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256']
assert not any(p.exists()for p in (WORK,CP,F,OUT))
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
source=bpy.data.objects[R16['bodyObject']];scene16=bpy.data.scenes[R16['scene']];bpy.context.window.scene=scene16;bpy.context.view_layer.update()
snap=helper['_snapshot'](source.data);a=snap['arrays'];saved=json.loads((ROOT/'reports/thai_stitched_panel_v16_20261026/saved_body_payload.json').read_text())
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==saved['arraysSha256']
P=a['coordinates'];T=a['triangles'];W=helper['_weights'](source.data,len(source.vertex_groups));assert hashlib.sha256(W.tobytes()).hexdigest()==saved['weightsSha256']
with np.load(C)as n:payload={k:n[k].copy()for k in n.files}
TN=payload['candidate_triangles'].astype(np.int32)
face=17935;old_vertex=12195;target=12194
assert TN.shape==T.shape and np.array_equal(np.flatnonzero((TN!=T).any(1)),[face])
delta=np.argwhere(TN!=T);assert delta.shape==(1,2)and int(delta[0,0])==face
corner=int(delta[0,1]);assert int(T[face,corner])==old_vertex and int(TN[face,corner])==target
assert np.array_equal(np.sort(T[face]),[12146,12191,12195])and np.array_equal(np.sort(TN[face]),[12146,12191,12194])
assert np.count_nonzero(T==old_vertex)==1
lv=a['loopVertices'].reshape(-1);changed_loop=source.data.polygons[face].loop_start+corner
assert np.array_equal(lv.reshape(-1,3),T)
source_normals=a['cornerNormals'];target_normals=source_normals[lv==target];assert np.array_equal(target_normals,np.broadcast_to(target_normals[0],target_normals.shape))
UV={}
for layer in source.data.uv_layers:
 uv=a['uv:'+layer.name];copies=uv[lv==target];assert np.array_equal(copies,np.broadcast_to(copies[0],copies.shape));UV[layer.name]=uv.copy();UV[layer.name][changed_loop]=copies[0]
def points(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
before_pose=points(source)
shutil.copy2(SOURCE,CP);F.mkdir();shutil.copy2(C,F/'quad_candidate.npz');shutil.copy2(QAP,F/'independent_quad_qa.json')
# Point local autosaves at a new working file before any scene mutation.
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
scene=bpy.data.scenes.new('REVIEW_THAI_QUAD_STITCH_V17_20261026');scene.world=scene16.world
scene['PREP_role']='One duplicate-vertex crack welded in a full-avatar review copy; source scenes and runtime unchanged.'
arm=source.parent.copy();arm.data=source.parent.data.copy();arm.name='REVIEW_V17_Rig';scene.collection.objects.link(arm)
reference=source.copy();reference.name='REFERENCE_V17_Original_Crack';scene.collection.objects.link(reference);reference.parent=arm;reference.matrix_parent_inverse=source.matrix_parent_inverse.copy();reference.matrix_basis=source.matrix_basis.copy();next(m for m in reference.modifiers if m.type=='ARMATURE').object=arm
mesh=bpy.data.meshes.new('REVIEW_V17_Stitched_Body_Mesh');mesh.from_pydata(P.tolist(),[],TN.tolist());mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
for v in bm.verts:
 for g in np.flatnonzero(W[v.index]>0):v[deform][int(g)]=float(W[v.index,g])
bm.to_mesh(mesh);bm.free();mesh.update()
for mat in source.data.materials:mesh.materials.append(mat)
mesh.polygons.foreach_set('use_smooth',a['polygonSmooth'].reshape(-1));mesh.polygons.foreach_set('material_index',a['polygonMaterial'].reshape(-1))
for layer in source.data.uv_layers:
 new=mesh.uv_layers.new(name=layer.name);new.data.foreach_set('uv',UV[layer.name].reshape(-1));new.active_render=layer.active_render
mesh.uv_layers.active_index=source.data.uv_layers.active_index
normals=source_normals.copy();normals[changed_loop]=target_normals[0];mesh.normals_split_custom_set(normals.tolist())
for name in ('prep_source_face_index','prep_source_vertex_index'):
 attr=source.data.attributes.get(name)
 if attr:
  values=np.empty(len(attr.data),np.int32);attr.data.foreach_get('value',values);new=mesh.attributes.new(name,'INT',attr.domain);new.data.foreach_set('value',values)
obj=bpy.data.objects.new('REVIEW_V17_Avatar_With_Quad_Stitch',mesh);scene.collection.objects.link(obj)
for group in source.vertex_groups:obj.vertex_groups.new(name=group.name)
obj.parent=arm;obj.matrix_parent_inverse=source.matrix_parent_inverse.copy();obj.matrix_basis=source.matrix_basis.copy();mod=obj.modifiers.new('Armature','ARMATURE');mod.object=arm
for key in ('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):setattr(mod,key,getattr(next(m for m in source.modifiers if m.type=='ARMATURE'),key))
bpy.context.window.scene=scene;bpy.context.view_layer.update()
after=helper['_snapshot'](mesh)['arrays'];assert np.array_equal(after['coordinates'],P)and np.array_equal(after['triangles'],TN)and np.array_equal(helper['_weights'](mesh,len(obj.vertex_groups)),W)
assert all(np.array_equal(after['uv:'+k],v)for k,v in UV.items())
outside=np.ones(len(normals),bool);outside[changed_loop]=False;normal_error=float(abs(after['cornerNormals'][outside]-source_normals[outside]).max());assert normal_error<5e-4
q=points(obj);qr=points(reference);pose_error=float(np.linalg.norm(q-qr,axis=1).max());assert pose_error<1e-6
def edge_map(tri):
 out={}
 for fi,t in enumerate(tri):
  for x,y in zip(t,np.roll(t,-1)):out.setdefault(tuple(sorted((int(x),int(y)))),[]).append((fi,int(x),int(y)))
 return out
old_edges=edge_map(T);new_edges=edge_map(TN);seams=[tuple(sorted((12146,target))),tuple(sorted((12191,target)))]
assert all(len(new_edges[e])==2 and new_edges[e][0][1:]==tuple(reversed(new_edges[e][1][1:]))for e in seams)
old_open={e for e,v in old_edges.items()if len(v)==1};new_open={e for e,v in new_edges.items()if len(v)==1};assert not(new_open-old_open)and len(old_open-new_open)==4
assert not{e for e,v in new_edges.items()if len(v)>2}-{e for e,v in old_edges.items()if len(v)>2}
def normal_area(Q):
 tri=Q[TN[face]];cross=np.cross(tri[1]-tri[0],tri[2]-tri[0]);length=np.linalg.norm(cross);return cross/length,float(length*.5)
base_normal,base_area=normal_area(q);motion=[]
for bone_name,degrees in [('head',-15),('head',15),('chest',-10),('chest',10),('L_clavicle',-10),('L_clavicle',10),('L_upper_arm',-15),('L_upper_arm',15)]:
 bone=arm.pose.bones[bone_name];basis=bone.matrix_basis.copy();bone.matrix_basis=basis@Matrix.Rotation(radians(degrees),4,'Y'if bone_name=='head'else'X');bpy.context.view_layer.update()
 qp=points(obj);rp=points(reference);error=float(np.linalg.norm(qp-rp,axis=1).max());n,area=normal_area(qp);ratio=area/base_area;dot=float(n@base_normal)
 assert error<1e-6 and np.isfinite(qp).all()and area>1e-10 and .25<ratio<4 and dot>0
 motion.append({'bone':bone_name,'degrees':degrees,'allVertexPoseMaxErrorMeters':error,'seamGapMeters':0.0,'previousSplitVertexGapMeters':float(np.linalg.norm(rp[target]-rp[old_vertex])),'faceAreaRatioToStanding':ratio,'normalDotToStanding':dot})
 bone.matrix_basis=basis;bpy.context.view_layer.update()
np.savez_compressed(F/'integrated_surface.npz',vertices=P,triangles=TN,weights=W,posed=points(obj),changed_loop=np.array(changed_loop),changed_face=np.array(face))
reference.hide_render=True;reference.hide_set(True);obj.hide_render=False
bpy.context.window.scene=scene16;bpy.context.view_layer.update();assert not helper['_differences'](snap,helper['_snapshot'](source.data))and np.array_equal(helper['_weights'](source.data,len(source.vertex_groups)),W)
assert np.array_equal(points(source),before_pose)
bpy.context.window.scene=scene;bpy.context.view_layer.update()
camera=bpy.data.objects.new('REVIEW_V17_Camera',scene16.camera.data.copy());scene.collection.objects.link(camera);scene.camera=camera;camera.matrix_world=scene16.camera.matrix_world.copy()
for light in(o for o in scene16.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
# Keep the meeting undisturbed: no render, window creation, activation or desktop switch.
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
saved_arrays=helper['_snapshot'](mesh)['arrays'];bodyhash={k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in saved_arrays.items()}
record={'status':'one-cloth-crack-welded-local-review-copy-saved-awaiting-reopen','library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'sourceLibrary':str(SOURCE),'sourceSha256':AUDIT['sha256'],'sourceHistoricalSha256':R16['sha256'],'checkpoint':str(CP),'candidateSha256':candidate_sha,
 'scene':scene.name,'bodyObject':obj.name,'referenceObject':reference.name,'sourceObject':source.name,'changedFace':face,'changedCorner':corner,'oldTriangle':T[face].tolist(),'newTriangle':TN[face].tolist(),'oldVertex':old_vertex,'targetVertex':target,'changedLoop':changed_loop,'triangles':len(TN),'vertices':len(P),'unreferencedVertices':int(len(P)-len(np.unique(TN))),
 'sourceGeometryAndWeightsPreserved':True,'allReviewPositionsWeightsPreserved':True,'oneFaceCornerRemapped':True,'newBoundaryEdgesIntroduced':0,'closedBoundaryEdges':4,'sharedSeamEdges':seams,'seamWindingOpposite':True,'outsideNormalMaxComponentTransferError':normal_error,'allVertexPoseMaxErrorMeters':pose_error,
 'previousStandingSplitGapMeters':float(np.linalg.norm(qr[target]-qr[old_vertex])),'motionSamples':motion,'bodyArraysSha256':bodyhash,'weightsSha256':hashlib.sha256(W.tobytes()).hexdigest(),
 'meetingMode':{'newWindows':False,'windowActivationRequested':False,'desktopSwitchRequested':False,'heavyRendering':False},'sourceAndPreviousSceneUnchanged':True,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,
 'limits':'One scanner split in the sleeve is topologically welded. No whole-garment, posture, fingers, collision-body or native Walk approval. Render deferred during the user meeting; geometry inspection and motion tests are recorded separately.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256'];OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
