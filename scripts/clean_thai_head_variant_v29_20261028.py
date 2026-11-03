"""Remove confirmed old cloth from the head extraction, preserving original outfits.

Runs in hidden local Blender when no GUI/MCP is running. This does not integrate
the clinical variant into the game or change the user's requested default outfit.
"""
import bpy,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_HEAD_CLOTH_CLEANUP_V29_20261028.json'
STATUS=ROOT/'work/v29_head_cleanup_status_20261028.json'
F=ROOT/'reports/thai_head_cloth_cleanup_v29_20261028'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists() and not F.exists()
    audit=json.loads((ROOT/'reports/CHARACTER_THAI_V28_RESUME_AUDIT_20261028.json').read_text())
    assert not audit['meshDifferences'] and audit['rigRestUnchanged'] and audit['nativeActionsUnchanged']
    source=Path(audit['library']);assert sha(source)==audit['currentSha256']
    maskpath=ROOT/'work/qa_thai_head_cloth_review_v29_20261028/head_identity_face_mask_v28_cloth_review_20261028.npz'
    assert sha(maskpath)=='cf9d5a8b5d1d880257e4369a719e5cc85cea071bbfcb05a951289f54bc1b4717'
    F.mkdir();cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_HEAD_CLOTH_CLEANUP_V29_20261028.blend'
    assert not cp.exists();shutil.copy2(source,cp)
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    r=json.loads((ROOT/'reports/CHARACTER_THAI_CLINICAL_IDENTITY_V28_20261027.json').read_text())
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    with np.load(maskpath)as n:mask={k:n[k].copy()for k in n.files}
    with np.load(ROOT/'reports/thai_clinical_body_v28_20261027/head_and_body_extraction_provenance.npz')as n:provenance={k:n[k].copy()for k in n.files}
    scene=bpy.data.scenes[r['scene']];window=bpy.context.window or bpy.context.window_manager.windows[0]
    window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[r['rig']];head=bpy.data.objects[r['headObject']];body=bpy.data.objects[r['bodyObject']]
    def choose(clip,frame):
        a=bpy.data.actions[r['nativeClips'][clip]['action']]
        arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
        for tr in arm.animation_data.nla_tracks:tr.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    old=h['_snapshot'](head.data)['arrays'];oldfaces=provenance['headSourceFaceIndices']
    assert len(old['triangles'])==len(oldfaces)==9492
    localfaces=np.flatnonzero(np.isin(oldfaces,mask['face_indices_to_keep']))
    removed=np.setdiff1d(oldfaces,oldfaces[localfaces]);assert len(localfaces)==9450 and len(removed)==42
    used=np.unique(old['triangles'][localfaces]);lookup=np.full(len(old['coordinates']),-1,np.int32);lookup[used]=np.arange(len(used))
    loops=(localfaces[:,None]*3+np.arange(3)).reshape(-1)
    normals=np.empty(len(head.data.loops)*3,np.float32)
    head.data.attributes['V28_identity_corner_normal'].data.foreach_get('vector',normals)
    normals=normals.reshape(-1,3)
    mesh=bpy.data.meshes.new('V29_Thai_Identity_Cloth_Residues_Removed')
    mesh.from_pydata(old['coordinates'][used].tolist(),[],lookup[old['triangles'][localfaces]].tolist());mesh.update()
    for mat in head.data.materials:mesh.materials.append(mat)
    mesh.polygons.foreach_set('use_smooth',old['polygonSmooth'][localfaces].reshape(-1))
    mesh.polygons.foreach_set('material_index',old['polygonMaterial'][localfaces].reshape(-1))
    for key,a in old.items():
        if key.startswith('uv:'):
            uv=mesh.uv_layers.new(name=key[3:]);uv.data.foreach_set('uv',a[loops].reshape(-1))
    mesh.normals_split_custom_set(normals[loops].tolist())
    attr=mesh.attributes.new('V28_identity_corner_normal','FLOAT_VECTOR','CORNER')
    attr.data.foreach_set('vector',normals[loops].reshape(-1))
    head.data=mesh;head['PREP_confirmed_old_cloth_faces_removed_from_head_only']=removed.tolist()
    new=h['_snapshot'](mesh)['arrays']
    assert np.array_equal(new['coordinates'],old['coordinates'][used])
    assert all(np.array_equal(new[k],v[loops])for k,v in old.items()if k.startswith('uv:'))
    scene['PREP_variant']='optional clinical clothing prototype; NOT default outfit'
    scene['PREP_user_default_outfit']='Original Thai white shirt and black skirt; refit to new body still pending'
    scene['PREP_user_optional_outfits']='Lab coat and school shirt selectable in wardrobe menu; not yet integrated'
    scene['PREP_runtime_integration_approved']=False
    text=bpy.data.texts.new('PREP_WARDROBE_POLICY_20261028')
    text.write('User confirmed 27/10/2026: preserve the original white shirt and black skirt as the default.\n'
               'The standard Remy body is approved only with Thai face and hair preserved.\n'
               'Lab coat and school shirt are optional menu additions.\n'
               'This clinical scene is an optional prototype, not the final default playable outfit.\n'
               'Original complete Thai source and wardrobe geometry remain intact.\n')
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HEAD_CLEAN_OPTIONAL_CLINICAL_V29_20261028.blend'
    assert not path.exists()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    savedsha=sha(path)
    # Fresh readback is mandatory: changing group names can leave a stale viewport graph.
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[r['rig']];head=bpy.data.objects[r['headObject']];body=bpy.data.objects[r['bodyObject']]
    assert len(body.vertex_groups)==55 and len(arm.data.bones)==55
    assert np.array_equal(h['_weights'](body.data,55),provenance['bodySourceWeights'][provenance['bodyKeptSourceVertices']])
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v)
        M=np.array(ev.matrix_world,dtype=float);q=v.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
    def headframe():
        ev=arm.evaluated_get(layer.depsgraph);return np.array(ev.matrix_world@ev.pose.bones[r['headBone']].matrix,dtype=float)
    choose('Idle',1);bind=np.linalg.inv(headframe())@np.array(head.matrix_world,dtype=float)
    visible=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
    shoes=next(o for o in visible if o.get('V28_original_source_name','').split('.')[0]=='Shoes')
    data={};samples=[]
    for clip,frames in [('Idle',[1,51,101,151]),('Walk',[1,7,13,19])]:
        for frame in frames:
            choose(clip,frame);label=f'{clip}_{frame}';allq=np.concatenate([points(o)for o in visible])
            hm=np.array(head.matrix_world,dtype=float);H=headframe()
            samples.append({'clip':clip,'frame':frame,'height':float(np.ptp(allq[:,2])),
                'supportShoeZ':float(points(shoes)[:,2].min()),'headBindingMaxMatrixError':float(np.abs(H@bind-hm).max())})
            data[label+'_headQ']=points(head);data[label+'_bodyQ']=points(body);data[label+'_headMatrix']=hm;data[label+'_boneHeadMatrix']=H
    movement=max(float(np.linalg.norm(data['Walk_1_bodyQ']-data[f'Walk_{f}_bodyQ'],axis=1).max())for f in [7,13,19])
    assert movement>.03 and all(abs(s['supportShoeZ'])<.02 and s['headBindingMaxMatrixError']<5e-5 for s in samples)
    assert abs(samples[0]['height']-1.70)<.02
    data.update(retainedOriginalHeadFaces=oldfaces[localfaces],removedOriginalHeadClothFaces=removed,relativeHeadFrame=bind)
    np.savez_compressed(F/'reopened_native_motion_samples.npz',**data)
    images=[]
    def render(clip,frame,view,direction,close=False):
        choose(clip,frame);scene.render.engine='BLENDER_EEVEE'
        scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG'
        scene.view_settings.view_transform='AgX';camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.69 if close else 1.9
        target=Vector((0,0,1.39 if close else .85));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        output=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(output)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(output)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'clip':clip,'frame':frame,'view':view,'path':str(output),'sha256':sha(output)})
    for view,direction in [('front',(0,-1,0)),('side',(-1,0,0)),('back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',1,'neck_front',(0,-1,0),True);render('Idle',1,'neck_side',(-1,0,0),True)
    for frame in [1,7,13,19]:render('Walk',frame,'front',(0,-1,0))
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    result={'status':'head-extraction-cleaned-saved-reopened-and-native-walk-sampled-awaiting-visual-review',
        'library':str(path),'sha256':savedsha,'checkpoint':str(cp),'checkpointSha256':sha(cp),'sourceLibrary':str(source),'sourceSha256':sha(source),
        'sourceHashUnchanged':sha(source)==audit['currentSha256'],'headMask':str(maskpath),'headMaskSha256':sha(maskpath),
        'removedHeadOnlyClothFaces':removed.tolist(),'remainingHeadFaces':len(localfaces),'retainedCoordinatesAndUVExact':True,
        'retainedNormalsAttributeExact':True,'bodyRetainedWeightsExact':True,'nativeRigAndActionsEdited':False,'samples':samples,
        'maximumNativeWalkBodyDisplacementMeters':movement,'allSupportingSolesWithinTwoCentimeters':all(abs(s['supportShoeZ'])<.02 for s in samples),
        'allHeadBindingsFollowNativeHeadBone':all(s['headBindingMaxMatrixError']<5e-5 for s in samples),'idleStandingHeight':samples[0]['height'],
        'allAnimatedHeightsWithinTwoCentimetersOf1p70':all(abs(s['height']-1.70)<.02 for s in samples),
        'animatedHeightExcursionIsNativeClipPose_NotAClaimOfConstantStandingHeight':True,'images':images,
        'defaultOutfitUserRequires':'original Thai white shirt and black skirt, fitted to approved standard body',
        'optionalMenuOutfitsUserRequires':['lab coat','school shirt'],'clinicalVariantIsNotDefault':True,
        'originalSourceOutfitRemovedOrModified':False,'originalOutfitRefitCompleted':False,'schoolShirtCompleted':False,
        'menuChanged':False,'runtimeChanged':False,'masterChanged':False,'GLBExportedOrReimported':False,
        'MCPAvailable':False,'execution':'Blender 5.2.3 hidden background CLI because GUI/MCP was absent',
        'blenderVersion':bpy.app.version_string,'newVisibleWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    assert sha(path)==savedsha
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items()if k not in ['images','samples','removedHeadOnlyClothFaces']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
