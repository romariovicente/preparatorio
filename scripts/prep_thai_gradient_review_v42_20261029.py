"""Build a diagnostic-only review mesh with unchanged bind and bone weights."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
I=ROOT/'work/probe_thai_gradient_diagnosis_v42_20261029/gradient_review_overlay_CPU_v42.npz'
OUT=ROOT/'reports/CHARACTER_THAI_GRADIENT_REVIEW_V42_20261029.json'
F=ROOT/'reports/thai_gradient_review_v42_20261029'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert I.exists() and not OUT.exists() and not F.exists()
stage=json.loads((ROOT/'reports/CHARACTER_THAI_GRADIENT_V42_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(stage['working']) and sha(stage['working'])==stage['workingSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
with np.load(I) as z:data={k:z[k].copy() for k in z.files}
assert str(data['sourceBodyBindSHA256'])==stage['actualSourceArchiveSha256']
with np.load(stage['actualSourceArchive']) as z:
    P=z['actualRestWorld'].copy();T=z['actualTriangles'].copy();W=z['actualWeights55'].copy();R=z['actualBoneRest55'].copy();names=z['actualNames55'].copy()
assert np.array_equal(data['restWorld'],P) and np.array_equal(data['triangles'],T) and np.array_equal(data['weights55'],W)
score=data['gradientMagnitudePerFace'];relative=data['relativeFailureFaceMask'].astype(bool);absolute=data['absoluteFailureFaceMask'].astype(bool)
review=data['reviewFaceIndices'].astype(int)
assert score.shape==relative.shape==absolute.shape==(len(T),) and np.isfinite(score).all() and score.min()>=0
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
source=bpy.data.objects[stage['sourceBody']];body=source.copy();body.data=source.data.copy()
body.name='V42_Skinning_Gradient_Review_Only';body.data.name='V42_V40_Exact_Mesh_Diagnostic_Corner_Colors'
scene.collection.objects.link(body);body.hide_render=False;body.hide_set(False,view_layer=layer)
source.hide_render=True;source.hide_set(True,view_layer=layer)
# Fixed diagnostic scale: normG=0 blue, sqrt(6)-1 yellow, >=5 red.
# It is a display scale, not a pose-quality threshold or clothing texture.
t=np.clip(np.log1p(score)/np.log(6),0,1).astype(np.float32)
face_colors=np.tile(np.array([.18,.22,.27,1],np.float32),(len(T),1))
value=t[review];rr=np.minimum(value*2,1);gg=np.where(value<.5,value*2,(1-value)*2);bb=np.maximum(1-value*2,0)
face_colors[review]=np.c_[rr,gg,bb,np.ones(len(review),np.float32)]
face_colors[relative]=[.95,.025,.6,1]
color=body.data.color_attributes.new(name='V42_Diagnostic_Gradient_Not_Outfit',type='FLOAT_COLOR',domain='CORNER')
assert len(body.data.loops)==len(T)*3
color.data.foreach_set('color',np.repeat(face_colors,3,axis=0).reshape(-1))
if hasattr(body.data.color_attributes,'active_color_index'):body.data.color_attributes.active_color_index=len(body.data.color_attributes)-1
if hasattr(body.data.color_attributes,'render_color_index'):body.data.color_attributes.render_color_index=len(body.data.color_attributes)-1
mat=bpy.data.materials.new('V42_DIAGNOSTIC_Gradient_Color_Only');mat.use_nodes=True
bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name=color.name
mat.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)
body['PREP_diagnostic_only_not_default_outfit']=True;body['PREP_geometry_or_weights_edited']=False
body['PREP_pose_correction_approved']=False;body['PREP_overlay_sha256']=sha(I)
body['PREP_relative_failure_source_face_ids']=np.flatnonzero(relative).tolist()
body['PREP_source_vertex_ids_unchanged']=True
body['PREP_legend']='Blue-yellow-red: spectral norm of spatial weight-gradient term (log1p scale,0..5). Magenta: relative pose gate failed. Gray: exterior review domain. Diagnostic, not clothing.'
body.data.polygons.foreach_set('select',relative)
body.select_set(True);layer.objects.active=body
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;space.shading.type='SOLID';space.shading.color_type='VERTEX'
        space.region_3d.view_location=Vector((0,0,.85));space.region_3d.view_distance=2.6
        space.region_3d.view_rotation=Vector((0,1,0)).to_track_quat('-Z','Y')
        space.region_3d.view_perspective='ORTHO'
scene['PREP_role']='Skinning gradient review only. V40 bind/weights/actions preserved. Not a playable map or approved character.'
native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
def choose(clip,frame):
    action=bpy.data.actions[clip+'.002']
    for arm in [native,rig]:
        arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
        for tr in arm.animation_data.nla_tracks:tr.mute=True
    scene.frame_set(frame);layer.update()
choose('Idle',101)
actual=h['_snapshot'](body.data)['arrays']
assert np.array_equal(actual['coordinates'],P) and np.array_equal(actual['triangles'],T) and np.array_equal(h['_weights'](body.data,55),W)
path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_GRADIENT_DIAGNOSTIC_V42_20261029.blend'
assert not path.exists();F.mkdir()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
saved_sha=sha(path);bodyname=body.name;scenename=scene.name
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
body=bpy.data.objects[bodyname];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
a=h['_snapshot'](body.data)['arrays'];ww=h['_weights'](body.data,55)
assert np.array_equal(a['coordinates'],P) and np.array_equal(a['triangles'],T) and np.array_equal(ww,W)
read_colors=np.empty(len(body.data.loops)*4,np.float32)
body.data.color_attributes['V42_Diagnostic_Gradient_Not_Outfit'].data.foreach_get('color',read_colors)
assert np.array_equal(read_colors.reshape(-1,4),np.repeat(face_colors,3,axis=0))
actual_archive={'actualRestWorld':a['coordinates'],'actualTriangles':a['triangles'],'actualWeights55':ww,
                'actualNames55':np.asarray(list(body.vertex_groups.keys())),
                'actualBoneRest55':np.array([np.array(native.data.bones[n].matrix_local) for n in names]),
                'actualCornerColors':read_colors.reshape(-1,4),'relativeFailureFaceMask':relative,
                'absoluteFailureFaceMask':absolute,'reviewFaceIndices':review}
assert len(body.modifiers)==1 and body.modifiers[0].type=='ARMATURE'
with np.load(stage['actualSourceArchive']) as z:
    for clip,frame in [('Idle',101),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}'
        for branch,arm in [('native',native),('corrected',rig)]:
            body.modifiers[0].object=arm;body.update_tag();layer.update()
            ev=body.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
            p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p)
            M=np.array(ev.matrix_world,dtype=float);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
            assert np.array_equal(q,z[label+'_'+branch+'BodyQ'])
            actual_archive[label+'_'+branch+'BodyQ']=q
body.modifiers[0].object=rig;body.update_tag();layer.update()
np.savez_compressed(F/'actual_reopened_review_bind_and_colors_v42.npz',**actual_archive)
# Diagnostic renders keep the saved original clothing visibility intact.
for o in scene.objects:
    if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_')) or o.get('V28_original_source_name','').split('.')[0]=='Shoes':o.hide_render=True
images=[]
def render(clip,frame,view,direction,detail=False):
    choose(clip,frame);camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.65 if detail else 1.93
    target=Vector((0,0,1.25 if detail else .84));camera.location=target+Vector(direction)*3
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    image=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(image)
    with bpy.context.temp_override(window=window):bpy.ops.render.render(write_still=True)
    images.append({'path':str(image),'sha256':sha(image),'diagnosticOnly':True})
render('Idle',101,'gradient_front',(0,-1,0));render('Idle',101,'gradient_axilla',(0,-1,0),True);render('Walk',19,'gradient_back',(0,1,0),True)
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
assert sha(stage['source'])==stage['sourceSha256'] and sha(path)==saved_sha
archive=F/'actual_reopened_review_bind_and_colors_v42.npz'
result={'status':'diagnostic-gradient-review-saved-reopened-no-pose-correction-claimed','library':str(path),'sha256':saved_sha,
 'scene':scenename,'bodyObject':bodyname,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
 'overlay':str(I),'overlaySha256':sha(I),'archive':str(archive),'archiveSha256':sha(archive),
 'relativeFailureFaces':int(relative.sum()),'absoluteFailureFaces':int(absolute.sum()),'reviewFaces':len(review),
 'sourceGeometry55WeightsRestActionsPreserved':True,'colorsAreDiagnosticNotDefaultOutfit':True,'images':images,
 'newSkinWeightsOrGeometryProposed':False,'poseApproved':False,'clothesApproved':False,'runtimeChanged':False,'masterChanged':False,
 'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='images'}))
