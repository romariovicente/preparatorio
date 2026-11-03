"""Editable collar annotation in an independent Blender study, never a fit fix."""
import bpy,hashlib,json,shutil,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
state=json.loads((ROOT/'reports/CHARACTER_THAI_SEAM_AREA_INCREMENT_20261026.json').read_text(encoding='utf-8'))
SOURCE=Path(state['savedPoseLibrary']['path'])
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.blend'
CHECKPOINT=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_COLLAR_V13_20261026.blend'
F=ROOT/'reports/thai_collar_annotation_v13_20261026'
OUT=ROOT/'reports/CHARACTER_THAI_COLLAR_ANNOTATION_V13_20261026.json'
ANNOTATION=ROOT/'work/qa_thai_collar_semantics_v13_20261026/review_face_regions.npz'
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve() and not bpy.data.is_dirty
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==state['savedPoseLibrary']['sha256']
assert hashlib.sha256(ANNOTATION.read_bytes()).hexdigest()=='a9950563a33b7840d574d7d62e138c864d33c3eaadd4fe17d942b6e614cc66f2'
assert not any(p.exists() for p in (WORK,CHECKPOINT,F,OUT))
source_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=source_scene
source_mesh=next(o for o in source_scene.objects if o.type=='MESH')
source_arm=next(o for o in source_scene.objects if o.type=='ARMATURE')
assert source_mesh.parent==source_arm and source_arm.parent is None and len(source_mesh.data.materials)==1
annotation=np.load(ANNOTATION);regions=annotation['face_region'];T=annotation['triangles'];P=annotation['vertices']
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
before=helper['_snapshot'](source_mesh.data)
assert np.array_equal(before['arrays']['coordinates'],P)
assert np.array_equal(before['arrays']['triangles'],T)
assert len(source_mesh.data.polygons)==len(T) and all(len(p.vertices)==3 for p in source_mesh.data.polygons)
W=helper['_weights'](source_mesh.data,len(source_mesh.vertex_groups))
expected=np.load(ROOT/'reports/thai_seam_area_v12_20261026/prepared_weights.npz')
assert np.array_equal(W,expected['weights'])
assert [g.name for g in source_mesh.vertex_groups]==expected['group_names'].tolist()
assert not np.isin(T[regions==1],annotation['protected_vertices']).any()
shutil.copy2(SOURCE,CHECKPOINT);F.mkdir()
for name in ('review_face_regions.npz','review_face_regions.json','collar_semantics_diagnosis.json','connected_context.json','collar_depth_context.png','collar_semantics_panel.png'):
    shutil.copy2(ROOT/'work/qa_thai_collar_semantics_v13_20261026'/name,F/name)
def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a)
    world=np.array(ev.matrix_world);ev.to_mesh_clear()
    return a.reshape(-1,3)@world[:3,:3].T+world[:3,3]
source_points=points(source_mesh)
review=bpy.data.scenes.new('REVIEW_THAI_COLLAR_V13_20261026')
review['PREP_role']='Editable face annotations only. No authorized semantic release or garment fit.'
review['PREP_legend']='0 gray unannotated;1 cyan light cloth candidate;2 orange ambiguous hair/shirt contact;3 violet protected hair context.'
review['PREP_frozen_contact_vertices']='11636,11637,11638: keep protected; ownership uncertain.'
review.world=source_scene.world
arm=source_arm.copy();arm.data=source_arm.data.copy();arm.name='REVIEW_V13_Rig';review.collection.objects.link(arm)
mesh=source_mesh.copy();mesh.data=source_mesh.data.copy();mesh.name='REVIEW_V13_Collar_Regions';review.collection.objects.link(mesh)
mesh.parent=arm;mesh.matrix_parent_inverse=source_mesh.matrix_parent_inverse.copy();mesh.matrix_world=source_mesh.matrix_world.copy()
for modifier in mesh.modifiers:
    if modifier.type=='ARMATURE':modifier.object=arm
mesh['PREP_annotation_only']=True
mesh['PREP_source_object']=source_mesh.name
assert not helper['_differences'](before,helper['_snapshot'](mesh.data))
assert np.array_equal(helper['_weights'](mesh.data,len(mesh.vertex_groups)),W)
attribute=mesh.data.attributes.new('prep_v13_review_region','INT','FACE');attribute.data.foreach_set('value',regions)
index_attr=mesh.data.attributes.new('prep_source_triangle_index','INT','FACE');index_attr.data.foreach_set('value',np.arange(len(T),dtype=np.int32))
vertex_attr=mesh.data.attributes.new('prep_source_vertex_index','INT','POINT');vertex_attr.data.foreach_set('value',np.arange(len(P),dtype=np.int32))
for light in (o for o in source_scene.objects if o.type=='LIGHT'):review.collection.objects.link(light)
camera=bpy.data.objects.new('REVIEW_V13_Camera',source_scene.camera.data.copy());review.collection.objects.link(camera);review.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=.70
review.render.engine='BLENDER_EEVEE';review.render.resolution_x=560;review.render.resolution_y=720;review.render.resolution_percentage=100
review.render.image_settings.file_format='PNG';review.view_settings.view_transform='AgX'
bpy.context.window.scene=review;bpy.context.view_layer.update()
clone_error=float(np.linalg.norm(points(mesh)-source_points,axis=1).max());assert clone_error<1e-5
renders=[]
def render_pair(prefix):
    for name,offset in [('back',(0,4,0)),('side',(4,0,0))]:
        center=Vector((.04,.03,1.39));camera.location=center+Vector(offset)
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        path=F/(prefix+'_'+name+'.png');review.render.filepath=str(path)
        bpy.ops.render.render(write_still=True);renders.append(str(path))
render_pair('textured')
material=bpy.data.materials.new('REVIEW_V13_Annotation_Colors_Not_Apparel');material.use_nodes=True
nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
output=nodes.new('ShaderNodeOutputMaterial');emission=nodes.new('ShaderNodeEmission')
attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='prep_v13_review_region'
divide=nodes.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=3
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.interpolation='CONSTANT'
ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1]);ramp.color_ramp.elements[0].color=(.14,.14,.14,1)
for position,color in [(.32,(.015,.65,.75,1)),(.65,(1,.32,.025,1)),(.98,(.38,.06,.75,1))]:
    element=ramp.color_ramp.elements.new(position);element.color=color
links.new(attr.outputs['Fac'],divide.inputs[0]);links.new(divide.outputs[0],ramp.inputs[0])
links.new(ramp.outputs['Color'],emission.inputs['Color']);links.new(emission.outputs[0],output.inputs['Surface'])
mesh.data.materials[0]=material
render_pair('regions')
bpy.context.window.scene=source_scene;bpy.context.view_layer.update()
after=helper['_snapshot'](source_mesh.data)
assert not helper['_differences'](before,after)
assert np.array_equal(helper['_weights'](source_mesh.data,len(source_mesh.vertex_groups)),W)
source_pose_error=float(np.linalg.norm(points(source_mesh)-source_points,axis=1).max());assert source_pose_error==0
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type!='VIEW_3D':continue
        space=area.spaces.active;space.shading.type='MATERIAL';space.overlay.show_overlays=False
        space.region_3d.view_location=Vector((0,0,.9));space.region_3d.view_distance=2.9
        space.region_3d.view_rotation=(Vector((0,0,.9))-Vector((1.4,-4,1.65))).to_track_quat('-Z','Y')
        space.region_3d.view_perspective='PERSP'
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
record={'status':'editable-collar-annotation-study-saved-not-garment-fit-or-game-asset',
 'library':str(WORK),'sha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),'checkpoint':str(CHECKPOINT),
 'source':str(SOURCE),'sourceSha256':state['savedPoseLibrary']['sha256'],
 'annotationSha256':hashlib.sha256(ANNOTATION.read_bytes()).hexdigest(),
 'regionFaceCounts':{str(i):int((regions==i).sum()) for i in range(4)},
 'reviewScene':review.name,'reviewMesh':mesh.name,'sourceMesh':source_mesh.name,
 'sourceArraysSha256':{k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in before['arrays'].items()},
 'sourceWeightSha256':hashlib.sha256(W.tobytes()).hexdigest(),
 'sourceAuthoringDataPreserved':True,'sourcePoseMaxError':source_pose_error,'clonePoseMaxError':clone_error,
 'renders':renders,'annotationOnly':True,'sourceGeometryChanged':False,'sourceWeightsChanged':False,
 'sourceMaterialsChanged':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,
 'nativeWalkValidated':False,'neutralPoseValidated':False,
 'remaining':'Lifted collar remains. Face annotations aid a later reviewed cloth split; three gray contact anchors remain frozen.'}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==state['savedPoseLibrary']['sha256']
OUT.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:record[k] for k in ('status','library','regionFaceCounts','sourcePoseMaxError','clonePoseMaxError')}))
