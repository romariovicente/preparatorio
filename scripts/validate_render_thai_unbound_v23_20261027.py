"""Reopen and preview the static UNBOUND source, never approve its old motion."""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_rebind_stage_v23_20261027'
REPORT=ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json'
OUT=ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_REOPEN_PREVIEW_20261027.json'
STATUS=ROOT/'work/v23_unbound_reopen_preview_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and not STATUS.exists()
    r=json.loads(REPORT.read_text());lib=Path(r['library'])
    assert Path(bpy.data.filepath)==lib and sha(lib)==r['sha256']and not bpy.data.is_dirty
    assert sha(r['source'])==r['sourceSha256']and sha(r['checkpoint'])==r['sourceSha256']
    bpy.ops.wm.open_mainfile(filepath=str(lib),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    body=bpy.data.objects[r['body']];guide=bpy.data.objects[r['guide']];source=bpy.data.objects[r['sourceBody']]
    stage_scene=bpy.data.scenes[r['scene']];source_scene=bpy.data.scenes[r['sourceScene']]
    stage_layer=stage_scene.view_layers[0];source_layer=source_scene.view_layers[0]
    def evaluated(obj,layer):
        layer.update();ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh();a=h['_snapshot'](m)['arrays'];M=np.array(ev.matrix_world)
        q=a['coordinates']@M[:3,:3].T+M[:3,3];d=a['cornerNormals'].astype(float)@np.linalg.inv(M[:3,:3]);d/=np.linalg.norm(d,axis=1)[:,None];ev.to_mesh_clear();return q,d
    with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:expected={k:n[k].copy()for k in n.files}
    source_q,source_d=evaluated(source,source_layer);q,d=evaluated(body,stage_layer)
    qerr=float(np.linalg.norm(q-expected['posedWorld'],axis=1).max())
    nerr=float(np.degrees(np.arccos(np.clip((d*expected['evaluatedCornerNormalsWorld']).sum(1),-1,1))).max())
    assert qerr<1e-6 and nerr<.05 and np.array_equal(source_q,expected['posedWorld'])
    stage_a=h['_snapshot'](body.data)['arrays'];source_a=h['_snapshot'](source.data)['arrays']
    assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in stage_a.items()}==r['bodyArraysSha256']
    for k,v in source_a.items():
        if k not in('coordinates','cornerNormals'):assert np.array_equal(v,stage_a[k])
    weights=h['_weights'](body.data,len(body.vertex_groups));assert np.array_equal(weights,expected['weights'])
    assert body.parent is None and not body.modifiers and body.animation_data is None and not body.constraints
    assert guide.animation_data is None and not guide.constraints and not guide.parent
    assert all(not b.constraints and np.array_equal(np.array(b.matrix_basis),np.eye(4))for b in guide.pose.bones)
    assert np.array_equal(np.array(body.matrix_world),np.eye(4))and np.array_equal(np.array(guide.matrix_world),np.eye(4))
    assert len(source.data.materials)==len(body.data.materials)and all(a is b for a,b in zip(source.data.materials,body.data.materials))
    names=[g.name for g in body.vertex_groups];assert names==[g.name for g in source.vertex_groups]
    payload={'posedWorld':q,'evaluatedCornerNormalsWorld':d,'sourcePosedWorld':source_q,'sourceEvaluatedCornerNormalsWorld':source_d,'weights':weights,'sourceWeights':h['_weights'](source.data,len(source.vertex_groups)),'groupNames':np.array(names),'sourceGroupNames':np.array([g.name for g in source.vertex_groups]),'bodyWorld':np.array(body.matrix_world),'guideWorld':np.array(guide.matrix_world),'guidePoseBases':np.array([np.array(guide.pose.bones[n].matrix_basis)for n in names]),'guideRestFrames':np.array([np.array(guide.data.bones[n].matrix_local)for n in names]),'guideRestHeads':np.array([list(guide.data.bones[n].head_local)for n in names]),'guideRestTails':np.array([list(guide.data.bones[n].tail_local)for n in names]),'guideParents':np.array([names.index(guide.data.bones[n].parent.name)if guide.data.bones[n].parent else-1 for n in names],np.int32),'guideUseConnect':np.array([guide.data.bones[n].use_connect for n in names]),'bodyParentName':np.array(''),'bodyModifierTypes':np.array([],dtype='U20'),'bodyActionName':np.array(''),'guideActionName':np.array(''),'materialNames':np.array([m.name for m in body.data.materials]),'sourceMaterialNames':np.array([m.name for m in source.data.materials])}
    for label,arrays,obj in(('source',source_a,source),('stage',stage_a,body)):
        for key,v in arrays.items():payload[label+'::'+key]=v
        attr=obj.data.attributes.get('sharp_edge');sharp=np.zeros(len(obj.data.edges),bool)
        if attr:attr.data.foreach_get('value',sharp)
        payload[label+'::sharpEdge']=sharp
    assert np.array_equal(payload['source::sharpEdge'],payload['stage::sharpEdge'])
    full=F/'reopened_full_baseline_export.npz';assert not full.exists();np.savez_compressed(full,**payload)
    folder=F/'matched_previews';assert not folder.exists();folder.mkdir()
    images=[]
    for name,direction in(('front',(0,-1,0)),('right',(-1,0,0)),('back',(0,1,0))):
        for label,scene in(('before_source',source_scene),('after_unbound',stage_scene)):
            window.scene=scene;layer=scene.view_layers[0];layer.update()
            scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=512;scene.render.resolution_y=768;scene.render.resolution_percentage=100
            scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX'
            camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.85
            target=Vector((0,0,.85));camera.location=target+Vector(direction)*3;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            path=folder/(name+'_'+label+'.png');scene.render.filepath=str(path)
            (ROOT/'work/v23_unbound_render_progress_20261027.json').write_text(json.dumps({'view':name,'state':label}))
            with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
            images.append({'view':name,'state':label,'path':str(path),'sha256':sha(path)})
    assert sha(lib)==r['sha256']and sha(r['source'])==r['sourceSha256']
    # Discard preview camera/render changes; restore the exact saved work session.
    bpy.ops.wm.open_mainfile(filepath=str(lib),load_ui=False,use_scripts=False)
    result={'status':'unbound-static-source-reopened-baseline-preserved-and-six-matched-previews-rendered','library':str(lib),'sha256':r['sha256'],'maximumBaselinePointErrorMeters':qerr,'maximumBaselineWorldNormalErrorDegrees':nerr,'fullReopenExport':str(full),'fullReopenExportSha256':sha(full),'sourceFileAndCheckpointIntact':True,'UVTopologyWeightsMaterialsSmoothAndSharpEdgeFlagsExact':True,'meshUnboundNoParentModifierActionOrConstraint':True,'separateGuideWorldAndBasesIdentityNoActionOrConstraint':True,'images':images,'savedSessionRestoredWithoutSavingPreviewChanges':True,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'boundRigStageStillRejected':True,'postureFixed':False,'weightsRepaired':False,'nativeWalkValidated':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'scope':'Unbound static source only. All old defects persist; no functional rig approval.'}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps(result))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
