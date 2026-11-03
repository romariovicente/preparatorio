"""Join six exact cap boundary aliases in a copied avatar; leave the seventh."""
import bpy,bmesh,json,hashlib,shutil,runpy
import numpy as np
from pathlib import Path
from mathutils import Matrix
from math import radians
ROOT=Path(__file__).resolve().parents[1]
PRIOR=json.loads((ROOT/'reports/CHARACTER_THAI_CLOTH_SEAM_V18_20261026.json').read_text())
AUDIT=json.loads((ROOT/'work/v18_before_v19_audit_20261026.json').read_text())
C=Path(globals()['PREP_CAP_PAYLOAD']);QAP=Path(globals()['PREP_CAP_QA']);QA=json.loads(QAP.read_text());csha=hashlib.sha256(C.read_bytes()).hexdigest()
assert QA['sha256']==csha and len(QA['checks'])>=5 and all(type(v)is bool and v for v in QA['checks'].values())
SOURCE=Path(AUDIT['library']);WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_PARTIAL_CAP_JOIN_V19_20261026.blend'
CP=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_CAP_JOIN_V19_20261026.blend';F=ROOT/'reports/thai_partial_cap_join_v19_20261026';OUT=ROOT/'reports/CHARACTER_THAI_PARTIAL_CAP_JOIN_V19_20261026.json'
assert Path(bpy.data.filepath)==SOURCE and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256']
assert not any(p.exists()for p in(WORK,CP,F,OUT))
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));source=bpy.data.objects[PRIOR['bodyObject']];source_scene=bpy.data.scenes[PRIOR['scene']]
bpy.context.window.scene=source_scene;bpy.context.view_layer.update();snapshot=h['_snapshot'](source.data);a=snapshot['arrays'];P=a['coordinates'];T=a['triangles'];W=h['_weights'](source.data,len(source.vertex_groups))
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==PRIOR['bodyArraysSha256']and hashlib.sha256(W.tobytes()).hexdigest()==PRIOR['weightsSha256']
with np.load(C)as n:TN=n['candidate_triangles'].copy().astype(np.int32)
assert TN.shape==T.shape
delta=np.argwhere(TN!=T);faces=np.unique(delta[:,0]);old=T[tuple(delta.T)];target=TN[tuple(delta.T)];mapping={int(x):int(y)for x,y in zip(old,target)}
assert len(delta)==12 and len(faces)==5 and len(mapping)==6 and not(set(mapping)&set(mapping.values()))
assert all(mapping[int(x)]==int(y)for x,y in zip(old,target))
canonical=np.arange(len(P),dtype=np.int32)
for x,y in mapping.items():canonical[x]=y
assert np.array_equal(TN,canonical[T])and np.array_equal(P[old],P[target])and np.array_equal(W[old],W[target])
assert 29974 not in mapping and 9755 not in mapping and 29974 not in mapping.values()and 9755 not in mapping.values()
assert np.any(TN==29974)and np.any(TN==9755)
assert all(len(set(map(int,t)))==3 for t in TN[faces])
lv=a['loopVertices'].reshape(-1);assert np.array_equal(lv.reshape(-1,3),T);loops=np.array([source.data.polygons[int(f)].loop_start+int(k)for f,k in delta])
seed_normals=[]
for y in target:
 copies=a['cornerNormals'][lv==y];assert len(copies)>0 and np.array_equal(copies,np.broadcast_to(copies[0],copies.shape));seed_normals.append(copies[0])
seed_normals=np.array(seed_normals,np.float32)
for layer in source.data.uv_layers:
 uv=a['uv:'+layer.name]
 for loop,y in zip(loops,target):
  copies=uv[lv==y];assert np.array_equal(copies,np.broadcast_to(copies[0],copies.shape))and np.array_equal(uv[loop],copies[0])
assert np.unique(a['polygonMaterial']).tolist()==[0]
def points(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
source_pose=points(source)
shutil.copy2(SOURCE,CP);F.mkdir();shutil.copy2(C,F/'cap_candidate.npz');shutil.copy2(QAP,F/'independent_cap_qa.json')
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
scene=bpy.data.scenes.new('REVIEW_THAI_PARTIAL_CAP_JOIN_V19_20261026');scene.world=source_scene.world
scene['PREP_role']='Six exact alias pairs joined between an existing cap and shirt. Seventh pair remains open; no complete garment approval.'
arm=source.parent.copy();arm.data=source.parent.data.copy();arm.name='REVIEW_V19_Rig';scene.collection.objects.link(arm)
reference=source.copy();reference.name='REFERENCE_V19_Separate_Cap';scene.collection.objects.link(reference);reference.parent=arm;reference.matrix_parent_inverse=source.matrix_parent_inverse.copy();reference.matrix_basis=source.matrix_basis.copy();next(m for m in reference.modifiers if m.type=='ARMATURE').object=arm
mesh=bpy.data.meshes.new('REVIEW_V19_Partially_Joined_Body_Mesh');mesh.from_pydata(P.tolist(),[],TN.tolist());mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
for vertex in bm.verts:
 for g in np.flatnonzero(W[vertex.index]>0):vertex[deform][int(g)]=float(W[vertex.index,g])
bm.to_mesh(mesh);bm.free();mesh.update()
for mat in source.data.materials:mesh.materials.append(mat)
mesh.polygons.foreach_set('use_smooth',a['polygonSmooth'].reshape(-1));mesh.polygons.foreach_set('material_index',a['polygonMaterial'].reshape(-1))
for layer in source.data.uv_layers:
 new=mesh.uv_layers.new(name=layer.name);new.data.foreach_set('uv',a['uv:'+layer.name].reshape(-1));new.active_render=layer.active_render
mesh.uv_layers.active_index=source.data.uv_layers.active_index
normals=a['cornerNormals'].copy();old_seed=normals[loops].copy();normals[loops]=seed_normals;mesh.normals_split_custom_set(normals.tolist())
for name in('prep_source_face_index','prep_source_vertex_index'):
 attr=source.data.attributes.get(name)
 if attr:
  values=np.empty(len(attr.data),np.int32);attr.data.foreach_get('value',values);new=mesh.attributes.new(name,'INT',attr.domain);new.data.foreach_set('value',values)
body=bpy.data.objects.new('REVIEW_V19_Avatar_Partial_Cap_Union',mesh);scene.collection.objects.link(body)
for group in source.vertex_groups:body.vertex_groups.new(name=group.name)
body.parent=arm;body.matrix_parent_inverse=source.matrix_parent_inverse.copy();body.matrix_basis=source.matrix_basis.copy();mod=body.modifiers.new('Armature','ARMATURE');mod.object=arm
for key in('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):setattr(mod,key,getattr(next(m for m in source.modifiers if m.type=='ARMATURE'),key))
bpy.context.window.scene=scene;bpy.context.view_layer.update();actual=h['_snapshot'](mesh)['arrays']
assert np.array_equal(actual['coordinates'],P)and np.array_equal(actual['triangles'],TN)and np.array_equal(h['_weights'](mesh,len(body.vertex_groups)),W)
for layer in source.data.uv_layers:assert np.array_equal(actual['uv:'+layer.name],a['uv:'+layer.name])
outside=np.ones(len(normals),bool);outside[loops]=False;outside_normal_error=float(abs(actual['cornerNormals'][outside]-a['cornerNormals'][outside]).max());assert outside_normal_error<5e-4
def edge_map(triangles):
 result={}
 for fi,t in enumerate(triangles):
  for x,y in zip(t,np.roll(t,-1)):result.setdefault(tuple(sorted((int(x),int(y)))),[]).append((fi,int(x),int(y)))
 return result
old_edges=edge_map(T);new_edges=edge_map(TN);predicted_edges=edge_map(canonical[T]);assert new_edges==predicted_edges
old_open={e for e,v in old_edges.items()if len(v)==1};new_open={e for e,v in new_edges.items()if len(v)==1}
raw_added=sorted(new_open-old_open);raw_removed=sorted(old_open-new_open);seams=sorted(e for e,v in new_edges.items()if len(v)==2 and len(old_edges.get(e,[]))==1)
assert len(raw_added)==2 and len(raw_removed)==12 and len(old_open)-len(new_open)==10 and len(seams)==5
assert all(new_edges[e][0][1:]==tuple(reversed(new_edges[e][1][1:]))for e in seams)
assert not{e for e,v in new_edges.items()if len(v)>2}-{e for e,v in old_edges.items()if len(v)>2}
def duplicates(triangles):
 rows,count=np.unique(np.sort(triangles,axis=1),axis=0,return_counts=True);return{tuple(map(int,row))for row in rows[count>1]}
assert not(duplicates(TN)-duplicates(T))
q=points(body);qr=points(reference);vertex_error=float(np.linalg.norm(q-qr,axis=1).max());surface_error=float(np.linalg.norm(q[TN]-qr[T],axis=2).max());assert vertex_error<1e-6 and surface_error==0.0
pending_gap=float(np.linalg.norm(q[29974]-q[9755]));assert pending_gap==float(np.linalg.norm(qr[29974]-qr[9755]))
motion=[]
for bone_name,degrees in[('head',-15),('head',15),('chest',-10),('chest',10),('R_clavicle',-10),('R_clavicle',10),('R_upper_arm',-15),('R_upper_arm',15)]:
 bone=arm.pose.bones[bone_name];basis=bone.matrix_basis.copy();bone.matrix_basis=basis@Matrix.Rotation(radians(degrees),4,'Y'if bone_name=='head'else'X');bpy.context.view_layer.update();qp=points(body);rp=points(reference)
 error=float(np.linalg.norm(qp[TN]-rp[T],axis=2).max());assert error==0.0 and np.isfinite(qp).all()
 tri=qp[TN[faces]];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5;assert(areas>1e-10).all()
 pg=float(np.linalg.norm(qp[29974]-qp[9755]));assert pg==float(np.linalg.norm(rp[29974]-rp[9755]))
 motion.append({'bone':bone_name,'degrees':degrees,'allTriangleCornerPositionsMaxErrorMeters':error,'sharedPairGapMeters':float(np.linalg.norm(qp[old]-qp[target],axis=1).max()),'pendingSeventhGapMeters':pg,'pendingGapUnchanged':True,'minimumCapTriangleAreaM2':float(areas.min())})
 bone.matrix_basis=basis;bpy.context.view_layer.update()
np.savez_compressed(F/'integrated_surface.npz',vertices=P,triangles=TN,weights=W,posed=points(body),changed_faces=faces,changed_corners=delta,old_vertices=np.array(list(mapping)),target_vertices=np.array(list(mapping.values())))
reference.hide_render=True;reference.hide_set(True)
bpy.context.window.scene=source_scene;bpy.context.view_layer.update();assert not h['_differences'](snapshot,h['_snapshot'](source.data))and np.array_equal(h['_weights'](source.data,len(source.vertex_groups)),W)and np.array_equal(points(source),source_pose)
bpy.context.window.scene=scene;bpy.context.view_layer.update();camera=bpy.data.objects.new('REVIEW_V19_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);scene.camera=camera;camera.matrix_world=source_scene.camera.matrix_world.copy()
for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
saved=h['_snapshot'](mesh)['arrays'];report={'status':'six-exact-cap-pairs-joined-in-local-copy-seventh-pending-awaiting-reopen','library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'sourceLibrary':str(SOURCE),'sourceSha256':AUDIT['sha256'],'checkpoint':str(CP),'candidateSha256':csha,
 'scene':scene.name,'bodyObject':body.name,'referenceObject':reference.name,'sourceObject':source.name,'changedFaces':faces.tolist(),'changedCorners':delta.tolist(),'oldToTarget':mapping,'changedLoopIndices':loops.tolist(),'triangles':len(TN),'vertices':len(P),'unreferencedVertices':int(len(P)-len(np.unique(TN))),
 'allStoredPositionsWeightsUVPreserved':True,'capFacesNotAddedOrRemoved':True,'oldBoundaryCount':len(old_open),'newBoundaryCount':len(new_open),'rawAddedBoundaryKeys':raw_added,'rawRemovedBoundaryKeys':raw_removed,'netBoundaryReduction':10,'newlySharedEdges':seams,'completeCanonicalIncidencesMatch':True,'pendingSeventhPair':[29974,9755],'pendingSeventhGapMeters':pending_gap,'pendingPairUnchanged':True,
 'outsideNormalMaxComponentTransferError':outside_normal_error,'changedNormalSeedMaxComponentDifference':float(abs(old_seed-seed_normals).max()),'allVertexPoseMaxErrorMeters':vertex_error,'allTriangleCornerPoseMaxErrorMeters':surface_error,'motionSamples':motion,
 'bodyArraysSha256':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in saved.items()},'weightsSha256':hashlib.sha256(W.tobytes()).hexdigest(),'sourcePreserved':True,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,
 'meetingMode':{'newWindows':False,'windowActivationRequested':False,'desktopSwitchRequested':False,'heavyRendering':False},'limit':'Partial topological union of an already-present five-face cap. Six exact pairs are shared; the seventh and four residual boundary segments remain pending. Two new raw boundary keys are exact endpoint renamings, not new geometric holes. Surface position/UV and prior overlap are unchanged; full textured appearance, whole clothing, anatomy and native Walk remain unapproved.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256'];OUT.write_text(json.dumps(report,indent=2));print(json.dumps(report))
