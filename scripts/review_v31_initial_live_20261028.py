"""Reopen the saved complete-body candidate in the verified project Blender window."""
import bpy,json,hashlib,traceback,runpy
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_V31_INITIAL_LIVE_REVIEW_20261028.json'
F=ROOT/'reports/thai_complete_anatomical_base_v31_20261028/initial_live_review'
STATUS=ROOT/'work/v31_initial_live_review_status_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and(not F.exists()or not any(F.iterdir()));F.mkdir(exist_ok=True)
    r=json.loads((ROOT/'reports/CHARACTER_THAI_COMPLETE_BASE_V31_20261028.json').read_text());assert sha(r['library'])==r['sha256']
    if not bpy.data.filepath:
        assert not bpy.data.is_dirty and set(bpy.data.objects.keys())=={'Cube','Camera','Light'}
    else:
        assert Path(bpy.data.filepath)==Path(r['library'])
        if bpy.data.is_dirty:
            assert any(m.name.startswith('V31_QA_Gray_Only_No_Final_Skin')for m in bpy.data.materials)
            snapshot=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_V31_UI_REVIEW_RETRY_20261028.blend'
            assert not snapshot.exists()
            bpy.ops.wm.save_as_mainfile(filepath=str(snapshot),compress=True,copy=True)
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[r['rig']];body=bpy.data.objects[r['bodyObject']];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    gray=bpy.data.materials.new('V31_QA_Gray_Only_No_Final_Skin');gray.use_nodes=True;next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    skin=body.data.materials[0]
    outfits=[o for o in scene.objects if o.name.startswith('V30_ORIGINAL_')or o.get('V28_original_source_name','').split('.')[0]=='Shoes']
    visibility={o.name:o.hide_render for o in outfits}
    archive={};images=[]
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002'];arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();p=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
    def render(clip,frame,view,direction,body_only=False):
        choose(clip,frame)
        for o in outfits:o.hide_render=True if body_only else visibility[o.name]
        body.data.materials[0]=gray if body_only else skin
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.93;target=Vector((0,0,.84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        path=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(path);STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        label=f'{clip}_{frame}';archive[label+'_bodyQ']=points(body);archive[label+'_headQ']=points(head)
        archive[label+'_pose55']=np.array([np.array(arm.evaluated_get(layer.depsgraph).pose.bones[n].matrix)for n in body.vertex_groups.keys()])
        images.append({'path':str(path),'sha256':sha(path),'clip':clip,'frame':frame,'view':view,'grayBodyDiagnosticOnly':body_only})
    render('Idle',1,'dressed_front',(0,-1,0));render('Idle',1,'dressed_side',(-1,0,0))
    render('Idle',1,'gray_body_front',(0,-1,0),True);render('Walk',7,'gray_body_front',(0,-1,0),True)
    np.savez_compressed(F/'initial_live_samples_v31.npz',**archive)
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    assert sha(r['library'])==r['sha256']
    result={'status':'four-real-live-previews-created-awaiting-review','library':r['library'],'sha256':r['sha256'],'images':images,
        'sourceFileUnchanged':True,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'runtimeChanged':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}));print(json.dumps({'status':result['status'],'images':len(images)}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
