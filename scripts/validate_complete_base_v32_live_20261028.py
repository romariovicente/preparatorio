"""Fresh real-Blender motion/identity exports and explicit full-body previews."""
import bpy,json,hashlib,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_V32_LIVE_VALIDATION_20261028.json'
F=ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation'
STATUS=ROOT/'work/v32_live_validation_status_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and not F.exists();F.mkdir()
    r=json.loads((ROOT/'reports/CHARACTER_THAI_COMPLETE_BASE_V32_20261028.json').read_text());assert sha(r['library'])==r['sha256']
    assert Path(bpy.data.filepath)==Path(r['library'])and not bpy.data.is_dirty
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[r['rig']];body=bpy.data.objects[r['bodyObject']];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    gray=bpy.data.materials.new('V32_QA_Gray_Only_No_Final_Skin');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    skin=body.data.materials[0];outfits=[o for o in scene.objects if o.name.startswith('V30_ORIGINAL_')or o.get('V28_original_source_name','').split('.')[0]=='Shoes']
    visibility={o.name:o.hide_render for o in outfits};archive={};images=[];rows=[]
    with np.load(ROOT/'reports/thai_head_cloth_cleanup_v29_20261028/reopened_native_motion_samples.npz')as n:oldhead={k:n[k].copy()for k in n.files if k.endswith('_headQ')}
    with np.load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')as n:bind={k:n[k].copy()for k in n.files}
    def choose(clip,frame):
        arm.data.pose_position='POSE';action=bpy.data.actions[clip+'.002'];arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();p=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';q,M=points(body);hq,hm=points(head);ev=arm.evaluated_get(layer.depsgraph)
        P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in bind['names55']]);A=np.array(ev.matrix_world,dtype=float)
        D=A@P@np.linalg.inv(bind['boneRest55'])@np.linalg.inv(A)@M
        blend=np.einsum('vj,jab->vab',bind['weights55'],D)
        expected=np.einsum('vab,vb->va',blend,np.column_stack([bind['restWorld'],np.ones(len(q))]))[:,:3]
        error=float(np.linalg.norm(q-expected,axis=1).max());assert error<2e-5,error
        identity=float(np.linalg.norm(hq-oldhead[label+'_headQ'],axis=1).max());assert identity<2e-5,identity
        assert np.isfinite(q).all()
        row={'clip':clip,'frame':frame,'bodyHeight':float(np.ptp(q[:,2])),'bodyMinZ':float(q[:,2].min()),
            'fullBodyAndHeadHeight':float(max(q[:,2].max(),hq[:,2].max())-min(q[:,2].min(),hq[:,2].min())),
            'maximumLBSPositionErrorMeters':error,'headIdentityGeometryDriftMeters':identity}
        rows.append(row);archive[label+'_bodyQ']=q;archive[label+'_headQ']=hq;archive[label+'_pose55']=P;archive[label+'_armWorld']=A;archive[label+'_bodyWorld']=M
    np.savez_compressed(F/'fresh_live_motion_samples_v32.npz',**archive)
    def render(clip,frame,view,direction,body_only=False,rest=False):
        choose(clip,frame)
        if rest:arm.data.pose_position='REST';layer.update()
        for o in outfits:o.hide_render=True if body_only else visibility[o.name]
        body.data.materials[0]=gray if body_only else skin
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.93;target=Vector((0,0,.84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        path=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(path);STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(path),'sha256':sha(path),'clip':clip,'frame':frame,'view':view,'grayBodyDiagnosticOnly':body_only,'rest':rest})
    for view,direction in [('dressed_front',(0,-1,0)),('dressed_side',(-1,0,0)),('dressed_back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',1,'gray_body_front',(0,-1,0),True);render('Idle',1,'gray_body_side',(-1,0,0),True)
    render('Idle',1,'gray_rest_front',(0,-1,0),True,True)
    for frame in [1,7,13,19]:render('Walk',frame,'gray_body_front',(0,-1,0),True)
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False);assert sha(r['library'])==r['sha256']
    result={'status':'saved-complete-base-reopened-and-native-motion-evaluated-awaiting-visual-acceptance',
        'library':r['library'],'sha256':r['sha256'],'samples':rows,'images':images,
        'allEightLiveLBSSamplesPass':all(row['maximumLBSPositionErrorMeters']<2e-5 for row in rows),
        'headFaceHairUnchangedAgainstV29':all(row['headIdentityGeometryDriftMeters']<2e-5 for row in rows),
        'allSupportingBodyMinZWithinTwoCentimeters':all(abs(row['bodyMinZ'])<.02 for row in rows),
        'idleStandingHeightWithinTwoCentimetersOf1p70':abs(rows[0]['fullBodyAndHeadHeight']-1.70)<.02,
        'wholeMotionOrAppearanceApproved':False,'originalClothingContinuityApproved':False,
        'originalShirtSkirtRemainDefaultDirection':True,'coatAndSchoolShirtOptional':True,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'sourceFileUnchanged':True,'MCPUsed':True,
        'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}));print(json.dumps({k:v for k,v in result.items()if k not in ['samples','images']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
