"""Create a separate rest staging copy of the actual evaluated V21 baseline.

This establishes a reproducible starting surface for a future broad rebind.
It does not correct posture, weights, skin holes, clothing or native Walk.
"""
import bpy,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from datetime import datetime,timezone
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_rebind_stage_v23_20261027'
LIB=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REBIND_STAGE_V23_20261027.blend'
CP=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_REBIND_STAGE_V23_20261027.blend'
REPORT=ROOT/'reports/CHARACTER_THAI_REBIND_STAGE_V23_20261027.json'
STATUS=ROOT/'work/v23_rebind_stage_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def evaluated(obj,layer):
    layer.update();ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh()
    a=helper['_snapshot'](m)['arrays'];world=np.array(ev.matrix_world)
    q=a['coordinates']@world[:3,:3].T+world[:3,3]
    d=a['cornerNormals']@np.linalg.inv(world[:3,:3])
    d/=np.linalg.norm(d,axis=1)[:,None]
    ev.to_mesh_clear()
    return q,d

try:
    assert not any(p.exists()for p in(LIB,CP,REPORT,STATUS,F))
    assert not bpy.app.background
    desktop=json.loads((ROOT/'work/blender_desktop_v21_20261027.json').read_text())
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(desktop['ObservedAt'])).total_seconds()<900
    assert len(desktop['BlenderWindows'])==1 and desktop['BlenderWindows'][0]['DesktopIndex']==1
    session=json.loads((ROOT/'reports/CHARACTER_THAI_POSTURE_V21_MCP_SESSION_20261027.json').read_text())
    prior=json.loads((ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.json').read_text())
    source=Path(session['workingLibrary'])
    assert Path(bpy.data.filepath)==source and not bpy.data.is_dirty and sha(source)==session['sha256']
    export_report=json.loads((ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.json').read_text())
    assert sha(export_report['npz'])==export_report['npzSHA256']
    with np.load(export_report['npz'])as n:e={k:n[k].copy()for k in n.files}
    with np.load(ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz')as n:rig={k:n[k].copy()for k in n.files}
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    source_scene=bpy.data.scenes[session['activeScene']];source_layer=source_scene.view_layers[0]
    original=bpy.data.objects[prior['baselineBody']]
    helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    before=helper['_snapshot'](original.data)
    assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in before['arrays'].items()}==prior['bodyArraysSha256']
    assert np.array_equal(helper['_weights'](original.data,len(original.vertex_groups)),e['weights'])
    source_q,source_d=evaluated(original,source_layer)
    assert np.array_equal(source_q,e['posedWorld'])and np.array_equal(source_d,e['evaluatedCornerNormalsWorld'])
    assert original.data.shape_keys is None
    shutil.copy2(source,CP);F.mkdir()
    with bpy.context.temp_override(window=window,scene=source_scene,view_layer=source_layer):
        bpy.ops.wm.save_as_mainfile(filepath=str(LIB),compress=True)
    scene=bpy.data.scenes.new('REVIEW_THAI_REBIND_STAGE_V23')
    scene.world=source_scene.world
    scene['PREP_role']='REBIND_BASELINE_STAGE_ONLY; old posture preserved; no repaired weights or motion approval'
    arm_data=bpy.data.armatures.new('V23_CURRENT_POSE_AS_REST_DATA')
    arm=bpy.data.objects.new('V23_Rebind_Staging_Rig',arm_data)
    scene.collection.objects.link(arm)
    arm.matrix_world=Matrix.Identity(4);arm.show_in_front=True
    window.scene=scene;layer=scene.view_layers[0];layer.objects.active=arm;arm.select_set(True,view_layer=layer)
    names=rig['group_names'].tolist();parents=rig['parent_indices'];world=rig['arm_world']
    heads=rig['bone_pose_heads']@world[:3,:3].T+world[:3,3]
    tails=rig['bone_pose_tails']@world[:3,:3].T+world[:3,3]
    pose_world=np.einsum('ij,njk->nik',world,rig['bone_pose_matrices'])
    frames=[]
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer,active_object=arm,object=arm):
        bpy.ops.object.mode_set(mode='EDIT')
        for i,name in enumerate(names):
            bone=arm_data.edit_bones.new(name)
            bone.head=Vector(heads[i]);bone.tail=Vector(tails[i])
            z=pose_world[i,:3,2];z=z/np.linalg.norm(z)
            bone.align_roll(Vector(z))
            bone.use_connect=False
            bone.use_deform=original.parent.data.bones[name].use_deform
        for i,name in enumerate(names):
            if parents[i]>=0:arm_data.edit_bones[name].parent=arm_data.edit_bones[names[int(parents[i])]]
        bpy.ops.object.mode_set(mode='OBJECT')
    for i,name in enumerate(names):
        bone=arm.pose.bones[name];bone.rotation_mode=original.parent.pose.bones[name].rotation_mode
        bone.matrix_basis=Matrix.Identity(4)
        frames.append(np.array(arm.data.bones[name].matrix_local))
    arm.data.pose_position='POSE'
    body=original.copy();body.data=original.data.copy();body.animation_data_clear()
    body.name='V23_Rebind_Staging_Baseline_Avatar';body.data.name='V23_Evaluated_World_Baseline_Mesh'
    scene.collection.objects.link(body)
    body.parent=arm;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
    for mod in body.modifiers:
        if mod.type=='ARMATURE':mod.object=arm
        else:raise ValueError('Unexpected source modifier: '+mod.type)
    body.data.vertices.foreach_set('co',e['posedWorld'].astype(np.float32).reshape(-1))
    body.data.update()
    body.data.normals_split_custom_set(e['evaluatedCornerNormalsWorld'].tolist())
    body['PREP_baseline_origin']='Exact evaluated standing surface baked from WORK V21; not healthy rest anatomy'
    body['PREP_weights_repaired']=False;body['PREP_motion_validated']=False
    layer.update();q,d=evaluated(body,layer)
    qerr=float(np.linalg.norm(q-source_q,axis=1).max())
    dots=np.clip(np.sum(d*source_d,axis=1),-1,1)
    nerr=float(np.degrees(np.arccos(dots)).max())
    assert qerr<1e-6 and nerr<.05,(qerr,nerr)
    a=helper['_snapshot'](body.data)['arrays']
    for key,v in before['arrays'].items():
        if key not in('coordinates','cornerNormals'):assert np.array_equal(a[key],v),key
    assert np.array_equal(helper['_weights'](body.data,len(body.vertex_groups)),e['weights'])
    newheads=np.array([list(arm.data.bones[n].head_local)for n in names])
    newtails=np.array([list(arm.data.bones[n].tail_local)for n in names])
    joint_error=float(max(np.linalg.norm(newheads-heads,axis=1).max(),np.linalg.norm(newtails-tails,axis=1).max()))
    assert joint_error<2e-6
    assert all(np.array_equal(np.array(arm.pose.bones[n].matrix_basis),np.eye(4))for n in names)
    camera=bpy.data.objects.new('V23_Staging_Camera',source_scene.camera.data.copy())
    scene.collection.objects.link(camera);camera.matrix_world=source_scene.camera.matrix_world.copy();scene.camera=camera
    for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
    note=bpy.data.texts.new('READ_ME_V23_BASELINE_STAGE_ONLY.txt')
    note.write('REBIND STAGING ONLY\nThe old posed mesh and evaluated normals are baked into world coordinates. The new rest rig uses the current world pose, unit object scale and identity pose bases. All stored weights, topology, per-corner UVs, smoothing and materials are preserved.\n\nThis only proves an unchanged baseline starting point for a wider rebind. Existing asymmetric posture, skin holes and clothing defects remain. Old weights are not certified and old actions were not copied to the new rig. No Walk, Mixamo, anatomy or gameplay approval. Do not promote to the game.\n\nParent hierarchy is retained but use_connect is false: shoulder/thigh offsets are intentional and must not be snapped to parent tails. Source and checkpoints are intact; local edits only.\n')
    layer.objects.active=body;arm.select_set(False,view_layer=layer);body.select_set(True,view_layer=layer)
    assert not helper['_differences'](before,helper['_snapshot'](original.data))
    oq,od=evaluated(original,source_layer)
    assert np.array_equal(oq,source_q)and np.array_equal(od,source_d)
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):
        bpy.ops.wm.save_as_mainfile(filepath=str(LIB),compress=True)
    np.savez_compressed(F/'staging_baseline_export.npz',posedWorld=q,evaluatedCornerNormalsWorld=d,storedPositions=a['coordinates'],storedCornerNormals=a['cornerNormals'],triangles=a['triangles'],weights=e['weights'],boneRestFrames=np.array(frames),boneRestHeads=newheads,boneRestTails=newtails,groupNames=np.array(names),parentIndices=parents)
    assert sha(source)==session['sha256']and sha(CP)==session['sha256']
    result={'status':'separate-rebind-baseline-stage-saved-awaiting-reopen-and-visual-qa','library':str(LIB),'sha256':sha(LIB),'checkpoint':str(CP),'checkpointSha256':sha(CP),'source':str(source),'sourceSha256':session['sha256'],'scene':scene.name,'body':body.name,'rig':arm.name,'sourceBody':original.name,'sourceScene':source_scene.name,'bodyArraysSha256':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()},'weightsSha256':hashlib.sha256(e['weights'].tobytes()).hexdigest(),'maximumBaselineWorldPointErrorMeters':qerr,'maximumBaselineWorldNormalErrorDegrees':nerr,'maximumRigJointErrorMeters':joint_error,'worldObjectMatricesIdentity':True,'poseBasesIdentity':True,'parentsPreservedWithUseConnectFalse':True,'nativeActionsCopiedToNewRig':False,'positionsAndCustomNormalsIntentionallyBakedFromEvaluatedWorld':True,'topologyAllUVWeightsMaterialsAndSmoothingExact':True,'sourceStoredDataAndEvaluatedAppearancePreserved':True,'sourceFilesPreserved':True,'postureFixed':False,'weightsRepaired':False,'nativeWalkValidated':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'scope':'Baseline-only staging for future rebind. Current defects remain; no new animation or posture accepted.'}
    REPORT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(REPORT)},indent=2));print(json.dumps(result))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
