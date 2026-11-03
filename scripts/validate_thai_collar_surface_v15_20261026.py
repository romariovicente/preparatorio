"""Reopen QA for a local new-cloth study, not an exported game asset."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_SURFACE_V15_20261026.json').read_text())
a=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text())
p=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_PATCH_V14_20261026.json').read_text())
OUT=ROOT/'reports/CHARACTER_THAI_COLLAR_SURFACE_V15_REOPEN_20261026.json';assert not OUT.exists()
assert Path(bpy.data.filepath).resolve()==Path(r['library']).resolve() and not bpy.data.is_dirty
assert hashlib.sha256(Path(r['library']).read_bytes()).hexdigest()==r['sha256']
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
source=bpy.data.objects[a['sourceMesh']];snap=helper['_snapshot'](source.data)
assert {k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in snap['arrays'].items()}==a['sourceArraysSha256']
assert hashlib.sha256(helper['_weights'](source.data,len(source.vertex_groups)).tobytes()).hexdigest()==a['sourceWeightSha256']
with np.load(r['candidate']) as data:d={k:data[k].copy() for k in data.files}
cloth=bpy.data.objects[r['clothObject']];s=helper['_snapshot'](cloth.data)
assert np.array_equal(s['arrays']['coordinates'],d['vertices'].astype(np.float32))
assert np.array_equal(s['arrays']['triangles'],d['triangles'].astype(np.int32))
assert np.array_equal(s['arrays']['uv:ClothStudyUV'],d['uv'].astype(np.float32))
assert np.array_equal(helper['_weights'](cloth.data,len(cloth.vertex_groups)),d['weights'].astype(np.float32))
def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    q=np.empty(len(data.vertices)*3,np.float32);data.vertices.foreach_get('co',q);M=np.array(ev.matrix_world);ev.to_mesh_clear()
    return q.reshape(-1,3)@M[:3,:3].T+M[:3,3]
bpy.context.window.scene=bpy.data.scenes[r['scene']];bpy.context.view_layer.update()
error=float(np.linalg.norm(points(cloth)-d['expected_posed'],axis=1).max());assert error<1e-5
reference=np.load(ROOT/'reports/thai_seam_area_v12_20261026/posed_surface.npz')['posed']
context_error=float(np.linalg.norm(points(bpy.data.objects[r['contextObject']])-reference,axis=1).max());assert context_error<1e-5
original_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=original_scene;bpy.context.view_layer.update()
source_error=float(np.linalg.norm(points(source)-reference,axis=1).max());assert source_error<1e-5
old=bpy.data.objects[p['patchObject']]
with np.load(ROOT/'reports/thai_collar_patch_v14_20261026/patch_source_mapping.npz') as data:old_map={k:data[k].copy() for k in data.files}
old_snap=helper['_snapshot'](old.data)
assert np.array_equal(old_snap['arrays']['coordinates'],old_map['vertices'])
assert np.array_equal(old_snap['arrays']['triangles'],old_map['triangles'])
assert np.array_equal(helper['_weights'](old.data,len(old.vertex_groups)),old_map['weights'])
for i,layer in enumerate(old.data.uv_layers):assert np.array_equal(old_snap['arrays']['uv:'+layer.name],old_map['uv_'+str(i)])
bpy.context.window.scene=bpy.data.scenes[r['scene']];bpy.context.view_layer.update()
report={'status':'saved-new-cloth-study-reopened-and-verified-not-runtime-or-full-garment-approval',
 'library':r['library'],'sha256':r['sha256'],'newClothGeometryWeightsUVExact':True,
 'sourceArraysWeightsExact':True,'originalV14PatchArraysWeightsUVExact':True,
 'sourcePoseMaxErrorMeters':source_error,'contextPoseMaxErrorMeters':context_error,'newClothPoseMaxErrorMeters':error,
 'activeScene':r['scene'],'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,
 'limits':'Independent reconstruction with open perimeter; replacement, seam union, collision and native Walk remain unvalidated.'}
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
