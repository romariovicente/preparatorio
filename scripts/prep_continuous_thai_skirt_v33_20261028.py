"""Bind a source-atlas-derived continuous neutral skirt; isolated local prototype.

V32 anatomy/identity/native animation and the unfinished original shirt are
preserved. Acceptance is explicitly deferred to visual and collision review.
"""
import bpy,bmesh,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'work/qa_thai_skirt_v33_20261028/skirt_neutral_retopology_work_v33.npz'
F=ROOT/'reports/thai_continuous_skirt_v33_20261028'
OUT=ROOT/'reports/CHARACTER_THAI_CONTINUOUS_SKIRT_V33_20261028.json'
STATUS=ROOT/'work/v33_continuous_skirt_status_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as n:return {k:n[k].copy()for k in n.files}
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

try:
    assert not OUT.exists() and not F.exists() and INPUT.is_file()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_SKIRT_V33_STAGE_20261028.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working']) and not bpy.data.is_dirty
    assert sha(bpy.data.filepath)==stage['workingSha256']
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    scene=window.scene;assert scene.name==stage['scene'];layer=scene.view_layers[0]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    body=bpy.data.objects['V32_Complete_Standard_Body_Prototype'];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    shirt=bpy.data.objects['V30_ORIGINAL_SHIRT_Regional_Bind_Pilot'];oldskirt=bpy.data.objects['V30_ORIGINAL_SKIRT_Regional_Bind_Pilot']
    arm=bpy.data.objects['V28_Clinical_Standard_Rig'];avatar=bpy.data.objects['V28_Thai_Clinical_Avatar_Root']
    def sig(obj):
        return {'arrays':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](obj.data)['arrays'].items()},
            'groups':list(obj.vertex_groups.keys()),'weights':hashlib.sha256(h['_weights'](obj.data,len(obj.vertex_groups)).tobytes()).hexdigest()}
    preserved={o.name:sig(o)for o in [body,head,shirt,oldskirt]}
    base=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')
    payload=load(INPUT);Q=payload['QIdleWorld'];T=payload['triangles'].astype(np.int32)
    UV=payload['UV0'].reshape(-1,2);UV2=payload['UV1'].reshape(-1,2)
    assert Q.ndim==2 and Q.shape[1]==3 and T.shape[1]==3 and len(UV)==3*len(T) and UV2.shape==UV.shape
    assert np.isfinite(Q).all()and np.isfinite(UV).all()and np.isfinite(UV2).all()
    source_path=ROOT/'reports/thai_original_outfit_bind_v30_20261028/regional_bind_and_reopened_walk_samples.npz'
    source=load(source_path);local=payload['sourceFaceLocalV30'];bary=payload['sourceBaryCorners']
    assert local.shape==(len(T),) and bary.shape==(len(T),3,3)
    assert local.min()>=0 and local.max()<len(source['skirt_sourceFaces'])
    assert np.array_equal(payload['sourceFaceID'],source['skirt_sourceFaces'][local])
    assert np.isfinite(bary).all()and bary.min()>=0 and np.max(np.abs(bary.sum(2)-1))<1e-12
    for uv,key in [(UV,'skirt_UV'),(UV2,'skirt_UV2')]:
        expected_uv=np.einsum('fck,fkd->fcd',bary,source[key].reshape(-1,3,2)[local])
        assert np.max(np.abs(uv.reshape(-1,3,2)-expected_uv))<1e-12
    assert str(payload['sourceSkirtDatasetSHA256'])==sha(source_path)
    assert str(payload['sourceBodyBindSHA256'])==sha(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')
    atlaspath=ROOT/'work/qa_thai_collar_semantics_v13_20261026/source_texture.png'
    assert str(payload['sourceAtlasSHA256'])==sha(atlaspath)
    names=base['names55'].tolist();A=base['armWorld'];R=base['boneRest55'];W=np.zeros((len(Q),55))
    def choose(clip,frame):
        arm.data.pose_position='POSE';action=bpy.data.actions[clip+'.002'];arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    assert np.max(np.abs(np.array(arm.evaluated_get(layer.depsgraph).matrix_world,dtype=float)-A))<1e-7
    P=np.array([np.array(arm.evaluated_get(layer.depsgraph).pose.bones[n].matrix,dtype=float)for n in names])
    assert np.max(np.abs(P-base['boneIdle55']))<1e-5
    assert np.array_equal(np.array([np.array(arm.data.bones[n].matrix_local,dtype=float)for n in names]),R)
    hip=np.array(arm.matrix_world@arm.pose.bones['mixamorig:Hips'].head)
    low=smooth((hip[2]+.12-Q[:,2])/.23);legmix=.45*low
    spine=.20*(1-low)*np.clip((Q[:,2]-hip[2])/.13,0,1);left=(np.tanh((Q[:,0]-hip[0])/.04)+1)/2
    for n,value in [('Hips',1-legmix-spine),('Spine',spine),('LeftUpLeg',legmix*left),('RightUpLeg',legmix*(1-left))]:W[:,names.index('mixamorig:'+n)]=value
    D=A@P@np.linalg.inv(R)@np.linalg.inv(A);blend=np.einsum('vj,jab->vab',W,D)
    cond=float(np.linalg.cond(blend).max());assert cond<1e6
    rest=np.linalg.solve(blend,np.column_stack([Q,np.ones(len(Q))])[:,:,None])[:,:,0][:,:3]
    F.mkdir()
    mesh=bpy.data.meshes.new('V33_Continuous_Original_Design_Skirt_BindMesh');mesh.from_pydata(rest.tolist(),[],T.tolist());mesh.update()
    # Material copy preserves the original photograph/atlas; UVs are explicitly derived.
    source_material=bpy.data.objects['V23_UNBOUND_World_Baseline_Source'].data.materials[0]
    material=source_material.copy();material.name='V33_Original_Black_Skirt_Atlas_Derived_UV';mesh.materials.append(material)
    mesh.polygons.foreach_set('use_smooth',[True]*len(T))
    for name,uv in [('UVMap',UV),('UVMap.001',UV2)]:mesh.uv_layers.new(name=name).data.foreach_set('uv',uv.reshape(-1))
    obj=bpy.data.objects.new('V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape',mesh);scene.collection.objects.link(obj)
    for name in names:obj.vertex_groups.new(name=name)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();dw=bm.verts.layers.deform.verify()
    for v in bm.verts:
        for j in np.flatnonzero(W[v.index]>0):v[dw][int(j)]=float(W[v.index,j])
    bm.to_mesh(mesh);bm.free();mesh.update()
    obj.parent=avatar;obj.matrix_parent_inverse=avatar.matrix_world.inverted();obj.matrix_world=Matrix.Identity(4)
    modifier=obj.modifiers.new('V33_Native_Remy_Continuous_Garment_Weights','ARMATURE');modifier.object=arm;modifier.use_deform_preserve_volume=False
    obj['PREP_source_atlas_preserved']=True;obj['PREP_UVs_derived_not_original_exact']=True
    obj['PREP_user_default_outfit_piece']='original black skirt';obj['PREP_appearance_approved']=False
    oldskirt.hide_render=True;oldskirt.hide_set(True,view_layer=layer)
    scene['PREP_role']='Isolated continuous skirt prototype on V32; not playable map'
    scene['PREP_current_outfit']='original shirt pending; continuous black skirt V33 awaiting QA'
    scene['PREP_default_outfit']='original white shirt + black skirt; clinical outfits optional'
    actual=h['_snapshot'](mesh)['arrays'];actualW=h['_weights'](mesh,55)
    assert np.max(np.abs(actualW.sum(1)-1))<1e-6 and (actualW>0).sum(1).max()<=4
    archive={'restP':actual['coordinates'],'triangles':actual['triangles'],'weights55':actualW,'names55':np.array(names),'UV0':actual['uv:UVMap'],'UV1':actual['uv:UVMap.001'],
        'QIdleFit':Q,'armWorld':A,'boneRest55':R,'objectWorld':np.eye(4),'bodyTriangles':base['triangles']}
    for key in payload:
        if key not in ['QIdleWorld','triangles','UV0','UV1']:archive['payload_'+key]=payload[key]
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_CONTINUOUS_SKIRT_V33_20261028.blend';assert not path.exists()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    savedsha=sha(path);scene_name=scene.name
    arm_name=arm.name;body_name=body.name;head_name=head.name;obj_name=obj.name
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scene_name];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects[arm_name];body=bpy.data.objects[body_name];head=bpy.data.objects[head_name];obj=bpy.data.objects[obj_name]
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);m=ev.to_mesh();p=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    rows=[];images=[]
    for clip,frame in [('Idle',1),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';q,M=points(obj);bq,_=points(body);ev=arm.evaluated_get(layer.depsgraph)
        P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names]);A=np.array(ev.matrix_world,dtype=float)
        D=A@P@np.linalg.inv(R)@np.linalg.inv(A)@M;bl=np.einsum('vj,jab->vab',actualW,D)
        expected=np.einsum('vab,vb->va',bl,np.column_stack([archive['restP'],np.ones(len(q))]))[:,:3]
        err=float(np.linalg.norm(q-expected,axis=1).max());assert err<2e-5
        fiterr=float(np.linalg.norm(q-Q,axis=1).max())if clip=='Idle'else None
        if fiterr is not None:assert fiterr<2e-5
        # BVH overlap detects crossing faces; signed nearest is an additional diagnostic.
        bodytree=BVHTree.FromPolygons(bq.tolist(),base['triangles'].tolist(),all_triangles=True)
        skirttree=BVHTree.FromPolygons(q.tolist(),T.tolist(),all_triangles=True)
        crossings=skirttree.overlap(bodytree)
        signed=[]
        for point in q:
            loc,normal,index,distance=bodytree.find_nearest(Vector(point));signed.append(float((Vector(point)-loc).dot(normal)))
        signed=np.array(signed)
        row={'clip':clip,'frame':frame,'maximumLBSPositionErrorMeters':err,'IdleTargetErrorMeters':fiterr,
            'bodyCrossingTrianglePairsBVH':len(crossings),'signedNearestMinimumMeters':float(signed.min()),'negativeSignedVertexCount':int((signed<-.001).sum()),
            'bounds':[q.min(0).tolist(),q.max(0).tolist()]};rows.append(row)
        archive[label+'_skirtQ']=q;archive[label+'_bodyQ']=bq;archive[label+'_pose55']=P;archive[label+'_armWorld']=A;archive[label+'_skirtWorld']=M
        archive[label+'_bodyTriangleCrossingPairs']=np.array(crossings,dtype=np.int32).reshape(-1,2);archive[label+'_signedNearest']=signed
    ar=F/'reopened_skirt_bind_and_motion_v33.npz';np.savez_compressed(ar,**archive)
    def render(clip,frame,view,direction,detail=False):
        choose(clip,frame);camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.65 if detail else 1.93
        target=Vector((0,0,.92 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        imagepath=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(imagepath);STATUS.write_text(json.dumps({'status':'rendering','path':str(imagepath)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(imagepath),'sha256':sha(imagepath),'clip':clip,'frame':frame,'view':view})
    for view,direction in [('front',(0,-1,0)),('side',(-1,0,0)),('back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',1,'skirt_detail_front',(0,-1,0),True)
    for frame in [1,7,13,19]:render('Walk',frame,'front',(0,-1,0))
    # Discard rendering-only camera changes by reopening the freshly saved candidate.
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    assert all(sig(bpy.data.objects[n])==s for n,s in preserved.items())
    assert sha(stage['working'])==stage['workingSha256'] and sha(stage['priorReviewFile'])==stage['priorReviewSha256']
    result={'status':'continuous-skirt-candidate-saved-and-reopened-awaiting-independent-QA','library':str(path),'sha256':savedsha,'scene':scene_name,
        'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],'stagedWorkUnchanged':True,'priorReviewUnchanged':True,
        'payload':str(INPUT),'payloadSha256':sha(INPUT),'archive':str(ar),'archiveSha256':sha(ar),'newObject':obj_name,
        'oldSkirtPreservedAndHidden':True,'bodyHeadShirtOldSkirtDataUnchanged':True,'nativeRigRestAndActionsEdited':False,
        'vertices':len(Q),'triangles':len(T),'maximumInverseBindCondition':cond,'maximumInfluences':int((actualW>0).sum(1).max()),
        'weightSumMaximumError':float(np.abs(actualW.sum(1,dtype=float)-1).max()),'samples':rows,'images':images,
        'sourceAtlasUnchanged':True,'UVsDerivedNotOriginalExact':True,'appearanceApproved':False,'wholeAnimationApproved':False,
        'shirtCompleted':False,'coatAndSchoolShirtOptional':True,'runtimeChanged':False,'GLBExportedOrReimported':False,'masterChanged':False,
        'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    assert sha(path)==savedsha;OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'candidate-ready-for-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items()if k not in ['samples','images']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
