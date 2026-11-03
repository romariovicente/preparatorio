"""A distinct, narrower deliverable: static unbound source plus separate guide.

The attempted bound stage is rejected. Do not treat removing its binding as
repairing that rig. The only accepted contract here is baseline appearance.
"""
import bpy,json,hashlib,runpy,shutil,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_rebind_stage_v23_20261027'
LIB=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REBIND_STAGE_V23_20261027.blend'
CP=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_REBIND_STAGE_V23_20261027.blend'
REPORT=ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json'
STATUS=ROOT/'work/v23_unbound_source_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not REPORT.exists()and not STATUS.exists()and Path(bpy.data.filepath)==LIB
    old=json.loads((ROOT/'work/v23_rebind_stage_status_20261027.json').read_text())
    assert old['status']=='error' and '91.582' in old['error']
    diag=ROOT/'work/qa_thai_rebind_stage_v23_20261027/normal_encoding_diagnostic.json'
    diagnostic=json.loads(diag.read_text())
    assert diagnostic['copiedMeshEvaluated']['exceedPoint05']==27
    assert diagnostic['copiedMeshStored']['maximumDegrees']<.05
    session=json.loads((ROOT/'reports/CHARACTER_THAI_POSTURE_V21_MCP_SESSION_20261027.json').read_text())
    prior=json.loads((ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.json').read_text())
    assert sha(session['workingLibrary'])==session['sha256']and sha(CP)==session['sha256']
    helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    E=ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz'
    with np.load(E)as n:e={k:n[k].copy()for k in n.files}
    with np.load(ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz')as n:oldrig={k:n[k].copy()for k in n.files}
    body=bpy.data.objects['V23_Rebind_Staging_Baseline_Avatar'];guide=body.parent;scene=body.users_scene[0]
    assert len(body.modifiers)==1 and body.modifiers[0].type=='ARMATURE'
    body.modifiers.clear();body.parent=None;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_world=Matrix.Identity(4)
    body.name='V23_UNBOUND_World_Baseline_Source';guide.name='V23_SEPARATE_REST_GUIDE_NOT_BOUND'
    guide['PREP_role']='Separate guide snapshot only; no mesh binding, no functional rig approval'
    body['PREP_role']='Static unbound evaluated baseline; vertex weights retained only as historical reference'
    body['PREP_bound_stage_rejected']=True
    body['PREP_bound_stage_max_normal_error_degrees']=diagnostic['copiedMeshEvaluated']['maximumDegrees']
    scene.name='REVIEW_THAI_UNBOUND_SOURCE_V23'
    scene['PREP_role']='UNBOUND_STATIC_SOURCE_ONLY; separate guide; bound stage failed normal fidelity'
    window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0];layer.update()
    def evaluated(obj,lyr):
        lyr.update();ev=obj.evaluated_get(lyr.depsgraph);m=ev.to_mesh();a=helper['_snapshot'](m)['arrays'];M=np.array(ev.matrix_world)
        q=a['coordinates']@M[:3,:3].T+M[:3,3];d=a['cornerNormals']@np.linalg.inv(M[:3,:3]);d=d.astype(float);d/=np.linalg.norm(d,axis=1)[:,None];ev.to_mesh_clear();return q,d
    q,d=evaluated(body,layer);target=e['evaluatedCornerNormalsWorld']
    qerr=float(np.linalg.norm(q-e['posedWorld'],axis=1).max());nerr=float(np.degrees(np.arccos(np.clip((d*target).sum(1),-1,1))).max())
    assert qerr<1e-6 and nerr<.05,(qerr,nerr)
    a=helper['_snapshot'](body.data)['arrays']
    original=bpy.data.objects[prior['baselineBody']];oa=helper['_snapshot'](original.data)['arrays']
    assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in oa.items()}==prior['bodyArraysSha256']
    for k,v in oa.items():
        if k not in('coordinates','cornerNormals'):assert np.array_equal(a[k],v),k
    sharp_flags=[]
    for obj in(original,body):
        attr=obj.data.attributes.get('sharp_edge');values=np.zeros(len(obj.data.edges),bool)
        if attr:attr.data.foreach_get('value',values)
        sharp_flags.append(values)
    assert np.array_equal(*sharp_flags),'Implicit sharp-edge flags changed; do not reset them to force fidelity'
    w=helper['_weights'](body.data,len(body.vertex_groups));assert np.array_equal(w,e['weights'])
    source_scene=bpy.data.scenes[session['activeScene']];sq,sd=evaluated(original,source_scene.view_layers[0])
    assert np.array_equal(sq,e['posedWorld'])
    source_normal_difference=float(np.degrees(np.arccos(np.clip((sd*target).sum(1),-1,1))).max())
    assert source_normal_difference<.05
    names=oldrig['group_names'].tolist();parents=oldrig['parent_indices'];aw=oldrig['arm_world']
    desired_heads=oldrig['bone_pose_heads']@aw[:3,:3].T+aw[:3,3]
    desired_tails=oldrig['bone_pose_tails']@aw[:3,:3].T+aw[:3,3]
    heads=np.array([list(guide.data.bones[n].head_local)for n in names]);tails=np.array([list(guide.data.bones[n].tail_local)for n in names])
    joint_error=float(max(np.linalg.norm(heads-desired_heads,axis=1).max(),np.linalg.norm(tails-desired_tails,axis=1).max()))
    assert joint_error<2e-6 and all(not b.use_connect for b in guide.data.bones)
    assert all(np.array_equal(np.array(guide.pose.bones[n].matrix_basis),np.eye(4))for n in names)
    assert np.array_equal(np.array(guide.matrix_world),np.eye(4))and np.array_equal(np.array(body.matrix_world),np.eye(4))
    for i,n in enumerate(names):assert (guide.data.bones[n].parent.name if guide.data.bones[n].parent else None)==(names[int(parents[i])]if parents[i]>=0 else None)
    assert not body.modifiers and body.parent is None and body.animation_data is None and guide.animation_data is None
    camera=bpy.data.objects.new('V23_Unbound_Source_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);camera.matrix_world=source_scene.camera.matrix_world.copy();scene.camera=camera
    for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
    note=bpy.data.texts.new('READ_ME_V23_UNBOUND_ONLY_BOUND_ATTEMPT_FAILED.txt')
    note.write('UNBOUND STATIC SOURCE ONLY\n\nThe attempted bound rest rig was rejected: Armature evaluation changed 27 corner normals, up to 91.582 degrees. The failed attempt and normal arrays are retained in work/reports. No threshold was relaxed.\n\nThis is a distinct, narrower deliverable: a static mesh with the old evaluated standing surface and normals baked into world coordinates, plus a separate unbound guide snapshot. The mesh has NO parent, NO Armature modifier and NO action. W is retained only as historical reference. The guide has no functional binding.\n\nCurrent asymmetric posture, scan holes and incomplete clothing remain. This is NOT a rig repair, new pose, native Walk, Mixamo result or anatomical certification. Do not promote to the game. A future rebind must address normal fidelity and skinning across the whole body before motion approval.\n')
    scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=1.9
    layer.objects.active=body;body.select_set(True,view_layer=layer);guide.select_set(False,view_layer=layer)
    shutil.copy2(diag,F/'normal_encoding_failed_bound_diagnostic.json')
    shutil.copy2(ROOT/'work/qa_thai_rebind_stage_v23_20261027/normal_encoding_failed_attempt.npz',F/'failed_bound_normal_arrays.npz')
    np.savez_compressed(F/'unbound_source_baseline_export.npz',posedWorld=q,evaluatedCornerNormalsWorld=d,storedPositions=a['coordinates'],storedCornerNormals=a['cornerNormals'],triangles=a['triangles'],weights=w,guideRestFrames=np.array([np.array(guide.data.bones[n].matrix_local)for n in names]),guideRestHeads=heads,guideRestTails=tails,groupNames=np.array(names),parentIndices=parents)
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(LIB),compress=True)
    assert sha(session['workingLibrary'])==session['sha256']and sha(CP)==session['sha256']
    result={'status':'unbound-static-source-and-separate-guide-saved-awaiting-reopen-preview-qa','library':str(LIB),'sha256':sha(LIB),'checkpoint':str(CP),'checkpointSha256':sha(CP),'source':session['workingLibrary'],'sourceSha256':session['sha256'],'scene':scene.name,'body':body.name,'guide':guide.name,'sourceBody':original.name,'sourceScene':source_scene.name,'bodyArraysSha256':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()},'weightsSha256':hashlib.sha256(w.tobytes()).hexdigest(),'maximumBaselineWorldPointErrorMeters':qerr,'maximumBaselineWorldNormalErrorDegrees':nerr,'maximumGuideJointErrorMeters':joint_error,'worldObjectMatricesIdentity':True,'guidePoseBasesIdentity':True,'guideParentsPreservedUseConnectFalse':True,'meshHasNoParentOrModifierOrAction':True,'guideNotBoundToMesh':True,'weightsHistoricalReferenceOnly':True,'topologyAllUVWeightsMaterialsSmoothingExact':True,'boundRigStageRejected':True,'rejectedBoundStageMaximumNormalErrorDegrees':diagnostic['copiedMeshEvaluated']['maximumDegrees'],'rejectedBoundStageNormalCountOverPoint05':27,'postureFixed':False,'weightsRepaired':False,'nativeWalkValidated':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'scope':'Distinct narrower contract: static unbound rebind source plus separate guide only. Bound rig attempt remains rejected, old posture and defects remain.'}
    REPORT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(REPORT)},indent=2));print(json.dumps(result))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
