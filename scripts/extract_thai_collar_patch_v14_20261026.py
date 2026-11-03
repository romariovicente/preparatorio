"""Prepare an independently editable cloth candidate; do not claim a fit repair."""
import bpy,json,hashlib,shutil,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
previous=json.loads((ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json').read_text(encoding='utf-8'))
SOURCE=Path(previous['library'])
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COLLAR_PATCH_V14_20261026.blend'
CHECKPOINT=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_PATCH_V14_20261026.blend'
F=ROOT/'reports/thai_collar_patch_v14_20261026'
OUT=ROOT/'reports/CHARACTER_THAI_COLLAR_PATCH_V14_20261026.json'
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve() and not bpy.data.is_dirty
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==previous['sha256']
assert not any(p.exists() for p in (WORK,CHECKPOINT,F,OUT))
scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=scene
source_mesh=bpy.data.objects[previous['sourceMesh']];source_arm=source_mesh.parent
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
snapshot=helper['_snapshot'](source_mesh.data);P=snapshot['arrays']['coordinates'];T=snapshot['arrays']['triangles']
W=helper['_weights'](source_mesh.data,len(source_mesh.vertex_groups))
annotation=np.load(ROOT/'reports/thai_collar_annotation_v13_20261026/review_face_regions.npz')
faces=annotation['region1_faces'];source_vertices=np.unique(T[faces]);index=np.full(len(P),-1,np.int32);index[source_vertices]=np.arange(len(source_vertices))
assert len(faces)==131 and len(source_vertices)==127 and not np.isin(source_vertices,annotation['protected_vertices']).any()
assert np.array_equal(P,annotation['vertices']) and np.array_equal(T,annotation['triangles'])
loop_ids=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in (source_mesh.data.polygons[int(i)] for i in faces)])
assert len(loop_ids)==len(faces)*3
shutil.copy2(SOURCE,CHECKPOINT);F.mkdir()
def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a);world=np.array(ev.matrix_world);ev.to_mesh_clear()
    return a.reshape(-1,3)@world[:3,:3].T+world[:3,3]
original_points=points(source_mesh)
edit=bpy.data.scenes.new('EDIT_THAI_COLLAR_PATCH_V14_20261026')
edit['PREP_role']='Independent light-cloth candidate for later fit/topology work; original avatar unchanged. Not approved replacement or game export.'
edit['PREP_source_face_count']=131;edit['PREP_ambiguous_contact']='11636/11637/11638 remain protected and are excluded.'
edit.world=scene.world
arm=source_arm.copy();arm.data=source_arm.data.copy();arm.name='EDIT_V14_Patch_Rig';edit.collection.objects.link(arm)
data=bpy.data.meshes.new('EDIT_V14_Light_Cloth_Patch_Mesh')
data.from_pydata(P[source_vertices].tolist(),[],index[T[faces]].tolist());data.update()
data.polygons.foreach_set('use_smooth',snapshot['arrays']['polygonSmooth'].reshape(-1)[faces])
for layer in source_mesh.data.uv_layers:
    new=data.uv_layers.new(name=layer.name)
    new.data.foreach_set('uv',snapshot['arrays']['uv:'+layer.name][loop_ids].reshape(-1))
    new.active_render=layer.active_render
data.uv_layers.active_index=source_mesh.data.uv_layers.active_index
assert hasattr(data,'normals_split_custom_set')
data.normals_split_custom_set(snapshot['arrays']['cornerNormals'][loop_ids].tolist())
data.materials.append(source_mesh.data.materials[0])
patch=bpy.data.objects.new('EDIT_V14_Independent_Light_Cloth_Patch',data);edit.collection.objects.link(patch)
patch.parent=arm;patch.matrix_parent_inverse=source_mesh.matrix_parent_inverse.copy();patch.matrix_world=source_mesh.matrix_world.copy()
for group in source_mesh.vertex_groups:patch.vertex_groups.new(name=group.name)
for local_id,source_id in enumerate(source_vertices):
    for group_id in np.flatnonzero(W[source_id]>0):patch.vertex_groups[int(group_id)].add([local_id],float(W[source_id,group_id]),'REPLACE')
modifier=patch.modifiers.new('Armature','ARMATURE');modifier.object=arm
for name in ('use_deform_preserve_volume','use_vertex_groups','use_bone_envelopes'):
    setattr(modifier,name,getattr(next(m for m in source_mesh.modifiers if m.type=='ARMATURE'),name))
attr=data.attributes.new('prep_source_vertex_index','INT','POINT');attr.data.foreach_set('value',source_vertices.astype(np.int32))
attr=data.attributes.new('prep_source_triangle_index','INT','FACE');attr.data.foreach_set('value',faces.astype(np.int32))
patch['PREP_candidate_only']=True;patch['PREP_next']='Fit/retopology and boundary support, then replacement review. Do not hide/delete source shirt merely to claim repair.'
local=helper['_snapshot'](data)
assert np.array_equal(local['arrays']['coordinates'],P[source_vertices])
assert np.array_equal(local['arrays']['triangles'],index[T[faces]])
assert np.array_equal(helper['_weights'](data,len(patch.vertex_groups)),W[source_vertices])
uv_exact=all(np.array_equal(local['arrays']['uv:'+layer.name],snapshot['arrays']['uv:'+layer.name][loop_ids]) for layer in source_mesh.data.uv_layers)
assert uv_exact
normal_error=float(np.abs(local['arrays']['cornerNormals']-snapshot['arrays']['cornerNormals'][loop_ids]).max());assert normal_error<5e-4
for light in (o for o in scene.objects if o.type=='LIGHT'):edit.collection.objects.link(light)
camera=bpy.data.objects.new('EDIT_V14_Patch_Camera',scene.camera.data.copy());edit.collection.objects.link(camera);edit.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=.32
edit.render.engine='BLENDER_EEVEE';edit.render.resolution_x=560;edit.render.resolution_y=560;edit.render.resolution_percentage=100
edit.render.image_settings.file_format='PNG';edit.view_settings.view_transform='AgX'
bpy.context.window.scene=edit;bpy.context.view_layer.update()
patch_points=points(patch);pose_error=float(np.linalg.norm(patch_points-original_points[source_vertices],axis=1).max());assert pose_error<1e-5
np.savez_compressed(F/'patch_source_mapping.npz',source_vertex_indices=source_vertices,source_face_indices=faces,
 vertices=P[source_vertices],triangles=index[T[faces]],weights=W[source_vertices],group_names=np.array([g.name for g in patch.vertex_groups]),
 expected_posed=original_points[source_vertices],corner_normals=local['arrays']['cornerNormals'],
 **{'uv_'+str(i):local['arrays']['uv:'+layer.name] for i,layer in enumerate(source_mesh.data.uv_layers)})
renders=[];center=Vector(patch_points.mean(0))
for name,offset in [('back',(0,3,0)),('side',(3,0,0))]:
    camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    path=F/('patch_'+name+'.png');edit.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
bpy.context.window.scene=scene;bpy.context.view_layer.update()
assert not helper['_differences'](snapshot,helper['_snapshot'](source_mesh.data))
assert np.array_equal(W,helper['_weights'](source_mesh.data,len(source_mesh.vertex_groups)))
assert float(np.linalg.norm(points(source_mesh)-original_points,axis=1).max())==0
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
record={'status':'independent-cloth-candidate-prepared-not-fitted-not-replacement-not-game-export',
 'library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),
 'sourceLibrary':str(SOURCE),'sourceSha256':previous['sha256'],'checkpoint':str(CHECKPOINT),
 'editScene':edit.name,'patchObject':patch.name,'patchVertices':len(source_vertices),'patchTriangles':len(faces),
 'rigBones':len(arm.data.bones),'patchPoseMaxError':pose_error,'patchSourceWeightsExact':True,
 'patchSourceUVExact':uv_exact,'patchCornerNormalMaxComponentError':normal_error,
 'protectedVerticesIncluded':0,'sourceAuthoringDataPreserved':True,'renders':renders,
 'sourceGeometryChanged':False,'sourceWeightsChanged':False,'runtimeChanged':False,'masterChanged':False,
 'remoteOperations':False,'neutralPoseValidated':False,'nativeWalkValidated':False,
 'scope':'Separate editable surface extracted from the reviewed 131 light-cloth candidate faces. Source avatar remains fully present and unchanged. The patch still has original fit/weights; extraction alone does not fix the raised collar.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==previous['sha256']
OUT.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:record[k] for k in ('status','library','patchVertices','patchTriangles','patchPoseMaxError','patchCornerNormalMaxComponentError')}))
