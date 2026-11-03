"""Install, save/reopen, and exercise the explicit-session review UI via bpy.ops."""
import bpy,json,hashlib,runpy,sys,types,shutil
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
CODE=ROOT/'scripts/pose_review_controller_v44_20261029.py'
F=ROOT/'reports/pose_review_controller_v44_20261029'
OUT=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json'
assert not OUT.exists() and not F.exists()
stage=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(stage['working']) and sha(stage['working'])==stage['workingSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
source=bpy.data.objects[stage['sourceBody']]
body=source.copy();body.data=source.data.copy();body.name='V44_Interactive_Pose_Study_Actor';body.data.name='V44_V40_Exact_Bind_With_Review_Offsets'
scene.collection.objects.link(body);body.hide_render=False;body.hide_set(False,view_layer=layer)
assert len(body.modifiers)==2 and body.modifiers[1].type=='NODES'
body.modifiers[1].node_group=body.modifiers[1].node_group.copy();body.modifiers[1].node_group.name='V44_Pose_Review_Offset_Only'
body['PREP_interactive_pose_review_v44']=True
body['PREP_review_native_rig']=stage['nativeRig'];body['PREP_review_pose_rig']=stage['poseRig']
body['PREP_review_is_samples_not_continuous_animation']=True
source.hide_render=True;source.hide_set(True,view_layer=layer)
body.select_set(True);layer.objects.active=body
textname='PREPARATORIO_V44_REVIEW_CONTROLS_EXPLICIT_RUN.py'
assert textname not in bpy.data.texts
text=bpy.data.texts.new(textname);text.from_string(CODE.read_text(encoding='utf-8'));text.use_module=False
def handlers():
    return {name:len(getattr(bpy.app.handlers,name)) for name in ['frame_change_pre','frame_change_post','load_pre','load_post','save_pre','save_post']}
handlers_before=handlers();autorun_before=bpy.context.preferences.filepaths.use_scripts_auto_execute
def module_register():
    module=types.ModuleType('preparatorio_review_v44');module.__file__=str(CODE)
    sys.modules[module.__name__]=module
    exec(compile(CODE.read_text(encoding='utf-8'),str(CODE),'exec'),module.__dict__)
    module.register();return module
module=module_register()
def settings(branch,variant):
    scene['PREP_review_settings_guard']=True
    try:scene.prep44_branch=branch;scene.prep44_variant=variant
    finally:scene['PREP_review_settings_guard']=False
settings('corrected','study')
assert bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)=={'FINISHED'}
for area in window.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.show_region_ui=True;area.tag_redraw()
scene['PREP_role']='Interactive review of eight existing pose samples. Base/corrective comparison only; not a validated full animation or game.'
path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_REVIEW_V44_20261029.blend'
assert not path.exists();F.mkdir()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
saved_sha=sha(path);bodyname=body.name;scenename=scene.name
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
body=bpy.data.objects[bodyname]
module=module_register()  # Explicit after reopen; no handler or trusted-file preference.
settings('corrected','study')
assert bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)=={'FINISHED'}
a=h['_snapshot'](body.data)['arrays'];W=h['_weights'](body.data,55)
native=bpy.data.objects[stage['nativeRig']]
names=list(body.vertex_groups.keys());R=np.array([np.array(native.data.bones[n].matrix_local,dtype=float) for n in names])
archive={'actualRestWorld':a['coordinates'],'actualTriangles':a['triangles'],'actualWeights55':W,'actualNames55':np.asarray(names),'actualBoneRest55':R}
def point_q():
    body.update_tag();layer.update();ev=body.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
    p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
    q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
def state():
    offset=np.empty(len(body.data.vertices)*3,np.float32);body.data.attributes[module.ATTR].data.foreach_get('vector',offset)
    arrays=h['_snapshot'](body.data)['arrays'];ww=h['_weights'](body.data,55)
    rigs=[]
    for name in [stage['nativeRig'],stage['poseRig']]:
        arm=bpy.data.objects[name];action=arm.animation_data.action;slot=arm.animation_data.action_slot
        rigs.append({'rig':name,'action':action.name if action else None,'slot':slot.identifier if slot else None})
    return {'frame':scene.frame_current,'range':[scene.frame_start,scene.frame_end],
            'rigs':rigs,'targetArmature':body.modifiers[0].object.name,'GNenabled':body.modifiers[1].show_viewport,
            'offsetHash':hashlib.sha256(offset.tobytes()).hexdigest(),'coordinateHash':hashlib.sha256(arrays['coordinates'].tobytes()).hexdigest(),
            'triangleHash':hashlib.sha256(arrays['triangles'].tobytes()).hexdigest(),'weightHash':hashlib.sha256(ww.tobytes()).hexdigest(),
            'restHash':hashlib.sha256(R.tobytes()).hexdigest(),'sourceCurveSignatures':u['action_signatures'](),
            'sample':[body.get('PREP_snapshot_clip'),body.get('PREP_snapshot_frame'),body.get('PREP_snapshot_branch'),body.get('PREP_review_variant')]}
cases=[]
for clip,frames in module.SAMPLES.items():
    for frame in frames:
        for branch in ['native','corrected']:
            for variant in ['base','study']:
                settings(branch,variant)
                assert bpy.ops.preparatorio.review_pose_sample_v44(clip=clip,sample_frame=frame)=={'FINISHED'}
                label=f'{clip}_{frame}_{branch}_{variant}';q=point_q();offset=np.empty(len(body.data.vertices)*3,np.float32)
                body.data.attributes[module.ATTR].data.foreach_get('vector',offset)
                archive[label+'Q']=q;archive[label+'Offset']=offset.reshape(-1,3)
                cases.append({'label':label,'sample':f'{clip}_{frame}','clip':clip,'frame':frame,'branch':branch,'mode':variant,
                              'Qkey':label+'Q','offsetKey':label+'Offset','state':state()})
callbacks=[]
scene.prep44_variant='base';callbacks.append({'property':'variant','value':'base','state':state()})
scene.prep44_branch='corrected';callbacks.append({'property':'branch','value':'corrected','state':state()})
def reject_case(label,callback):
    before=state();caught=None;result=None
    try:result=callback()
    except Exception as exc:caught=str(exc)
    after=state();refused=result=={'CANCELLED'} or caught is not None
    assert refused and before==after,label
    return {'label':label,'refused':refused,'error':caught,'stateBefore':before,'stateAfter':after,'unchanged':before==after}
negative=[]
negative.append(reject_case('unsupported-frame',lambda:bpy.ops.preparatorio.review_pose_sample_v44(clip='Walk',sample_frame=99)))
fixture=F/'tampered_candidate_COPY_only.npz';shutil.copy2(module.CANDIDATE,fixture)
with fixture.open('ab') as stream:stream.write(b'PREP44_INVALID_COPY_FIXTURE')
original_candidate=module.CANDIDATE
try:
    module.CANDIDATE=fixture;module._CACHE=None
    negative.append(reject_case('tampered-copy-not-original',lambda:bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)))
finally:module.CANDIDATE=original_candidate;module._CACHE=None
vertex=0;bone=int(np.flatnonzero(W[vertex]>0)[0]);old_weight=float(W[vertex,bone])
try:
    body.vertex_groups[bone].add([vertex],old_weight*.9,'REPLACE');body.data.update()
    negative.append(reject_case('edited-review-actor-weight',lambda:bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)))
finally:body.vertex_groups[bone].add([vertex],old_weight,'REPLACE');body.data.update()
assert np.array_equal(h['_weights'](body.data,55),W)
settings('corrected','study');assert bpy.ops.preparatorio.review_pose_sample_v44(clip='Idle',sample_frame=101)=={'FINISHED'}
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
assert bpy.data.texts[textname].as_string()==CODE.read_text(encoding='utf-8') and not bpy.data.texts[textname].use_module
assert handlers()==handlers_before and bpy.context.preferences.filepaths.use_scripts_auto_execute==autorun_before
assert sha(stage['source'])==stage['sourceSha256'] and sha(path)==saved_sha and sha(stage['candidate'])==stage['candidateSha256']
ar=F/'actual_review_controller_cases_v44.npz';np.savez_compressed(ar,**archive)
result={'status':'review-controller-saved-reopened-32-API-cases-awaiting-independent-QA','library':str(path),'sha256':saved_sha,
 'scene':scenename,'actor':bodyname,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
 'controller':str(CODE),'controllerSha256':sha(CODE),'textBlock':textname,'textBlockSHA256':hashlib.sha256(bpy.data.texts[textname].as_string().encode()).hexdigest(),
 'textBlockUseModule':False,'explicitRegistrationAfterReopen':True,'panelRNARegistered':hasattr(bpy.types,'PREP44_PT_PoseReview'),
 'operatorRNARegistered':hasattr(bpy.types,'PREP44_OT_PoseSample'),'humanClicksClaimed':False,
 'archive':str(ar),'archiveSha256':sha(ar),'cases':cases,'propertyCallbacks':callbacks,'negativeCases':negative,
 'handlersBefore':handlers_before,'handlersAfter':handlers(),'autoExecutionPreferenceUnchanged':True,
 'sourceGeometryRestWeightsCurvesPreserved':True,'newSolverExecuted':False,'snapshotSamplesOnly':True,'fullAnimationApproved':False,
 'clothesApproved':False,'runtimeChanged':False,'masterChanged':False,'newWindowOpened':False,'windowFocusedOrMoved':False,
 'desktopSwitched':False,'remoteOperations':False,'MCPUsed':True}
OUT.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['cases','propertyCallbacks','negativeCases']}))
