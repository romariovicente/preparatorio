"""Three frozen local CorrectiveSmooth trials in the existing Blender session.

Source P/T/W55/rest/actions are preserved. Post-modifier Q is not claimed to be
LBS; pre/post and native/3degree branches are exported independently for QA.
"""
import bpy,bmesh,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_axilla_corrective_v37_20261028'
OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_CORRECTIVE_V37_20261028.json';STATUS=ROOT/'work/v37_corrective_status_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as f:return {k:f[k].copy()for k in f.files}
def smoothstep(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def relative_surface(a,b,T,ids):
    t=T[ids];u=a[t[:,1]]-a[t[:,0]];v=a[t[:,2]]-a[t[:,0]];cu=b[t[:,1]]-b[t[:,0]];cv=b[t[:,2]]-b[t[:,0]]
    n=np.cross(u,v);cn=np.cross(cu,cv);area=np.linalg.norm(n,axis=1);ca=np.linalg.norm(cn,axis=1)
    ul=np.linalg.norm(u,axis=1);un=u/ul[:,None];vp=(v*un).sum(1);perp=np.sqrt(np.maximum((v*v).sum(1)-vp*vp,1e-30))
    j0=cu/ul[:,None];j1=(cv-cu*(vp/ul)[:,None])/perp[:,None];sv=np.linalg.svd(np.stack([j0,j1],axis=2),compute_uv=False)
    ratio=ca/area;dot=(n*cn).sum(1)/np.maximum(area*ca,1e-30)
    bad=(ratio<.8)|(ratio>1.25)|(sv.min(1)<.85)|(sv.max(1)>1.15)|(dot<np.cos(np.deg2rad(20)))
    return {'areaMin':float(ratio.min()),'areaMax':float(ratio.max()),'singularMin':float(sv.min()),'singularMax':float(sv.max()),
        'normalDotMin':float(dot.min()),'badFaces':int(bad.sum()),'pass':bool(not bad.any())}
try:
    assert not F.exists()and not OUT.exists()
    contract=ROOT/'work/qa_thai_axilla_corrective_v37_20261028/qa_contract.md'
    assert sha(contract)=='916a64fc22c63b3c290a57d1df473670d7defe210e24d1e86a9caf09fff145d0'
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_V37_STAGE_20261028.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working'])and not bpy.data.is_dirty and sha(stage['working'])==stage['workingSha256']
    u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));sig=u['mesh_signature'];h=u['helpers'];actions=u['action_signatures']
    assert actions()==stage['actionSignatures'];assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    base=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')
    native_live=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation/fresh_live_motion_samples_v32.npz')
    pose_live=load(ROOT/'reports/thai_pose_clearance_v35_20261028/fresh_live_motion_samples_v35.npz')
    region_path=ROOT/'work/qa_thai_axilla_weights_v36_20261028/axilla_weights_candidate_v36.npz';region=load(region_path)
    assert not bool(region['accepted'])and np.array_equal(region['triangles'],base['triangles'])and np.array_equal(region['restWorld'],base['restWorld'])
    distance=region['geodesicDistanceRest'];mask=np.where(np.isfinite(distance),1-smoothstep((distance-.008)/.012),0).astype(np.float32)
    mask[distance>=.02]=0;ids=np.flatnonzero(mask>0);T=base['triangles'];W=base['weights55'];names=base['names55'].tolist();R=base['boneRest55']
    patch_vertices=np.zeros(len(mask),bool);patch_vertices[np.unique(T[np.any(mask[T]>0,axis=1)])]=True
    patch=np.flatnonzero(np.any(patch_vertices[T],axis=1));arm_affected=np.zeros(len(mask),bool)
    states=[('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]
    for clip,frame in states:
        label=f'{clip}_{frame}';arm_affected|=np.linalg.norm(pose_live[label+'_bodyQ']-native_live[label+'_bodyQ'],axis=1)>1e-6
    union=np.flatnonzero(np.any((arm_affected|patch_vertices)[T],axis=1))
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
    native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']];source=bpy.data.objects[stage['sourceBody']]
    body=source.copy();body.data=source.data.copy();body.name='V37_Local_Axilla_Corrective_Study';body.data.name='V37_V32_Exact_Bind_With_Corrective_Mask'
    scene.collection.objects.link(body);body.hide_render=False;body.hide_set(False,view_layer=layer);source.hide_render=True;source.hide_set(True,view_layer=layer)
    assert len(body.vertex_groups)==55
    group=body.vertex_groups.new(name='V37_Axilla_Corrective_Mask');assert group.index==55 and rig.data.bones.get(group.name)is None
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();bm.verts.index_update();dw=bm.verts.layers.deform.verify()
    for i in ids:bm.verts[int(i)][dw][55]=float(mask[i])
    bm.to_mesh(body.data);bm.free();body.data.update()
    a=h['_snapshot'](body.data)['arrays'];weights=h['_weights'](body.data,56)
    assert np.array_equal(a['coordinates'],base['restWorld'])and np.array_equal(a['triangles'],T)and np.array_equal(weights[:,:55],W)
    armature=next(m for m in body.modifiers if m.type=='ARMATURE')
    corrective=body.modifiers.new('V37_Local_Axilla_Corrective_Smooth','CORRECTIVE_SMOOTH')
    corrective.rest_source='ORCO';corrective.smooth_type='LENGTH_WEIGHTED';corrective.factor=.5;corrective.iterations=5
    corrective.scale=1;corrective.vertex_group=group.name;corrective.use_only_smooth=False;corrective.use_pin_boundary=True
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.data.pose_position='POSE';arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
            for tr in arm.animation_data.nla_tracks:tr.mute=True
        scene.frame_set(frame);layer.update()
    def points():
        ev=body.evaluated_get(layer.depsgraph);m=ev.to_mesh();p=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    def branch(arm):armature.object=arm;body.update_tag();layer.update()
    choose('Idle',1);probe_file=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_CORRECTIVE_V37_PROBE_20261028.blend';assert not probe_file.exists()
    body['PREP_unapproved_local_corrective_study']=True;scene['PREP_role']='Local corrective surface study; no source weight repair adopted; not a playable scene'
    F.mkdir()
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(probe_file),compress=True)
    archive={'restWorld':base['restWorld'],'triangles':T,'weights55':W,'names55':base['names55'],'boneRest55':R,
        'mask':mask,'geodesicDistanceRest':distance,'seedFaces':region['seedFaces'],'seedVertexIndices':region['seedVertexIndices'],
        'patchFaceIndices':patch,'relativeComparisonFaceIndices':union,'parameterValues':np.array([.25,.5,.75]),'iterations':np.array(5),
        'sourceROIFileSHA256':np.array(sha(region_path)),'contractSHA256':np.array(sha(contract))}
    for clip,frame in states:
        choose(clip,frame);label=f'{clip}_{frame}';corrective.show_viewport=False;corrective.show_render=False
        for tag,arm in [('native',native),('corrected',rig)]:
            branch(arm);q,M=points();ev=arm.evaluated_get(layer.depsgraph);P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names]);A=np.array(ev.matrix_world,dtype=float)
            D=A@P@np.linalg.inv(R)@np.linalg.inv(A)@M;blend=np.einsum('vj,jab->vab',W,D)
            expected=np.einsum('vab,vb->va',blend,np.c_[base['restWorld'],np.ones(len(mask))])[:,:3]
            error=float(np.linalg.norm(q-expected,axis=1).max());assert error<2e-5
            archive[label+'_'+tag+'Qpre']=q;archive[label+'_'+tag+'Pose55']=P;archive[label+'_'+tag+'ArmWorld']=A;archive[label+'_'+tag+'BodyWorld']=M
            archive[label+'_'+tag+'PreLBSMaxError']=np.array(error)
    corrective.show_viewport=True;corrective.show_render=True;rest_norm=np.cross(base['restWorld'][T[patch,1]]-base['restWorld'][T[patch,0]],base['restWorld'][T[patch,2]]-base['restWorld'][T[patch,0]])
    rest_area=np.linalg.norm(rest_norm,axis=1);rows=[]
    for tag,factor in [('f025',.25),('f050',.5),('f075',.75)]:
        corrective.factor=factor;per_state=[]
        for clip,frame in states:
            choose(clip,frame);label=f'{clip}_{frame}';qs={};state={'sample':label}
            for which,arm in [('native',native),('corrected',rig)]:
                branch(arm);q,M=points();pre=archive[label+'_'+which+'Qpre'];delta=np.linalg.norm(q-pre,axis=1);qs[which]=q
                archive[tag+'_'+label+'_'+which+'Qpost']=q
                nn=np.cross(q[T[patch,1]]-q[T[patch,0]],q[T[patch,2]]-q[T[patch,0]]);area=np.linalg.norm(nn,axis=1)
                P=archive[label+'_'+which+'Pose55'];A=archive[label+'_'+which+'ArmWorld'];D=A@P@np.linalg.inv(R)@np.linalg.inv(A)@M
                J=np.einsum('fj,jab->fab',W[T[patch]].mean(1),D[:,:3,:3])
                refs=np.linalg.det(J)[:,None]*np.linalg.solve(J.transpose(0,2,1),rest_norm[:,:,None])[:,:,0]
                dot=(nn*refs).sum(1)/np.maximum(np.linalg.norm(nn,axis=1)*np.linalg.norm(refs,axis=1),1e-30)
                ratio=area/np.maximum(rest_area,1e-30);absolute_bad=(ratio<.05)|(ratio>4)|(dot<=0)|(area<1e-14)
                state[which]={'maximumCorrectionMeters':float(delta.max()),'outsideMaskMaximumMeters':float(delta[mask==0].max()),
                    'minimumAreaOverRest':float(ratio.min()),'maximumAreaOverRest':float(ratio.max()),'minimumTransportedNormalDot':float(dot.min()),
                    'absoluteBadFaces':int(absolute_bad.sum()),'absolutePreliminaryPass':bool(not absolute_bad.any())}
            state['nativeTo3Degree']=relative_surface(qs['native'],qs['corrected'],T,union);per_state.append(state)
            STATUS.write_text(json.dumps({'status':'probing','parameter':tag,'sample':label}))
        score=sum(s['nativeTo3Degree']['badFaces']+s['native']['absoluteBadFaces']+s['corrected']['absoluteBadFaces']for s in per_state)
        preliminary=all(s['nativeTo3Degree']['pass']and all(s[k]['absolutePreliminaryPass']and s[k]['maximumCorrectionMeters']<=.003001 and s[k]['outsideMaskMaximumMeters']<1e-6 for k in ['native','corrected'])for s in per_state)
        rows.append({'tag':tag,'factor':factor,'iterations':5,'scorePreliminaryFailures':score,'preliminaryPassExcludingIndependentFanAndCollision':preliminary,'states':per_state})
    selected=min(rows,key=lambda row:(not row['preliminaryPassExcludingIndependentFanAndCollision'],row['scorePreliminaryFailures'],row['factor']))
    corrective.factor=selected['factor'];choose('Idle',1);branch(rig)
    body['PREP_selected_factor']=selected['factor'];body['PREP_accepted_for_surface_or_runtime']=False
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(probe_file),compress=True)
    saved_sha=sha(probe_file);bodyname=body.name;scenename=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(probe_file),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
    native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']];body=bpy.data.objects[bodyname]
    armature=next(m for m in body.modifiers if m.type=='ARMATURE');corrective=next(m for m in body.modifiers if m.type=='CORRECTIVE_SMOOTH')
    reopen_errors=[]
    for clip,frame in states:
        choose(clip,frame);label=f'{clip}_{frame}'
        for which,arm in [('native',native),('corrected',rig)]:
            branch(arm);q,_=points();err=float(np.linalg.norm(q-archive[selected['tag']+'_'+label+'_'+which+'Qpost'],axis=1).max());assert err<2e-5
            archive['reopened_'+label+'_'+which+'Qpost']=q;reopen_errors.append(err)
    ar=F/'actual_corrective_trials_v37.npz';np.savez_compressed(ar,**archive)
    bpy.ops.wm.open_mainfile(filepath=str(probe_file),load_ui=False,use_scripts=False)
    assert actions()==stage['actionSignatures'];assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    assert sha(stage['source'])==stage['sourceSha256']and sha(stage['working'])==stage['workingSha256']and sha(probe_file)==saved_sha
    result={'status':'three-frozen-corrective-surface-trials-saved-reopened-awaiting-independent-QA','library':str(probe_file),'sha256':saved_sha,
        'scene':scenename,'bodyObject':bodyname,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'archive':str(ar),'archiveSha256':sha(ar),'contract':str(contract),'contractSha256':sha(contract),
        'maskVertices':len(ids),'patchFaces':len(patch),'relativeFaces':len(union),'parameters':rows,'selectedTag':selected['tag'],
        'maximumReopenedPostPositionDifferenceMeters':max(reopen_errors),'source55BoneWeightsAndBindGeometryExact':True,
        'sourceActionsAndRestUnchanged':True,'postCorrectiveClaimedAsLBS':False,'V36WeightsAdopted':False,
        'newMaskGroupIsMetadataNotBoneWeight':True,'appearanceApproved':False,'wholeAnimationApproved':False,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({'report':str(OUT),'library':str(probe_file),'sha256':saved_sha,'selected':selected['tag'],
        'trials':[{k:r[k]for k in ['tag','scorePreliminaryFailures','preliminaryPassExcludingIndependentFanAndCollision']}for r in rows]}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
