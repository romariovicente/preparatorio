"""Inspect actual native Idle/Walk and render the approved standard-body prototype."""
import bpy, json, hashlib, traceback, runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_clinical_body_v28_20261027/native_motion_review'
OUT=ROOT/'reports/CHARACTER_THAI_CLINICAL_MOTION_V28_20261027.json'
STATUS=ROOT/'work/v28_clinical_motion_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists() and not F.exists()
    r=json.loads((ROOT/'reports/CHARACTER_THAI_CLINICAL_IDENTITY_V28_20261027.json').read_text())
    assert Path(bpy.data.filepath)==Path(r['library']) and sha(r['library'])==r['sha256']
    F.mkdir();window=bpy.context.window or bpy.context.window_manager.windows[0]
    scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[r['rig']];head=bpy.data.objects[r['headObject']]
    body=bpy.data.objects[r['bodyObject']]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    def choose(label,frame):
        action=bpy.data.actions[r['nativeClips'][label]['action']]
        arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    def meshdata(obj):
        ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
        a=h['_snapshot'](mesh)['arrays'];M=np.array(ev.matrix_world,dtype=np.float64)
        q=a['coordinates']@M[:3,:3].T+M[:3,3]
        ev.to_mesh_clear();return q,a,M
    def headframe():
        a=arm.evaluated_get(layer.depsgraph)
        return np.array(a.matrix_world@a.pose.bones[r['headBone']].matrix,dtype=np.float64)
    choose('Idle',1);C=np.linalg.inv(headframe())@np.array(head.matrix_world,dtype=np.float64)
    rows=[];archive={};visible=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
    shoes=next(o for o in visible if o.get('V28_original_source_name','').split('.')[0]=='Shoes')
    for clip,frames in [('Idle',[1,51,101,151]),('Walk',[1,7,13,19])]:
        for frame in frames:
            choose(clip,frame);label=f'{clip}_{frame}';hq,ha,hm=meshdata(head);bq,ba,bm=meshdata(body)
            sq,_,_=meshdata(shoes);allq=np.concatenate([meshdata(o)[0]for o in visible])
            H=headframe();expected=H@C;attachment=float(np.abs(expected-hm).max())
            row={'label':label,'clip':clip,'frame':frame,'height':float(np.ptp(allq[:,2])),
                 'minimumZ':float(allq[:,2].min()),'shoeMinimumZ':float(sq[:,2].min()),
                 'headAttachmentMaxMatrixError':attachment,'headWorld':hm.tolist(),
                 'headBoneWorld':H.tolist(),'bodyWorld':bm.tolist(),
                 'slot':arm.animation_data.action_slot.identifier}
            rows.append(row);archive[label+'_headQ']=hq;archive[label+'_bodyQ']=bq
            archive[label+'_shoeQ']=sq;archive[label+'_headMatrix']=hm
            archive[label+'_boneHeadMatrix']=H
    archive['headT']=ha['triangles'];archive['bodyT']=ba['triangles'];archive['relativeHeadFrame']=C
    archive['headRawP']=h['_snapshot'](head.data)['arrays']['coordinates']
    archive['headRawUV']=h['_snapshot'](head.data)['arrays']['uv:UVMap']
    np.savez_compressed(F/'native_idle_walk_samples.npz',**archive)
    walk=[row for row in rows if row['clip']=='Walk']
    movement=max(float(np.linalg.norm(archive['Walk_1_bodyQ']-archive[f'Walk_{i}_bodyQ'],axis=1).max())for i in [7,13,19])
    images=[]
    def render(label,frame,view,direction,close=False):
        choose(label,frame)
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=512;scene.render.resolution_y=768
        scene.render.resolution_percentage=100;scene.render.threads_mode='FIXED';scene.render.threads=2
        scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
        scene.view_settings.view_transform='AgX'
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.69 if close else 1.89
        target=Vector((0,0,1.39 if close else .85));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        path=F/f'{label}_{frame}_{view}.png';scene.render.filepath=str(path)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'clip':label,'frame':frame,'view':view,'path':str(path),'sha256':sha(path)})
    render('Idle',1,'front',(0,-1,0));render('Idle',1,'side',(-1,0,0));render('Idle',1,'back',(0,1,0))
    render('Idle',1,'neck_front',(0,-1,0),True);render('Idle',1,'neck_side',(-1,0,0),True)
    for frame in [1,7,13,19]:render('Walk',frame,'front',(0,-1,0))
    choose('Idle',1)
    result={'status':'native-samples-exported-and-rendered-awaiting-visual-QA','library':r['library'],
            'sha256':r['sha256'],'samples':rows,'images':images,'maximumNativeWalkBodyDisplacementMeters':movement,
            'actualWalkChangesBody':movement>.03,'allHeadBindingsFollowNativeHeadBone':all(x['headAttachmentMaxMatrixError']<5e-5 for x in rows),
            'allHeightsWithinTwoCentimetersOf1p70':all(abs(x['height']-1.70)<.02 for x in rows),
            'allSupportingSolesWithinTwoCentimetersOfGround':all(abs(x['shoeMinimumZ'])<.02 for x in rows),
            'headHasNoArmatureDeformer':not any(m.type=='ARMATURE'for m in head.modifiers),
            'headParentBone':head.parent_bone,'hiddenOriginalIdentityObjects':r['originalIdentityObjectsHiddenAndExcluded'],
            'headFaceHairVisualApproved':False,'neckSeamVisualApproved':False,'runtimeChanged':False,
            'originalRemySourceUnchanged':sha(r['whiteBodySource'])==r['whiteBodySourceSha256'],
            'workingLibraryUnchangedDuringQA':sha(r['library'])==r['sha256'],'remoteOperations':False,
            'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items()if k not in ['images','samples']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
