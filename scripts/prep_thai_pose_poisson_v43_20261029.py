"""Save/reopen a pose-corrective SNAPSHOT, not a complete animated character."""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
I=ROOT/'work/probe_thai_pose_poisson_v43_20261029/pose_poisson_candidate_v43.npz'
OUT=ROOT/'reports/CHARACTER_THAI_POSE_POISSON_V43_20261029.json'
F=ROOT/'reports/thai_pose_poisson_v43_20261029';STATUS=ROOT/'work/v43_pose_poisson_status_20261029.json'
ATTR='V43_Pose_Offset_ObjectSpace_Snapshot'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p) as z:return {k:z[k].copy() for k in z.files}
try:
    assert I.exists() and not OUT.exists() and not F.exists()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_POISSON_V43_STAGE_20261029.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working']) and sha(stage['working'])==stage['workingSha256']
    u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
    assert u['action_signatures']()==stage['actionSignatures']
    assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
    base=load(Path(stage['actualSourceArchive']));trial=load(I)
    assert str(trial['sourceBodyBindSHA256'])==stage['actualSourceArchiveSha256']
    P=base['actualRestWorld'];T=base['actualTriangles'];W=base['actualWeights55'];R=base['actualBoneRest55'];names=base['actualNames55'].tolist()
    assert np.array_equal(trial['restWorldCandidate'],P) and np.array_equal(trial['trianglesCandidate'],T) and np.array_equal(trial['weights55Candidate'],W)
    assert np.array_equal(base['actualBodyWorld'],np.eye(4)), 'World offsets require explicit conversion for nonidentity BodyWorld'
    editable=trial['editableVertexIndices'].astype(int);outside=np.ones(len(P),bool);outside[editable]=False
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
    source=bpy.data.objects[stage['sourceBody']];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    body=source.copy();body.data=source.data.copy();body.name='V43_Pose_Poisson_SNAPSHOT_Idle101_Corrected'
    body.data.name='V43_V40_Exact_Bind_With_Pose_Offset_Attribute';scene.collection.objects.link(body)
    body.hide_render=False;body.hide_set(False,view_layer=layer)
    for name in [stage['sourceBody'],stage['diagnosticBodyToHide']]:
        obj=bpy.data.objects[name];obj.hide_render=True;obj.hide_set(True,view_layer=layer)
    assert len(body.modifiers)==1 and body.modifiers[0].type=='ARMATURE'
    first=body.modifiers[0];assert first.object==rig and not first.use_deform_preserve_volume
    attr=body.data.attributes.new(name=ATTR,type='FLOAT_VECTOR',domain='POINT')
    group=bpy.data.node_groups.new('V43_SNAPSHOT_Add_ObjectSpace_PoseOffset','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    inp=group.nodes.new('NodeGroupInput');out=group.nodes.new('NodeGroupOutput')
    named=group.nodes.new('GeometryNodeInputNamedAttribute');named.data_type='FLOAT_VECTOR';named.inputs['Name'].default_value=ATTR
    position=group.nodes.new('GeometryNodeSetPosition')
    group.links.new(inp.outputs['Geometry'],position.inputs['Geometry'])
    group.links.new(named.outputs['Attribute'],position.inputs['Offset'])
    group.links.new(position.outputs['Geometry'],out.inputs['Geometry'])
    corrective=body.modifiers.new('V43_POSE_OFFSET_SNAPSHOT_NOT_CONTINUOUS_ANIMATION','NODES');corrective.node_group=group
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
            for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    def offset(label,branch):
        delta=np.asarray(trial[label+'_'+branch+'DeltaQ'],dtype=np.float32)
        assert delta.shape==P.shape and np.isfinite(delta).all() and np.array_equal(delta[outside],np.zeros_like(delta[outside]))
        body.data.attributes[ATTR].data.foreach_set('vector',delta.reshape(-1));body.data.update();body.update_tag();layer.update()
        return delta
    choose('Idle',101);offset('Idle_101','corrected')
    body['PREP_snapshot_only_not_continuous_animation']=True
    body['PREP_snapshot_clip']='Idle';body['PREP_snapshot_frame']=101;body['PREP_snapshot_branch']='corrected'
    body['PREP_pose_or_game_approved']=False;body['PREP_source_candidate_sha256']=sha(I)
    scene['PREP_role']='Single-pose corrective snapshot. Offset must change for each pose; not a full animation, runtime or GLB.'
    scene.frame_start=101;scene.frame_end=101
    library=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_POISSON_V43_SNAPSHOT_20261029.blend'
    assert not library.exists();F.mkdir()
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(library),compress=True)
    saved_sha=sha(library);bodyname=body.name;scenename=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
    body=bpy.data.objects[bodyname];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    first,corrective=body.modifiers;head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    arrays=h['_snapshot'](body.data)['arrays'];ww=h['_weights'](body.data,55)
    rr=np.array([np.array(native.data.bones[n].matrix_local,dtype=float) for n in names])
    assert np.array_equal(arrays['coordinates'],P) and np.array_equal(arrays['triangles'],T) and np.array_equal(ww,W) and np.array_equal(rr,R)
    archive={'actualRestWorld':arrays['coordinates'],'actualTriangles':arrays['triangles'],'actualWeights55':ww,
        'actualNames55':np.asarray(list(body.vertex_groups.keys())),'actualBoneRest55':rr,'actualBodyWorld':np.array(body.matrix_world,dtype=float),
        'editableVertexIndices':editable,'snapshotFrame':np.array(101),'snapshotBranch':np.array('corrected')}
    def points(obj):
        ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p)
        M=np.array(ev.matrix_world,dtype=float);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
    rows=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';row={'sample':label}
        for branch,arm in [('native',native),('corrected',rig)]:
            first.object=arm;corrective.show_viewport=False;corrective.show_render=False;body.update_tag();layer.update();qpre=points(body)
            assert np.array_equal(qpre,base[label+'_'+branch+'BodyQ'])
            delta=offset(label,branch);corrective.show_viewport=True;corrective.show_render=True;body.update_tag();layer.update();qpost=points(body)
            expected=trial[label+'_'+branch+'Qcandidate']
            error=float(np.linalg.norm(qpost-expected,axis=1).max());addition_error=float(np.linalg.norm(qpost-(qpre+delta),axis=1).max())
            assert error<2e-5 and addition_error<2e-5 and np.array_equal(qpost[outside],qpre[outside])
            archive[label+'_'+branch+'Qpre']=qpre;archive[label+'_'+branch+'Qpost']=qpost;archive[label+'_'+branch+'ActualOffset']=delta
            row[branch]={'CPUPostErrorMeters':error,'additionErrorMeters':addition_error,'exteriorDriftMeters':0.,'maximumCorrectionMeters':float(np.linalg.norm(qpost-qpre,axis=1).max())}
        hq=points(head);assert np.array_equal(hq,base[label+'_headQ']);archive[label+'_headQ']=hq
        rows.append(row);STATUS.write_text(json.dumps({'status':'sampling','sample':label}))
    ar=F/'actual_reopened_pose_snapshots_v43.npz';np.savez_compressed(ar,**archive)
    first.object=rig;corrective.show_viewport=True;corrective.show_render=True
    gray=bpy.data.materials.new('V43_QA_Gray_Not_Default_Outfit');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    body.data.materials[0]=gray
    for obj in scene.objects:
        if obj.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_')) or obj.get('V28_original_source_name','').split('.')[0]=='Shoes':obj.hide_render=True
    images=[]
    def render(clip,frame,view,direction,detail=False):
        choose(clip,frame);offset(f'{clip}_{frame}','corrected');camera=scene.camera
        camera.data.type='ORTHO';camera.data.ortho_scale=.65 if detail else 1.93
        target=Vector((0,0,1.25 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        path=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(path)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window):bpy.ops.render.render(write_still=True)
        images.append({'path':str(path),'sha256':sha(path),'diagnosticOnly':True,'sampleSpecificOffsetApplied':True})
    render('Idle',101,'gray_front',(0,-1,0));render('Idle',101,'axilla_front',(0,-1,0),True);render('Walk',19,'axilla_back',(0,1,0),True)
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    assert u['action_signatures']()==stage['actionSignatures']
    assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
    assert sha(stage['source'])==stage['sourceSha256'] and sha(library)==saved_sha
    result={'status':'pose-Poisson-SNAPSHOT-saved-reopened-no-continuous-animation-claim','library':str(library),'sha256':saved_sha,
        'scene':scenename,'bodyObject':bodyname,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'candidate':str(I),'candidateSha256':sha(I),'archive':str(ar),'archiveSha256':sha(ar),'images':images,'samples':rows,
        'sourceGeometry55WeightsRestActionsPreserved':True,'snapshotOnlyNotFullAnimation':True,'selectedSnapshot':'Idle101_corrected',
        'geometryNodesAfterArmatureAdditionVerified':True,'poseQualityApproved':False,'clothesApproved':False,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items() if k not in ['samples','images']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
