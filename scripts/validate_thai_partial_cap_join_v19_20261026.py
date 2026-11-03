"""Validate the saved partial cap union without inferring garment completion."""
import bpy,json,hashlib,runpy,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_PARTIAL_CAP_JOIN_V19_20261026.json').read_text());prior=json.loads((ROOT/'reports/CHARACTER_THAI_CLOTH_SEAM_V18_20261026.json').read_text());original=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
OUT=ROOT/'reports/CHARACTER_THAI_PARTIAL_CAP_JOIN_V19_REOPEN_20261026.json';assert not OUT.exists()
assert Path(bpy.data.filepath)==Path(r['library'])and hashlib.sha256(Path(r['library']).read_bytes()).hexdigest()==r['sha256']
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));body=bpy.data.objects[r['bodyObject']];source=bpy.data.objects[r['sourceObject']]
a=h['_snapshot'](body.data)['arrays'];sa=h['_snapshot'](source.data)['arrays'];weights=h['_weights'](body.data,len(body.vertex_groups))
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==r['bodyArraysSha256']and hashlib.sha256(weights.tobytes()).hexdigest()==r['weightsSha256']
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in sa.items()}==prior['bodyArraysSha256']and hashlib.sha256(h['_weights'](source.data,len(source.vertex_groups)).tobytes()).hexdigest()==prior['weightsSha256']
orig=bpy.data.objects[original['sourceMesh']];assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](orig.data)['arrays'].items()}==original['sourceArraysSha256']
assert hashlib.sha256(h['_weights'](orig.data,len(orig.vertex_groups)).tobytes()).hexdigest()==original['sourceWeightSha256']
canonical=np.arange(len(a['coordinates']),dtype=np.int32)
for x,y in r['oldToTarget'].items():canonical[int(x)]=int(y)
assert np.array_equal(a['triangles'],canonical[sa['triangles']])and np.array_equal(a['coordinates'],sa['coordinates'])and np.array_equal(weights,h['_weights'](source.data,len(source.vertex_groups)))
for layer in source.data.uv_layers:assert np.array_equal(a['uv:'+layer.name],sa['uv:'+layer.name])
assert [s.material for s in body.material_slots]==[s.material for s in source.material_slots]
def points(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
bpy.context.window.scene=bpy.data.scenes[prior['scene']];bpy.context.view_layer.update();sq=points(source)
bpy.context.window.scene=bpy.data.scenes[r['scene']];bpy.context.view_layer.update();q=points(body)
with np.load(ROOT/'reports/thai_partial_cap_join_v19_20261026/integrated_surface.npz')as n:expected=n['posed']
reopen_error=float(np.linalg.norm(q-expected,axis=1).max());source_error=float(np.linalg.norm(q[a['triangles']]-sq[sa['triangles']],axis=2).max());assert reopen_error<1e-6 and source_error<1e-6
pending=float(np.linalg.norm(q[29974]-q[9755]));assert abs(pending-r['pendingSeventhGapMeters'])<1e-6
edges={}
for t in a['triangles']:
 for x,y in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted((int(x),int(y)))),[]).append((int(x),int(y)))
assert all(len(edges[tuple(e)])==2 and edges[tuple(e)][0]==tuple(reversed(edges[tuple(e)][1]))for e in r['newlySharedEdges'])
assert sum(len(v)==1 for v in edges.values())==r['newBoundaryCount']
assert hashlib.sha256(Path(r['sourceLibrary']).read_bytes()).hexdigest()==r['sourceSha256']and hashlib.sha256(Path(r['checkpoint']).read_bytes()).hexdigest()==r['sourceSha256']
record={'status':'six-pair-partial-cap-union-reopened-and-verified','library':r['library'],'sha256':r['sha256'],'allSavedBodyArraysNormalsUVWeightsExact':True,'sourceV18AndOriginalAuthoringDataPreserved':True,'sourceAndCheckpointBytesPreserved':True,'allPositionsWeightsUVExactSource':True,'originalMaterialsReused':True,'fiveSeamsTopologyAndWindingPassed':True,'bodyPoseReopenMaxErrorMeters':reopen_error,'allTriangleCornerPoseMaxErrorVersusSourceMeters':source_error,'pendingSeventhGapMeters':pending,'pendingPairStillUnchanged':True,'activeScene':r['scene'],'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,'meetingMode':r['meetingMode'],'limit':r['limit']}
OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
