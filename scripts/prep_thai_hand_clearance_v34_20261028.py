"""Apply a measured, local bind-surface correction in an isolated Blender copy.

Keep V32, Thai identity, native bone rest, weights, all 2200 native curves and
clothing sources unchanged. Fine skin, clothes and whole animation stay pending.
"""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
I=ROOT/'work/qa_thai_hand_clearance_v34_20261028/hand_clearance_candidate_v34.npz'
F=ROOT/'reports/thai_hand_clearance_v34_20261028';OUT=ROOT/'reports/CHARACTER_THAI_HAND_CLEARANCE_V34_20261028.json'
STATUS=ROOT/'work/v34_hand_clearance_status_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as f:return {k:f[k].copy()for k in f.files}
def action_signatures():
    rows={}
    for clip in ['Idle.002','Walk.002','Dance.002','Interact.002']:
        curves=[]
        for l in bpy.data.actions[clip].layers:
            for strip in l.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        p=[[ *k.co,*k.handle_left,*k.handle_right,k.interpolation,k.easing,k.handle_left_type,k.handle_right_type]for k in fc.keyframe_points]
                        curves.append([fc.data_path,fc.array_index,fc.extrapolation,p])
        assert curves
        rows[clip]={'curveCount':len(curves),'sha256':hashlib.sha256(json.dumps(curves,separators=(',',':')).encode()).hexdigest()}
    return rows
try:
    assert I.exists() and not F.exists() and not OUT.exists()
    s=json.loads((ROOT/'reports/CHARACTER_THAI_HAND_CLEARANCE_V34_STAGE_20261028.json').read_text())
    assert Path(bpy.data.filepath)==Path(s['working']) and not bpy.data.is_dirty and sha(s['working'])==s['workingSha256']
    assert action_signatures()==s['actionSignatures']
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
    assert scene.name==s['scene']
    base=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz');payload=load(I)
    P=payload['restWorldCandidate'];assert P.shape==base['restWorld'].shape and np.isfinite(P).all()
    changed=np.asarray(payload['changedVertexIndices'],dtype=np.int32);outside=np.ones(len(P),dtype=bool);outside[changed]=False
    assert np.array_equal(P[outside],base['restWorld'][outside]),'Unedited vertices must remain bit-exact'
    assert np.array_equal(payload['triangles'],base['triangles']) and np.array_equal(payload['weights55'],base['weights55'])
    assert str(payload['sourceBodyBindSHA256'])==sha(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    def sig(o):
        return {'arrays':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](o.data)['arrays'].items()},
            'groups':list(o.vertex_groups.keys()),'weights':hashlib.sha256(h['_weights'](o.data,len(o.vertex_groups)).tobytes()).hexdigest()}
    assert all(sig(bpy.data.objects[n])==value for n,value in s['meshSignatures'].items())
    names=base['names55'].tolist();R=base['boneRest55'];arm=bpy.data.objects['V28_Clinical_Standard_Rig']
    assert np.array_equal(np.array([np.array(arm.data.bones[n].matrix_local,dtype=float)for n in names]),R)
    old=bpy.data.objects['V32_Complete_Standard_Body_Prototype'];obj=old.copy();obj.data=old.data.copy()
    obj.name='V34_Complete_Standard_Body_Local_Arm_Clearance';obj.data.name='V34_Local_Arm_Clearance_Surface';scene.collection.objects.link(obj)
    obj.data.vertices.foreach_set('co',P.astype(np.float32).reshape(-1));obj.data.update()
    obj.hide_render=False;obj.hide_set(False,view_layer=layer);old.hide_render=True;old.hide_set(True,view_layer=layer)
    obj['PREP_local_arm_clearance_candidate']=True;obj['PREP_full_appearance_approved']=False;obj['PREP_source_body_preserved']=old.name
    actual=h['_snapshot'](obj.data)['arrays'];W=h['_weights'](obj.data,55)
    assert np.array_equal(W,base['weights55']) and np.array_equal(actual['triangles'],base['triangles'])
    scene['PREP_role']='Local arm/hand clearance candidate on complete V32; clothes still rejected'
    scene['PREP_appearance_approved']=False
    def choose(clip,frame):
        arm.data.pose_position='POSE';a=bpy.data.actions[clip+'.002'];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAND_CLEARANCE_V34_20261028.blend';assert not path.exists();F.mkdir()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    library_sha=sha(path);objname=obj.name;scenename=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects['V28_Clinical_Standard_Rig'];obj=bpy.data.objects[objname];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    skirt=bpy.data.objects['V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape'];old=bpy.data.objects['V32_Complete_Standard_Body_Prototype']
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v)
        M=np.array(ev.matrix_world,dtype=float);q=v.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    live=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation/fresh_live_motion_samples_v32.npz')
    archive={'restP':actual['coordinates'],'triangles':actual['triangles'],'weights55':W,'names55':np.array(names),'boneRest55':R,
        'armWorld':base['armWorld'],'objectWorld':base['objectWorld'],'skirtTriangles':h['_snapshot'](skirt.data)['arrays']['triangles']}
    for k,v in payload.items():archive['payload_'+k]=v
    rows=[];images=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';q,M=points(obj);hq,_=points(head);sq,_=points(skirt);ev=arm.evaluated_get(layer.depsgraph)
        P55=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names]);A=np.array(ev.matrix_world,dtype=float)
        D=A@P55@np.linalg.inv(R)@np.linalg.inv(A)@M;blend=np.einsum('vj,jab->vab',W,D)
        expected=np.einsum('vab,vb->va',blend,np.c_[archive['restP'],np.ones(len(q))])[:,:3]
        lbs=float(np.linalg.norm(expected-q,axis=1).max());identity=float(np.linalg.norm(hq-live[label+'_headQ'],axis=1).max());assert lbs<2e-5 and identity<2e-5
        drift=np.linalg.norm(q-live[label+'_bodyQ'],axis=1)
        archive[label+'_bodyQ']=q;archive[label+'_headQ']=hq;archive[label+'_skirtQ']=sq;archive[label+'_pose55']=P55;archive[label+'_armWorld']=A;archive[label+'_bodyWorld']=M
        outside_drift=float(drift[outside].max());assert outside_drift<2e-6
        row={'clip':clip,'frame':frame,'maximumLBSPositionErrorMeters':lbs,'headIdentityDriftMeters':identity,'maximumBodySurfaceDisplacementMeters':float(drift.max()),
            'maximumUneditedSurfaceDriftMeters':outside_drift,
            'bodyMinimumZ':float(q[:,2].min()),'fullBodyHeadHeight':float(max(q[:,2].max(),hq[:,2].max())-min(q[:,2].min(),hq[:,2].min()))};rows.append(row)
    archive_path=F/'reopened_body_and_cloth_motion_v34.npz';np.savez_compressed(archive_path,**archive)
    gray=bpy.data.materials.new('V34_QA_Gray_Only_Not_Final_Outfit');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    original_mat=obj.data.materials[0]
    outfits=[o for o in scene.objects if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_'))or o.get('V28_original_source_name','').split('.')[0]=='Shoes']
    visibility={o.name:o.hide_render for o in outfits}
    def render(clip,frame,view,direction,diagnostic=True,detail=False):
        choose(clip,frame)
        for o in outfits:o.hide_render=True if diagnostic else visibility[o.name]
        obj.data.materials[0]=gray if diagnostic else original_mat
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.00 if detail else 1.93
        target=Vector((0,0,.95 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        imagepath=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(imagepath);STATUS.write_text(json.dumps({'status':'rendering','path':str(imagepath)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(imagepath),'sha256':sha(imagepath),'clip':clip,'frame':frame,'view':view,'grayDiagnosticOnly':diagnostic})
    for view,direction in [('gray_front',(0,-1,0)),('gray_side',(-1,0,0)),('gray_back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',1,'hand_hip_detail',(0,-1,0),True,True)
    render('Idle',1,'dressed_front',(0,-1,0),False)
    for frame in [1,7,13,19]:render('Walk',frame,'gray_front',(0,-1,0))
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    assert action_signatures()==s['actionSignatures']
    arm=bpy.data.objects['V28_Clinical_Standard_Rig']
    assert np.array_equal(np.array([np.array(arm.data.bones[n].matrix_local,dtype=float)for n in names]),R)
    assert all(sig(bpy.data.objects[n])==value for n,value in s['meshSignatures'].items())
    assert sha(s['source'])==s['sourceSha256'] and sha(s['working'])==s['workingSha256'] and sha(path)==library_sha
    result={'status':'local-arm-surface-candidate-saved-and-reopened-awaiting-independent-QA','library':str(path),'sha256':library_sha,
        'scene':scenename,'newBodyObject':objname,'checkpoint':s['checkpoint'],'checkpointSha256':s['checkpointSha256'],
        'payload':str(I),'payloadSha256':sha(I),'archive':str(archive_path),'archiveSha256':sha(archive_path),
        'allPreservedMeshesExact':True,'nativeActionCurvesExact':True,'nativeActionCurveCounts':s['actionSignatures'],
        'nativeRestChanged':False,'weights55AndTopologyExactAgainstV32':True,'samples':rows,'images':images,
        'bodyAppearanceApproved':False,'wholeAnimationApproved':False,'originalClothesApproved':False,'clinicalOutfitsOptional':True,
        'GLBExportedOrReimported':False,'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,
        'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items()if k not in ['samples','images','nativeActionCurveCounts']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
