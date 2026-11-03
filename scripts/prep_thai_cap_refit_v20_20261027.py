"""Controlled last-corner sleeve refit, with original per-loop UVs preserved."""
import bpy,bmesh,json,hashlib,shutil,runpy,numpy as np
from pathlib import Path
from mathutils import Matrix
from math import radians
ROOT=Path(__file__).resolve().parents[1]
PRIOR=json.loads((ROOT/'reports/CHARACTER_THAI_PARTIAL_CAP_JOIN_V19_20261026.json').read_text());AUDIT=json.loads((ROOT/'work/v19_headless_resume_20261027.json').read_text())
C=ROOT/'work/qa_thai_cap_refit_v20_20261027/cap_refit_v20_preflight.npz';QAP=ROOT/'work/qa_thai_cap_refit_v20_review_20261027/cap_refit_v20_independent_audit.json'
QA=json.loads(QAP.read_text());csha=hashlib.sha256(C.read_bytes()).hexdigest();assert QA['candidateSHA256']==csha and len(QA['checks'])>=20 and all(type(v)is bool and v for v in QA['checks'].values())
SOURCE=Path(AUDIT['library']);WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_CLOSED_CAP_V20_20261027.blend';CP=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_CAP_REFIT_V20_20261027.blend'
F=ROOT/'reports/thai_cap_refit_v20_20261027';OUT=ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_20261027.json'
assert bpy.app.background and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256'];assert not any(p.exists()for p in(WORK,CP,F,OUT))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));source=bpy.data.objects[PRIOR['bodyObject']];source_scene=bpy.data.scenes[PRIOR['scene']];bpy.context.window.scene=source_scene;bpy.context.view_layer.update()
snap=h['_snapshot'](source.data);a=snap['arrays'];P=a['coordinates'];T=a['triangles'];W=h['_weights'](source.data,len(source.vertex_groups))
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==PRIOR['bodyArraysSha256']and hashlib.sha256(W.tobytes()).hexdigest()==PRIOR['weightsSha256']
with np.load(C)as n:payload={k:n[k].copy()for k in n.files}
TN=payload['candidate_triangles'].astype(np.int32);delta=np.argwhere(TN!=T);expected_delta=np.array([[42674,0],[42675,1],[42678,1]],np.int32);assert np.array_equal(delta,expected_delta)
canonical=np.arange(len(P),dtype=np.int32);canonical[29974]=9755;assert np.array_equal(TN,canonical[T]);faces=np.unique(delta[:,0]);loops=np.array([source.data.polygons[int(f)].loop_start+int(k)for f,k in delta])
assert np.array_equal(a['loopVertices'].reshape(-1,3),T)and not np.any(TN==29974)
bind_movement=float(np.linalg.norm(P[29974]-P[9755]));assert bind_movement<=.001
names=payload['source_uv_layer_names'].tolist();assert names==[l.name for l in source.data.uv_layers]
for index,name in enumerate(names):
 assert np.array_equal(a['uv:'+name],payload['source_corner_uv_native'][index])and np.array_equal(payload['candidate_corner_uv_native'][index],a['uv:'+name])
assert np.array_equal(a['cornerNormals'],payload['source_corner_normals'])
requested_normals=payload['candidate_corner_normals'];assert np.array_equal(np.flatnonzero(np.max(abs(requested_normals-a['cornerNormals']),axis=1)>0),loops)
def points(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
source_pose=points(source)
shutil.copy2(SOURCE,CP);F.mkdir();shutil.copy2(C,F/'cap_refit_candidate.npz');shutil.copy2(QAP,F/'independent_cap_refit_qa.json')
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
scene=bpy.data.scenes.new('REVIEW_THAI_CLOSED_CAP_V20_20261027');scene.world=source_scene.world
scene['PREP_role']='Controlled submillimeter last-corner refit of an existing sleeve cap; not a whole-garment approval.'
arm=source.parent.copy();arm.data=source.parent.data.copy();arm.name='REVIEW_V20_Rig';scene.collection.objects.link(arm)
reference=source.copy();reference.name='REFERENCE_V20_Pending_Cap_Corner';scene.collection.objects.link(reference);reference.parent=arm;reference.matrix_parent_inverse=source.matrix_parent_inverse.copy();reference.matrix_basis=source.matrix_basis.copy();next(m for m in reference.modifiers if m.type=='ARMATURE').object=arm
mesh=bpy.data.meshes.new('REVIEW_V20_Closed_Cap_Body_Mesh');mesh.from_pydata(P.tolist(),[],TN.tolist());mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();deform=bm.verts.layers.deform.verify()
for v in bm.verts:
 for g in np.flatnonzero(W[v.index]>0):v[deform][int(g)]=float(W[v.index,g])
bm.to_mesh(mesh);bm.free();mesh.update()
for mat in source.data.materials:mesh.materials.append(mat)
mesh.polygons.foreach_set('use_smooth',a['polygonSmooth'].reshape(-1));mesh.polygons.foreach_set('material_index',a['polygonMaterial'].reshape(-1))
for layer in source.data.uv_layers:
 new=mesh.uv_layers.new(name=layer.name);new.data.foreach_set('uv',a['uv:'+layer.name].reshape(-1));new.active_render=layer.active_render
mesh.uv_layers.active_index=source.data.uv_layers.active_index;mesh.normals_split_custom_set(requested_normals.tolist())
for name in('prep_source_face_index','prep_source_vertex_index'):
 attr=source.data.attributes.get(name)
 if attr:
  values=np.empty(len(attr.data),np.int32);attr.data.foreach_get('value',values);new=mesh.attributes.new(name,'INT',attr.domain);new.data.foreach_set('value',values)
body=bpy.data.objects.new('REVIEW_V20_Avatar_Closed_Cap',mesh);scene.collection.objects.link(body)
for group in source.vertex_groups:body.vertex_groups.new(name=group.name)
body.parent=arm;body.matrix_parent_inverse=source.matrix_parent_inverse.copy();body.matrix_basis=source.matrix_basis.copy();mod=body.modifiers.new('Armature','ARMATURE');mod.object=arm
for key in('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):setattr(mod,key,getattr(next(m for m in source.modifiers if m.type=='ARMATURE'),key))
bpy.context.window.scene=scene;bpy.context.view_layer.update();after=h['_snapshot'](mesh)['arrays']
assert np.array_equal(after['coordinates'],P)and np.array_equal(after['triangles'],TN)and np.array_equal(h['_weights'](mesh,len(body.vertex_groups)),W)
for name in names:assert np.array_equal(after['uv:'+name],a['uv:'+name])
outside=np.ones(len(requested_normals),bool);outside[loops]=False;outside_error=float(abs(after['cornerNormals'][outside]-a['cornerNormals'][outside]).max());seed_error=float(abs(after['cornerNormals'][loops]-requested_normals[loops]).max());assert outside_error<5e-4 and seed_error<5e-4
def edges(triangles):
 result={}
 for fi,t in enumerate(triangles):
  for x,y in zip(t,np.roll(t,-1)):result.setdefault(tuple(sorted((int(x),int(y)))),[]).append((fi,int(x),int(y)))
 return result
old_edges=edges(T);new_edges=edges(TN);old_open={e for e,v in old_edges.items()if len(v)==1};new_open={e for e,v in new_edges.items()if len(v)==1}
assert not(new_open-old_open)and len(old_open-new_open)==4
seams=[(9754,9755),(9755,9758)];assert all(len(new_edges[e])==2 and new_edges[e][0][1:]==tuple(reversed(new_edges[e][1][1:]))for e in seams)
assert not{e for e,v in new_edges.items()if len(v)>2}-{e for e,v in old_edges.items()if len(v)>2}
def duplicates(triangles):
 rows,count=np.unique(np.sort(triangles,axis=1),axis=0,return_counts=True);return{tuple(map(int,row))for row in rows[count>1]}
assert not(duplicates(TN)-duplicates(T))
affected_edges={tuple(sorted((int(x),int(y))))for t in TN[faces]for x,y in zip(t,np.roll(t,-1))};assert len(affected_edges)==7
def normals_areas(Q,tri):
 v=Q[tri];cross=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);length=np.linalg.norm(cross,axis=1);return cross/np.maximum(length[:,None],1e-20),length*.5
corner_mask=np.ones(T.size,bool);corner_mask[loops]=False
def probe(label,degrees=0):
 qp=points(body);rp=points(reference);movement=np.linalg.norm(qp[TN]-rp[T],axis=2);max_move=float(movement.max());unchanged=float(movement.reshape(-1)[corner_mask].max());assert max_move<=.001 and unchanged<1e-6
 normals,areas=normals_areas(qp,TN);old_normals,old_areas=normals_areas(rp,T);ratios=areas[faces]/old_areas[faces];dots=(normals[faces]*old_normals[faces]).sum(1);assert(areas[faces]>1e-10).all()and(ratios>=.5).all()and(ratios<=2).all()and(dots>.9).all()
 angles=[]
 for e in affected_edges:
  fs=[v[0]for v in new_edges[e]];assert len(fs)==2;angles.append(float(np.degrees(np.arccos(np.clip(normals[fs[0]]@normals[fs[1]],-1,1)))))
 assert max(angles)<90
 return {'bone':label,'degrees':degrees,'maximumTriangleCornerMovementMeters':max_move,'unchangedCornersMaxErrorMeters':unchanged,'minimumChangedAreaRatio':float(ratios.min()),'maximumChangedAreaRatio':float(ratios.max()),'minimumGeometricNormalDot':float(dots.min()),'maximumAffectedEdgeAngleDegrees':max(angles),'closedSeamGapMeters':0.0}
motion=[];saved_pose_position=arm.data.pose_position;arm.data.pose_position='REST';bpy.context.view_layer.update();motion.append(probe('rest'));arm.data.pose_position=saved_pose_position;bpy.context.view_layer.update();motion.append(probe('standing'))
for name,degrees in[('head',-15),('head',15),('chest',-10),('chest',10),('R_clavicle',-10),('R_clavicle',10),('R_upper_arm',-15),('R_upper_arm',15)]:
 bone=arm.pose.bones[name];basis=bone.matrix_basis.copy();bone.matrix_basis=basis@Matrix.Rotation(radians(degrees),4,'Y'if name=='head'else'X');bpy.context.view_layer.update();motion.append(probe(name,degrees));bone.matrix_basis=basis;bpy.context.view_layer.update()
q=points(body);qr=points(reference);np.savez_compressed(F/'integrated_surface.npz',vertices=P,triangles=TN,weights=W,posed=q,changed_faces=faces,changed_corners=delta)
reference.hide_render=True;reference.hide_set(True)
bpy.context.window.scene=source_scene;bpy.context.view_layer.update();assert not h['_differences'](snap,h['_snapshot'](source.data))and np.array_equal(h['_weights'](source.data,len(source.vertex_groups)),W)and np.array_equal(points(source),source_pose)
bpy.context.window.scene=scene;bpy.context.view_layer.update();camera=bpy.data.objects.new('REVIEW_V20_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);scene.camera=camera;camera.matrix_world=source_scene.camera.matrix_world.copy()
for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True);saved=h['_snapshot'](mesh)['arrays']
record={'status':'controlled-last-cap-corner-refit-saved-awaiting-reopen-and-renders','library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'sourceLibrary':str(SOURCE),'sourceSha256':AUDIT['sha256'],'historicalSourceSha256':PRIOR['sha256'],'sourceByteMatchHistorical':False,'checkpoint':str(CP),'candidateSha256':csha,
 'scene':scene.name,'bodyObject':body.name,'referenceObject':reference.name,'sourceObject':source.name,'changedCorners':delta.tolist(),'changedLoopIndices':loops.tolist(),'oldVertex':29974,'targetVertex':9755,'changedFaces':faces.tolist(),'bindModelSpaceCornerMovementMeters':bind_movement,'closedSeamGapMeters':0.0,'sourceStandingGapMeters':float(np.linalg.norm(qr[29974]-qr[9755])),'storedPositionsWeightsAllUVExact':True,'oldBoundaryCount':len(old_open),'newBoundaryCount':len(new_open),'removedBoundaryKeys':sorted(old_open-new_open),'newBoundaryKeys':[],'finalSharedSeamEdges':seams,'outsideNormalMaxComponentError':outside_error,'changedNormalTargetMaxComponentError':seed_error,'motionSamples':motion,
 'triangles':len(TN),'vertices':len(P),'unreferencedVertices':int(len(P)-len(np.unique(TN))),'bodyArraysSha256':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in saved.items()},'weightsSha256':hashlib.sha256(W.tobytes()).hexdigest(),'sourcePreserved':True,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,'visibleWindowsOpened':False,'desktopSwitched':False,'MCPUsed':False,'executionMode':'Blender 5.2.3 LTS background CLI through official Windows app alias; GUI/MCP were not running','scope':'Controlled non-exact fitting of one existing cap corner. All seven border points now join this local cap; full garment, anatomy, collision and native Walk remain unapproved. Per-corner UVs are unchanged; custom normals intentionally adopt existing shirt target normal.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==AUDIT['sha256'];OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
