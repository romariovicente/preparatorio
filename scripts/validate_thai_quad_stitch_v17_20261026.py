"""Reopen validation for the local one-corner cloth stitch."""
import bpy,json,hashlib,runpy,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_QUAD_STITCH_V17_20261026.json').read_text());old=json.loads((ROOT/'reports/CHARACTER_THAI_STITCHED_PANEL_V16_20261026.json').read_text());A=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
OUT=ROOT/'reports/CHARACTER_THAI_QUAD_STITCH_V17_REOPEN_20261026.json';assert not OUT.exists()
assert Path(bpy.data.filepath)==Path(r['library'])and hashlib.sha256(Path(r['library']).read_bytes()).hexdigest()==r['sha256']
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));body=bpy.data.objects[r['bodyObject']];a=h['_snapshot'](body.data)['arrays'];W=h['_weights'](body.data,len(body.vertex_groups))
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==r['bodyArraysSha256']and hashlib.sha256(W.tobytes()).hexdigest()==r['weightsSha256']
source=bpy.data.objects[r['sourceObject']];sa=h['_snapshot'](source.data)['arrays'];saved=json.loads((ROOT/'reports/thai_stitched_panel_v16_20261026/saved_body_payload.json').read_text())
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in sa.items()}==saved['arraysSha256']and hashlib.sha256(h['_weights'](source.data,len(source.vertex_groups)).tobytes()).hexdigest()==saved['weightsSha256']
original=bpy.data.objects[A['sourceMesh']];assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](original.data)['arrays'].items()}==A['sourceArraysSha256']
assert hashlib.sha256(h['_weights'](original.data,len(original.vertex_groups)).tobytes()).hexdigest()==A['sourceWeightSha256']
assert np.array_equal(a['coordinates'],sa['coordinates'])and np.array_equal(W,h['_weights'](source.data,len(source.vertex_groups)))
delta=np.argwhere(a['triangles']!=sa['triangles']);assert np.array_equal(delta,[[r['changedFace'],r['changedCorner']]])
for layer in source.data.uv_layers:
 u=a['uv:'+layer.name];prev=sa['uv:'+layer.name];keep=np.ones(len(u),bool);keep[r['changedLoop']]=False;assert np.array_equal(u[keep],prev[keep])
 target=prev[sa['loopVertices'].reshape(-1)==r['targetVertex']][0];assert np.array_equal(u[r['changedLoop']],target)
def points(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
F=ROOT/'reports/thai_quad_stitch_v17_20261026';expected=np.load(F/'integrated_surface.npz')['posed']
bpy.context.window.scene=bpy.data.scenes[old['scene']];bpy.context.view_layer.update();source_points=points(source)
bpy.context.window.scene=bpy.data.scenes[r['scene']];bpy.context.view_layer.update();q=points(body);pose_error=float(np.linalg.norm(q-expected,axis=1).max());source_error=float(np.linalg.norm(q-source_points,axis=1).max());assert pose_error<1e-6 and source_error<1e-6
edges={}
for fi,t in enumerate(a['triangles']):
 for x,y in zip(t,np.roll(t,-1)):edges.setdefault(tuple(sorted((int(x),int(y)))),[]).append((int(x),int(y)))
assert all(len(edges[tuple(e)])==2 and edges[tuple(e)][0]==tuple(reversed(edges[tuple(e)][1]))for e in r['sharedSeamEdges'])
assert hashlib.sha256(Path(r['sourceLibrary']).read_bytes()).hexdigest()==r['sourceSha256']and hashlib.sha256(Path(r['checkpoint']).read_bytes()).hexdigest()==r['sourceSha256']
record={'status':'one-cloth-crack-weld-reopened-and-numerically-verified','library':r['library'],'sha256':r['sha256'],'sourceAndCheckpointBytesPreserved':True,'bodyAllSavedArraysNormalsUVWeightsExact':True,'sourceV16ArraysWeightsExact':True,'originalAuthoringSourceArraysWeightsExact':True,'oneFaceCornerOnly':True,'allVertexPositionsWeightsExactSource':True,'sharedSeamTopologyPassed':True,'newPoseReopenMaxErrorMeters':pose_error,'allVertexPoseMaxErrorVersusSourceMeters':source_error,'activeScene':r['scene'],'meetingMode':r['meetingMode'],'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'nativeWalkValidated':False,'limits':r['limits']}
OUT.write_text(json.dumps(record,indent=2));print(json.dumps(record))
