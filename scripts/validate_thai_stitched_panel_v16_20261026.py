"""Validate the saved/reopened actual stitched review copy and untouched source."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_STITCHED_PANEL_V16_20261026.json').read_text())
a=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
OUT=ROOT/'reports/CHARACTER_THAI_STITCHED_PANEL_V16_REOPEN_20261026.json';assert not OUT.exists()
assert Path(bpy.data.filepath).resolve()==Path(r['library']).resolve() and hashlib.sha256(Path(r['library']).read_bytes()).hexdigest()==r['sha256']
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
source=bpy.data.objects[r['sourceObject']];snapshot=helper['_snapshot'](source.data)
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in snapshot['arrays'].items()}==a['sourceArraysSha256']
assert hashlib.sha256(helper['_weights'](source.data,len(source.vertex_groups)).tobytes()).hexdigest()==a['sourceWeightSha256']
F=ROOT/'reports/thai_stitched_panel_v16_20261026'
with np.load(F/'blender_integrated_surface.npz')as n:d={k:n[k].copy()for k in n.files}
with np.load(F/'panel_candidate.npz')as n:c={k:n[k].copy()for k in n.files}
body=bpy.data.objects[r['bodyObject']];actual=helper['_snapshot'](body.data)
saved=json.loads((F/'saved_body_payload.json').read_text())
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in actual['arrays'].items()}==saved['arraysSha256']
assert hashlib.sha256(helper['_weights'](body.data,len(body.vertex_groups)).tobytes()).hexdigest()==saved['weightsSha256']
assert np.array_equal(actual['arrays']['coordinates'],d['vertices']) and np.array_equal(actual['arrays']['triangles'],d['triangles'])
assert np.array_equal(helper['_weights'](body.data,len(body.vertex_groups)),d['weights'])
kept=d['source_faces_kept'];loop_ids=np.concatenate([np.arange(source.data.polygons[int(i)].loop_start,source.data.polygons[int(i)].loop_start+3)for i in kept])
for layer in source.data.uv_layers:
 assert np.array_equal(actual['arrays']['uv:'+layer.name][:len(loop_ids)],snapshot['arrays']['uv:'+layer.name][loop_ids])
 assert np.array_equal(actual['arrays']['uv:'+layer.name][len(loop_ids):],c['uv'])
normal_error=float(np.abs(actual['arrays']['cornerNormals'][:len(loop_ids)]-snapshot['arrays']['cornerNormals'][loop_ids]).max());assert normal_error<5e-4
assert [s.material for s in body.material_slots]==[s.material for s in source.material_slots]
def points(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
bpy.context.window.scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.view_layer.update();source_points=points(source)
expected=np.load(ROOT/'reports/thai_seam_area_v12_20261026/posed_surface.npz')['posed'];source_error=float(np.linalg.norm(source_points-expected,axis=1).max());assert source_error<1e-6
bpy.context.window.scene=bpy.data.scenes[r['scene']];bpy.context.view_layer.update();q=points(body)
pose_error=float(np.linalg.norm(q-d['posed'],axis=1).max());outside_error=float(np.linalg.norm(q[:r['sourceVertexCount']]-source_points,axis=1).max());assert pose_error<1e-6 and outside_error<1e-6
edges={};directions={};T=actual['arrays']['triangles']
for fi,t in enumerate(T):
 for x,y in zip(t,np.roll(t,-1)):
  key=tuple(sorted((int(x),int(y))));edges.setdefault(key,[]).append(fi);directions.setdefault(key,[]).append((int(x),int(y)))
mapping=d['panel_to_body_vertex'];seams=np.sort(mapping[c['boundary_edges']],axis=1)
assert all(len(edges[tuple(e)])==2 and directions[tuple(e)][0]==tuple(reversed(directions[tuple(e)][1]))for e in seams)
assert hashlib.sha256(Path(r['sourceLibrary']).read_bytes()).hexdigest()==r['sourceSha256']
record={'status':'saved-shared-vertex-panel-reopened-and-verified-local-copy-only','library':r['library'],'sha256':r['sha256'],
 'bodyGeometryWeightsAndUVExact':True,'sourceAuthoringArraysWeightsExact':True,'sourceLibraryBytesPreserved':True,
 'allSavedBodyArraysIncludingNormalsExact':True,'originalMaterialsReused':True,'outsideNormalMaxComponentTransferError':normal_error,
 'sharedSeamEdges':len(seams),'seamTopologyAndWindingPassed':True,'sourcePoseMaxErrorMeters':source_error,
 'bodyPoseReopenMaxErrorMeters':pose_error,'originalVerticesPoseMaxErrorMeters':outside_error,
 'activeScene':r['scene'],'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,
 'scope':'A single reviewed garment panel is replaced in a separate full-avatar copy. Shared indices make its outer seam continuous; this does not approve the remaining shirt, high collar, full neutral pose or native Walk.'}
OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
