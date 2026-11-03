"""Validate persisted Blender working data, not a runtime GLB export."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_PATCH_V14_20261026.json').read_text(encoding='utf-8'))
a=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text(encoding='utf-8'))
OUT=ROOT/'reports/CHARACTER_THAI_COLLAR_PATCH_V14_REOPEN_20261026.json';assert not OUT.exists()
assert Path(bpy.data.filepath).resolve()==Path(r['library']).resolve()
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
source_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=source_scene
source=bpy.data.objects[a['sourceMesh']];snapshot=helper['_snapshot'](source.data)
source_hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in snapshot['arrays'].items()}
assert source_hashes==a['sourceArraysSha256']
W=helper['_weights'](source.data,len(source.vertex_groups))
assert hashlib.sha256(W.tobytes()).hexdigest()==a['sourceWeightSha256']
expected_source=np.load(ROOT/'reports/thai_seam_area_v12_20261026/posed_surface.npz')['posed']
def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    v=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',v);world=np.array(ev.matrix_world);ev.to_mesh_clear()
    return v.reshape(-1,3)@world[:3,:3].T+world[:3,3]
source_pose_error=float(np.linalg.norm(points(source)-expected_source,axis=1).max());assert source_pose_error<1e-5
mapping=np.load(ROOT/'reports/thai_collar_patch_v14_20261026/patch_source_mapping.npz')
edit=bpy.data.scenes[r['editScene']];bpy.context.window.scene=edit;patch=bpy.data.objects[r['patchObject']]
actual=helper['_snapshot'](patch.data)
assert np.array_equal(actual['arrays']['coordinates'],mapping['vertices']) and np.array_equal(actual['arrays']['triangles'],mapping['triangles'])
assert np.array_equal(helper['_weights'](patch.data,len(patch.vertex_groups)),mapping['weights'])
for i,layer in enumerate(patch.data.uv_layers):assert np.array_equal(actual['arrays']['uv:'+layer.name],mapping['uv_'+str(i)])
normal_error=float(np.abs(actual['arrays']['cornerNormals']-mapping['corner_normals']).max());assert normal_error<1e-5
pose_error=float(np.linalg.norm(points(patch)-mapping['expected_posed'],axis=1).max());assert pose_error<1e-5
point_ids=np.empty(len(patch.data.vertices),np.int32);patch.data.attributes['prep_source_vertex_index'].data.foreach_get('value',point_ids)
face_ids=np.empty(len(patch.data.polygons),np.int32);patch.data.attributes['prep_source_triangle_index'].data.foreach_get('value',face_ids)
assert np.array_equal(point_ids,mapping['source_vertex_indices']) and np.array_equal(face_ids,mapping['source_face_indices'])
review_mesh=bpy.data.objects[a['reviewMesh']]
regions=np.empty(len(review_mesh.data.polygons),np.int32);review_mesh.data.attributes['prep_v13_review_region'].data.foreach_get('value',regions)
assert {str(i):int((regions==i).sum()) for i in range(4)}==a['regionFaceCounts']
bpy.context.window.scene=source_scene;bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type!='VIEW_3D':continue
        space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_overlays=False
        space.region_3d.view_location=Vector((0,0,.9));space.region_3d.view_distance=2.9
        space.region_3d.view_rotation=(Vector((0,0,.9))-Vector((1.4,-4,1.65))).to_track_quat('-Z','Y')
        space.region_3d.view_perspective='PERSP'
assert hashlib.sha256(Path(r['library']).read_bytes()).hexdigest()==r['sha256']
report={'status':'saved-Blender-study-reopened-and-preservation-verified-not-runtime-validation',
 'library':r['library'],'sha256':r['sha256'],'patchVertices':len(point_ids),'patchTriangles':len(face_ids),
 'patchSourceMappingExact':True,'patchWeightsExact':True,'patchUVsExact':True,
 'patchNormalsReopenMaxError':normal_error,'patchPoseMaxError':pose_error,'sourcePoseMaxError':source_pose_error,
 'annotationRegionCountsPreserved':True,'originalSourceAuthoringArraysAndWeightsExact':True,
 'activeScene':source_scene.name,'visibleWindowsOpened':False,'desktopSwitched':False,
 'runtimeChanged':False,'masterChanged':False,'GLBExported':False,
 'scope':'Reopened the saved .blend working study and verified source data, annotation attributes and extracted patch. Fit repair and runtime export remain pending.'}
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
