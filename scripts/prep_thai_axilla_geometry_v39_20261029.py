"""Integrate a bounded Rest-geometry study on a copy, then save/reopen and sample.

This is not approval of poses, clothes, GLB or the playable scene.
"""
import bpy, json, hashlib, runpy, traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'work/probe_thai_axilla_geometry_v39_20261029/geometry_candidate_v39.npz'
F=ROOT/'reports/thai_axilla_geometry_v39_20261029'
OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_GEOMETRY_V39_20261029.json'
STATUS=ROOT/'work/v39_geometry_status_20261029.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p) as z:return {k:z[k].copy() for k in z.files}
try:
    assert PAYLOAD.exists() and not F.exists() and not OUT.exists()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_GEOMETRY_V39_STAGE_20261029.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working']) and not bpy.data.is_dirty
    assert sha(stage['working'])==stage['workingSha256']
    util=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
    sig=util['mesh_signature'];actions=util['action_signatures'];h=util['helpers']
    assert actions()==stage['actionSignatures']
    assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    base_path=ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz'
    base=load(base_path);trial=load(PAYLOAD)
    assert str(trial['sourceBodyBindSHA256'])==sha(base_path)
    P=trial['restWorldCandidate'];T=trial['trianglesCandidate'];W=trial['weights55Candidate']
    assert P.shape==base['restWorld'].shape and np.isfinite(P).all()
    assert np.array_equal(T,base['triangles']) and np.array_equal(W,base['weights55'])
    assert np.array_equal(trial['sourceVertexIds'],np.arange(len(P)))
    assert np.array_equal(trial['names55'],base['names55']) and np.array_equal(trial['boneRest55'],base['boneRest55'])
    region=load(ROOT/'work/qa_thai_axilla_weights_v36_20261028/axilla_weights_candidate_v36.npz')
    distance=region['geodesicDistanceRest'];outside=~(distance<.018)
    assert np.array_equal(P[outside],base['restWorld'][outside])
    changed=np.flatnonzero(np.any(P!=base['restWorld'],axis=1))
    assert len(changed)>0 and np.max(np.linalg.norm(P-base['restWorld'],axis=1))<=.002001
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    scene=window.scene;layer=scene.view_layers[0]
    source=bpy.data.objects[stage['sourceBody']]
    native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    body=source.copy();body.data=source.data.copy()
    body.name='V39_Local_Axilla_Rest_Geometry_Study';body.data.name='V39_Source_Topology_Weights_Local_Rest_Repair'
    scene.collection.objects.link(body)
    body.data.vertices.foreach_set('co',np.asarray(P,dtype=np.float32).reshape(-1))
    body.data.update();body.hide_render=False;body.hide_set(False,view_layer=layer)
    assert [m.type for m in body.modifiers]==['ARMATURE']
    modifier=body.modifiers[0];assert modifier.object==rig
    for name in [stage['sourceBody'],'V37_Local_Axilla_Corrective_Study']:
        if name in bpy.data.objects:
            o=bpy.data.objects[name];o.hide_render=True;o.hide_set(True,view_layer=layer)
    actual=h['_snapshot'](body.data)['arrays']
    assert np.array_equal(actual['coordinates'],P) and np.array_equal(actual['triangles'],T)
    assert np.array_equal(h['_weights'](body.data,55),W)
    body['PREP_local_geometry_study']=True
    body['PREP_appearance_and_animation_approved']=False
    body['PREP_original_outfit_still_pending']=True
    body['PREP_source_payload_sha256']=sha(PAYLOAD)
    scene['PREP_role']='Local axilla Rest geometry study. Not the playable map; clothes and poses require separate QA.'
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.data.pose_position='POSE';arm.animation_data.action=action
            arm.animation_data.action_slot=action.slots[0]
            for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    library=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_GEOMETRY_V39_PROBE_20261029.blend'
    assert not library.exists();F.mkdir()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):
        bpy.ops.wm.save_as_mainfile(filepath=str(library),compress=True)
    saved_sha=sha(library);body_name=body.name;scene_name=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    scene=bpy.data.scenes[scene_name];window.scene=scene;layer=scene.view_layers[0]
    body=bpy.data.objects[body_name];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    modifier=body.modifiers[0];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    R=base['boneRest55'];names=base['names55'].tolist()
    before=load(ROOT/'reports/thai_pose_clearance_v35_20261028/fresh_live_motion_samples_v35.npz')
    old=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation/fresh_live_motion_samples_v32.npz')
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
        p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p)
        M=np.asarray(ev.matrix_world,dtype=float);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3]
        ev.to_mesh_clear();return q,M
    archive={k:trial[k] for k in ['restWorldCandidate','trianglesCandidate','weights55Candidate','sourceVertexIds','names55','boneRest55','sourceBodyBindSHA256']}
    archive.update(restWorldSource=base['restWorld'],changedVertexIndices=changed,geodesicDistanceRest=distance)
    rows=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';row={'sample':label}
        for tag,arm,baseline in [('native',native,old),('corrected',rig,before)]:
            modifier.object=arm;body.update_tag();layer.update();q,M=points(body)
            arm_ev=arm.evaluated_get(layer.depsgraph)
            poses=np.asarray([np.asarray(arm_ev.pose.bones[n].matrix,dtype=float) for n in names])
            A=np.asarray(arm_ev.matrix_world,dtype=float)
            D=A@poses@np.linalg.inv(R)@np.linalg.inv(A)@M
            cpu=np.einsum('vab,vb->va',np.einsum('vj,jab->vab',W,D),np.c_[P,np.ones(len(P))])[:,:3]
            error=float(np.linalg.norm(cpu-q,axis=1).max())
            assert error<2e-5
            exterior=float(np.linalg.norm(q[outside]-baseline[label+'_bodyQ'][outside],axis=1).max())
            assert exterior<2e-6
            archive[label+'_'+tag+'BodyQ']=q;archive[label+'_'+tag+'Pose55']=poses
            archive[label+'_'+tag+'ArmWorld']=A;archive[label+'_'+tag+'BodyWorld']=M
            row[tag]={'LBSMaxErrorMeters':error,'outsideChangeMeters':exterior,'minimumBodyZ':float(q[:,2].min())}
        hq,_=points(head);assert np.linalg.norm(hq-old[label+'_headQ'],axis=1).max()<2e-5
        archive[label+'_headQ']=hq;rows.append(row)
    ar=F/'saved_reopened_geometry_and_motion_v39.npz';np.savez_compressed(ar,**archive)
    images=[]
    gray=bpy.data.materials.new('V39_QA_Gray_Diagnostic_Not_Default_Outfit');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    body.data.materials[0]=gray
    for o in scene.objects:
        if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_')) or o.get('V28_original_source_name','').split('.')[0]=='Shoes':o.hide_render=True
    def render(clip,frame,view,direction,detail=False):
        choose(clip,frame);modifier.object=rig;body.update_tag();layer.update()
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.58 if detail else 1.93
        target=Vector((0,0,1.27 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        path=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(path)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(path),'sha256':sha(path),'diagnosticOnly':True})
    render('Idle',1,'gray_front',(0,-1,0))
    render('Idle',101,'axilla_front',(0,-1,0),True)
    render('Walk',19,'axilla_back',(0,1,0),True)
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    assert actions()==stage['actionSignatures']
    assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    assert sha(stage['source'])==stage['sourceSha256'] and sha(library)==saved_sha
    result={'status':'local-rest-geometry-study-saved-reopened-awaiting-independent-QA',
        'library':str(library),'sha256':saved_sha,'scene':scene_name,'bodyObject':body_name,
        'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'payload':str(PAYLOAD),'payloadSha256':sha(PAYLOAD),'archive':str(ar),'archiveSha256':sha(ar),
        'changedVertices':len(changed),'maximumRestChangeMeters':float(np.linalg.norm(P-base['restWorld'],axis=1).max()),
        'sourceTopologyAndWeightsExact':True,'sourceMeshesAndActionsPreserved':True,'samples':rows,'images':images,
        'appearanceApproved':False,'animationApproved':False,'originalOutfitStillPending':True,
        'runtimeChanged':False,'masterChanged':False,'GLBExportedOrReimported':False,
        'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items() if k not in ['samples','images']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
