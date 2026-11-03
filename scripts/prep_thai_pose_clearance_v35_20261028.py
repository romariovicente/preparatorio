"""Pose-only arm clearance on copied rig; original mesh/rest/curves are exact.

This pilot adds three degrees of arm abduction through two pose constraints.
It is neither a complete outfit nor an animation/runtime export approval.
"""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_pose_clearance_v35_20261028';OUT=ROOT/'reports/CHARACTER_THAI_POSE_CLEARANCE_V35_20261028.json'
STATUS=ROOT/'work/v35_pose_clearance_status_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as f:return {k:f[k].copy()for k in f.files}
def rotation_y(angle):
    c=np.cos(angle);s=np.sin(angle);return np.array([[c,0,s],[0,1,0],[-s,0,c]])
try:
    assert not OUT.exists()and not F.exists()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_CLEARANCE_V35_STAGE_20261028.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working'])and not bpy.data.is_dirty and sha(stage['working'])==stage['workingSha256']
    utility=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));sig=utility['mesh_signature'];actions=utility['action_signatures'];h=utility['helpers']
    assert actions()==stage['actionSignatures']
    assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    base=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')
    live=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation/fresh_live_motion_samples_v32.npz')
    names=base['names55'].tolist();R=base['boneRest55'];A=base['armWorld'];inverseA=np.linalg.inv(A)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0];assert scene.name==stage['scene']
    native=bpy.data.objects['V28_Clinical_Standard_Rig'];sourcebody=bpy.data.objects['V32_Complete_Standard_Body_Prototype']
    rig=native.copy();rig.data=native.data.copy();rig.name='V35_Local_Pose_Clearance_Rig';rig.data.name='V35_Rest55_Exact_Copy'
    scene.collection.objects.link(rig);rig.hide_render=True;rig.hide_set(True,view_layer=layer)
    assert np.array_equal(np.array([np.array(rig.data.bones[n].matrix_local,dtype=float)for n in names]),R)
    assert np.max(np.abs(np.array(rig.matrix_world,dtype=float)-A))<1e-7
    body=sourcebody.copy();body.data=sourcebody.data.copy();body.name='V35_Complete_Body_Pose_Arm_Clearance';body.data.name='V35_Body_Bind_Exact_V32_Copy'
    scene.collection.objects.link(body);body.hide_render=False;body.hide_set(False,view_layer=layer)
    sourcebody.hide_render=True;sourcebody.hide_set(True,view_layer=layer)
    modifiers=[m for m in body.modifiers if m.type=='ARMATURE'];assert len(modifiers)==1;modifiers[0].object=rig
    assert sig(body)==stage['meshSignatures'][sourcebody.name]
    # A is uniform-scaled; the controls store delta rotation in armature axes.
    U,_,VT=np.linalg.svd(A[:3,:3]);RA=U@VT;controls=[];chains={}
    for side,sign in [('Left',1),('Right',-1)]:
        delta_pose=RA.T@rotation_y(np.deg2rad(-sign*3.0))@RA
        control=bpy.data.objects.new('V35_'+side+'_Arm_Abduction_3deg_Control',None);scene.collection.objects.link(control)
        control.matrix_world=Matrix(delta_pose).to_4x4();control.empty_display_type='PLAIN_AXES';control.empty_display_size=.03
        control.hide_render=True;control.hide_set(True,view_layer=layer)
        control['PREP_rotation_is_literal_armature_space_offset']=True;controls.append(control.name)
        bone=rig.pose.bones['mixamorig:'+side+'Arm'];constraint=bone.constraints.new('COPY_ROTATION')
        assert 'BEFORE'in [i.identifier for i in constraint.bl_rna.properties['mix_mode'].enum_items]
        constraint.name='V35_'+side+'_Arm_3deg_Additive_Clearance';constraint.target=control
        constraint.owner_space='POSE';constraint.target_space='WORLD';constraint.mix_mode='BEFORE';constraint.influence=1
        chains[side]=[names.index(b.name)for b in [rig.data.bones[bone.name],*rig.data.bones[bone.name].children_recursive]]
    allarm=sorted(set(chains['Left']+chains['Right']));outside=[j for j in range(55)if j not in allarm]
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.data.pose_position='POSE';arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
            for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();p=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    # Verify constraint semantics before saving any candidate library.
    choose('Idle',1)
    ev=rig.evaluated_get(layer.depsgraph);P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names])
    predicted=live['Idle_1_pose55'].copy()
    for side,sign in [('Left',1),('Right',-1)]:
        indices=chains[side];pivot=(A@predicted[names.index('mixamorig:'+side+'Arm')])[:3,3]
        rw=rotation_y(np.deg2rad(-sign*3));C=np.eye(4);C[:3,:3]=rw;C[:3,3]=pivot-rw@pivot
        predicted[indices]=inverseA@C@A@predicted[indices]
    initial_pose_error=float(np.max(np.abs(P-predicted)));assert initial_pose_error<1e-4,('Unexpected constraint semantics',initial_pose_error)
    body['PREP_pose_clearance_3deg_pilot']=True;body['PREP_bind_mesh_weights_unchanged']=True;body['PREP_full_appearance_approved']=False
    rig['PREP_native_rest_and_shared_action_curves_exact']=True;rig['PREP_glTF_requires_baked_pose_validation']=True
    scene['PREP_role']='Pose-only three-degree arm clearance pilot; original clothes still unfinished'
    scene['PREP_appearance_approved']=False
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_CLEARANCE_V35_20261028.blend';assert not path.exists();F.mkdir()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    library_sha=sha(path);scenename=scene.name;rigname=rig.name;bodyname=body.name
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
    native=bpy.data.objects['V28_Clinical_Standard_Rig'];rig=bpy.data.objects[rigname];body=bpy.data.objects[bodyname]
    head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved'];skirt=bpy.data.objects['V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape']
    archive={'restP':base['restWorld'],'restWorld':base['restWorld'],'triangles':base['triangles'],'weights55':base['weights55'],'names55':np.array(names),'boneRest55':R,'armWorld':A,
        'objectWorld':base['objectWorld'],'leftArmChainIndices':np.array(chains['Left']),'rightArmChainIndices':np.array(chains['Right']),
        'skirtTriangles':h['_snapshot'](skirt.data)['arrays']['triangles'],'abductionDegrees':np.array(3.)}
    rows=[];images=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';q,M=points(body);hq,_=points(head);sq,_=points(skirt);ev=rig.evaluated_get(layer.depsgraph)
        P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names]);Aw=np.array(ev.matrix_world,dtype=float)
        deform=Aw@P@np.linalg.inv(R)@np.linalg.inv(Aw)@M;blend=np.einsum('vj,jab->vab',base['weights55'],deform)
        expected=np.einsum('vab,vb->va',blend,np.c_[base['restWorld'],np.ones(len(q))])[:,:3]
        lbs=float(np.linalg.norm(expected-q,axis=1).max());identity=float(np.linalg.norm(hq-live[label+'_headQ'],axis=1).max())
        unaffected=float(np.max(np.abs(P[outside]-live[label+'_pose55'][outside])));assert lbs<2e-5 and identity<2e-5 and unaffected<1e-5
        drift=np.linalg.norm(q-live[label+'_bodyQ'],axis=1)
        rows.append({'clip':clip,'frame':frame,'maximumLBSPositionErrorMeters':lbs,'headIdentityDriftMeters':identity,
            'outsideArmChainsPoseMatrixMaximumError':unaffected,'maximumBodyDisplacementMeters':float(drift.max()),
            'bodyMinimumZ':float(q[:,2].min()),'fullBodyHeadHeight':float(max(q[:,2].max(),hq[:,2].max())-min(q[:,2].min(),hq[:,2].min()))})
        archive[label+'_bodyQ']=q;archive[label+'_headQ']=hq;archive[label+'_skirtQ']=sq;archive[label+'_pose55']=P;archive[label+'_armWorld']=Aw;archive[label+'_bodyWorld']=M
    ar=F/'fresh_live_motion_samples_v35.npz';np.savez_compressed(ar,**archive)
    gray=bpy.data.materials.new('V35_Diagnostic_Gray_Not_Final_Clothes');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    mat=body.data.materials[0];outfits=[o for o in scene.objects if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_'))or o.get('V28_original_source_name','').split('.')[0]=='Shoes']
    visibility={o.name:o.hide_render for o in outfits}
    def render(clip,frame,view,direction,diagnostic=True,detail=False):
        choose(clip,frame)
        for o in outfits:o.hide_render=True if diagnostic else visibility[o.name]
        body.data.materials[0]=gray if diagnostic else mat
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.0 if detail else 1.93
        target=Vector((0,0,.95 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        output=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(output);STATUS.write_text(json.dumps({'status':'rendering','path':str(output)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(output),'sha256':sha(output),'clip':clip,'frame':frame,'view':view,'grayDiagnosticOnly':diagnostic})
    for view,direction in [('gray_front',(0,-1,0)),('gray_side',(-1,0,0)),('gray_back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',1,'hand_hip_detail',(0,-1,0),True,True);render('Idle',1,'dressed_front',(0,-1,0),False)
    for frame in [1,7,13,19]:render('Walk',frame,'gray_front',(0,-1,0))
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    assert actions()==stage['actionSignatures'];assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    assert sig(bpy.data.objects[bodyname])==stage['meshSignatures']['V32_Complete_Standard_Body_Prototype']
    assert sha(stage['source'])==stage['sourceSha256']and sha(stage['working'])==stage['workingSha256']and sha(path)==library_sha
    result={'status':'pose-only-three-degree-arm-candidate-saved-reopened-awaiting-QA','library':str(path),'sha256':library_sha,'scene':scenename,
        'newRig':rigname,'newBody':bodyname,'controls':controls,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'archive':str(ar),'archiveSha256':sha(ar),'abductionDegrees':3,'initialConstraintVsWorldRotationMatrixError':initial_pose_error,
        'allSourceMeshDataExact':True,'newBodyBindMeshWeightsExactAgainstV32':True,'sourceActionCurvesExact':True,'nativeRestPreserved':True,
        'samples':rows,'images':images,'appearanceApproved':False,'collisionClearanceApproved':False,'wholeAnimationApproved':False,
        'originalOutfitStillUnfinished':True,'coatAndSchoolShirtOptional':True,'constraintsBakedForExport':False,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items()if k not in ['samples','images']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
