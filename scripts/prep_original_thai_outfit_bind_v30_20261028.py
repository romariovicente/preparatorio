"""Original shirt/skirt regional fit + new native weights: a separated, unapproved pilot.

Original scan, atlas, UVs, Remy, V29 and runtime are never overwritten. The
conservative masks have gaps; this script does not declare complete garments.
"""
import bpy,bmesh,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];INPUT=ROOT/'work/qa_thai_original_outfit_v30_20261028'
F=ROOT/'reports/thai_original_outfit_bind_v30_20261028';OUT=ROOT/'reports/CHARACTER_THAI_ORIGINAL_OUTFIT_BIND_V30_20261028.json'
STATUS=ROOT/'work/v30_original_outfit_bind_status_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as n:return {k:n[k].copy()for k in n.files}
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def unit(v):return v/np.linalg.norm(v)
def rotation_between(a,b):
    a=unit(a);b=unit(b);v=np.cross(a,b);c=np.dot(a,b)
    K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    assert c>-.95
    return np.eye(3)+K+K@K/(1+c)
try:
    assert not OUT.exists() and (not F.exists() or not any(F.iterdir()));F.mkdir(exist_ok=True)
    prior=json.loads((ROOT/'reports/CHARACTER_THAI_HEAD_CLOTH_CLEANUP_V29_20261028.json').read_text())
    extraction=json.loads((INPUT/'original_outfit_extraction_report_v30.json').read_text())
    native_report=json.loads((INPUT/'target_surface_and_rig_report.json').read_text())
    proxy_report=json.loads((INPUT/'native_clothing_proxies_report.json').read_text())
    source=Path(prior['library']);assert sha(source)==prior['sha256']
    assert sha(extraction['shirtMask'])==extraction['shirtMaskSHA256'] and sha(extraction['skirtMask'])==extraction['skirtMaskSHA256']
    assert sha(native_report['archive'])==native_report['archiveSha256'] and sha(proxy_report['archive'])==proxy_report['archiveSha256']
    cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_ORIGINAL_OUTFIT_V30_20261028.blend'
    if cp.exists():assert sha(cp)==prior['sha256']
    else:shutil.copy2(source,cp)
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    scene=bpy.data.scenes['PREP_THAI_CLINICAL_STANDARD_BODY_V28'];scene.name='REVIEW_THAI_ORIGINAL_OUTFIT_BIND_V30'
    window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects['V28_Clinical_Standard_Rig'];avatar=bpy.data.objects['V28_Thai_Clinical_Avatar_Root']
    head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved'];native_body=bpy.data.objects['V28_Standard_Clinical_Body_No_Original_Head']
    def choose(clip,frame):
        a=bpy.data.actions[clip+'.002'];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
        for tr in arm.animation_data.nla_tracks:tr.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    frozen=load(extraction['sourceDataset']);target=load(native_report['archive']);proxies=load(proxy_report['archive'])
    Q=frozen['posedWorld'];T=frozen['stage::triangles'];assert T.shape==(44999,3)
    oldrig=load(ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz')
    oldheads=oldrig['bone_pose_heads']@oldrig['arm_world'][:3,:3].T+oldrig['arm_world'][:3,3]
    oldnames=oldrig['group_names'].tolist();names=target['boneNames'].tolist()
    oldH={n:oldheads[i]for i,n in enumerate(oldnames)};newH={n:target['boneIdleHeadsWorld'][i]for i,n in enumerate(names)}
    A=target['armWorld'];deform=A@target['boneIdleMatrices']@np.linalg.inv(target['boneRestMatrices'])@np.linalg.inv(A)
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    # Region proxies include the true native top: the skin mesh has no full hidden torso.
    proxyQ=np.concatenate([target['bodyIdleWorld'],proxies['topQ'],proxies['bottomQ']])
    proxyW=np.concatenate([target['bodyWeights'],proxies['topW'],proxies['bottomW']])
    proxyT=np.concatenate([target['bodyTriangles'],proxies['topT']+len(target['bodyIdleWorld']),proxies['bottomT']+len(target['bodyIdleWorld'])+len(proxies['topQ'])])
    averageW=proxyW[proxyT].mean(1);centers=proxyQ[proxyT].mean(1)
    def indices(parts):return [i for i,n in enumerate(names)if n.split(':')[-1]in parts]
    torso_ids=indices(['Hips','Spine','Spine1','Spine2','Neck'])
    left_ids=indices(['LeftShoulder','LeftArm','LeftForeArm']);right_ids=indices(['RightShoulder','RightArm','RightForeArm'])
    region_faces={
        'torso':np.flatnonzero((averageW[:,torso_ids].sum(1)>.6)&(centers[:,2]>.9)),
        'left':np.flatnonzero((averageW[:,left_ids].sum(1)>.55)&(centers[:,2]>1.04)),
        'right':np.flatnonzero((averageW[:,right_ids].sum(1)>.55)&(centers[:,2]>1.04)),
        'skirt':np.flatnonzero((averageW[:,indices(['Hips','Spine','Spine1','LeftUpLeg','RightUpLeg'])].sum(1)>.6)&(centers[:,2]>.80)&(centers[:,2]<1.18))}
    trees={k:BVHTree.FromPolygons(proxyQ.tolist(),proxyT[v].tolist(),all_triangles=True)for k,v in region_faces.items()}
    assert all(len(v)>30 for v in region_faces.values())
    def nearest(region,p):
        location,normal,index,distance=trees[region].find_nearest(Vector(p));assert index is not None
        tri=proxyT[region_faces[region][index]];points=proxyQ[tri];v0=points[1]-points[0];v1=points[2]-points[0];v2=np.array(location)-points[0]
        d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01
        if abs(den)<1e-20:bar=np.array([1.,0.,0.])
        else:
            v=(d11*(v2@v0)-d01*(v2@v1))/den;w=(d00*(v2@v1)-d01*(v2@v0))/den;bar=np.array([1-v-w,v,w]);bar=np.maximum(bar,0);bar/=bar.sum()
        return np.array(location),np.array(normal),bar@proxyW[tri],float(distance)
    source_materials=bpy.data.objects['V23_UNBOUND_World_Baseline_Source'].data.materials
    garments=[];archive={};rows=[]
    for label,maskpath in [('shirt',extraction['shirtMask']),('skirt',extraction['skirtMask'])]:
        mask=load(maskpath);faces=mask['face_indices_to_keep'];used=np.unique(T[faces]);q=Q[used].astype(float)
        loops=(faces[:,None]*3+np.arange(3)).reshape(-1)
        # Torso maps actual hip/neck landmarks; sleeves use their anatomical arm segment.
        t=(q[:,2]-oldH['hips'][2])/(oldH['neck'][2]-oldH['hips'][2])
        center=newH['mixamorig:Hips']+(newH['mixamorig:Neck']-newH['mixamorig:Hips'])*t[:,None]
        scale=float(target['avatarRootWorld'][0,0]);fit=center.copy();fit[:,:2]+=q[:,:2]*scale
        fit[:,2]=newH['mixamorig:Hips'][2]+(q[:,2]-oldH['hips'][2])*(newH['mixamorig:Neck'][2]-newH['mixamorig:Hips'][2])/(oldH['neck'][2]-oldH['hips'][2])
        alpha=smooth((np.abs(q[:,0])-.15)/.09)*smooth((q[:,2]-1.10)/.14)if label=='shirt'else np.zeros(len(q))
        if label=='shirt':
            for side,prefix,positive in [('L','Left',True),('R','Right',False)]:
                ids=np.flatnonzero((q[:,0]>0)==positive)
                sv=oldH[side+'_forearm']-oldH[side+'_upper_arm'];tv=newH['mixamorig:'+prefix+'ForeArm']-newH['mixamorig:'+prefix+'Arm']
                R=rotation_between(sv,tv);ratio=np.linalg.norm(tv)/np.linalg.norm(sv)
                moved=(q[ids]-oldH[side+'_upper_arm'])@R.T*ratio+newH['mixamorig:'+prefix+'Arm']
                fit[ids]=fit[ids]*(1-alpha[ids,None])+moved*alpha[ids,None]
        # Move only toward anatomically restricted proxies, with capped corrections.
        initial=fit.copy();W=np.zeros((len(q),55));corrections=[]
        for i,p in enumerate(fit):
            side='left'if q[i,0]>0 else 'right';region='skirt'if label=='skirt'else(side if alpha[i]>.45 else 'torso')
            near,n,_,distance=nearest(region,p);signed=float((p-near)@n)
            offset=np.clip(.004-signed,-.035,.035)if signed<.004 or distance>.06 else 0.
            if distance>.06 and signed>.004:offset=-min(distance-.035,.035)
            fit[i]=p+n*offset;corrections.append(float(abs(offset)))
            if label=='shirt':
                _,_,tw,_=nearest('torso',fit[i]);_,_,aw,_=nearest(side,fit[i])
                w=tw*(1-alpha[i])+aw*alpha[i]
                allowed=torso_ids+(left_ids if q[i,0]>0 else right_ids);w[[j for j in range(55)if j not in allowed]]=0
                order=np.argsort(w)[-4:];W[i,order]=w[order];assert W[i].sum()>0;W[i]/=W[i].sum()
            else:
                hipZ=newH['mixamorig:Hips'][2];low=float(smooth((hipZ+.12-fit[i,2])/.23));legmix=.45*low
                spine=.20*(1-low)*float(np.clip((fit[i,2]-hipZ)/.13,0,1));left=(np.tanh((fit[i,0]-newH['mixamorig:Hips'][0])/.04)+1)/2
                for n,value in [('Hips',1-legmix-spine),('Spine',spine),('LeftUpLeg',legmix*left),('RightUpLeg',legmix*(1-left))]:W[i,names.index('mixamorig:'+n)]=value
        assert np.isfinite(fit).all() and np.max(np.abs(W.sum(1)-1))<1e-6 and np.max((W>0).sum(1))<=4
        if label=='skirt':assert np.count_nonzero(W[:,[i for i,n in enumerate(names)if n.split(':')[-1]not in ['Hips','Spine','LeftUpLeg','RightUpLeg']]])==0
        blend=np.einsum('vj,jab->vab',W,deform);condition=float(np.linalg.cond(blend).max());assert condition<1e6
        rest=np.linalg.solve(blend,np.column_stack([fit,np.ones(len(fit))])[:,:,None])[:,:,0][:,:3]
        lookup=np.full(len(Q),-1,np.int32);lookup[used]=np.arange(len(used));mesh=bpy.data.meshes.new('V30_Original_'+label+'_BindMesh')
        mesh.from_pydata(rest.tolist(),[],lookup[T[faces]].tolist());mesh.update()
        for material in source_materials:mesh.materials.append(material)
        mesh.polygons.foreach_set('use_smooth',frozen['stage::polygonSmooth'][faces].reshape(-1))
        mesh.polygons.foreach_set('material_index',frozen['stage::polygonMaterial'][faces].reshape(-1))
        for key in ['stage::uv:UVMap','stage::uv:UVMap.001']:
            uv=mesh.uv_layers.new(name=key.split('uv:')[1]);uv.data.foreach_set('uv',frozen[key][loops].reshape(-1))
        obj=bpy.data.objects.new('V30_ORIGINAL_'+label.upper()+'_Regional_Bind_Pilot',mesh);scene.collection.objects.link(obj)
        for name in names:obj.vertex_groups.new(name=name)
        bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.verts.index_update();layerW=bm.verts.layers.deform.verify()
        for v in bm.verts:
            for j in np.flatnonzero(W[v.index]>0):v[layerW][int(j)]=float(W[v.index,j])
        bm.to_mesh(mesh);bm.free();mesh.update()
        obj.parent=avatar;obj.matrix_parent_inverse=avatar.matrix_world.inverted();obj.matrix_world=Matrix.Identity(4)
        skin=obj.modifiers.new('V30_Native_Remy_Weights_New_Garment','ARMATURE');skin.object=arm;skin.use_deform_preserve_volume=False
        obj['PREP_original_outfit_piece']=label;obj['PREP_user_default_outfit']=True;obj['PREP_incomplete_conservative_extraction']=True
        obj['PREP_source_face_ids']=faces.tolist();garments.append(obj)
        actual=h['_snapshot'](mesh)['arrays'];actualW=h['_weights'](mesh,55)
        assert np.array_equal(actual['uv:UVMap'],frozen['stage::uv:UVMap'][loops]) and np.array_equal(actual['uv:UVMap.001'],frozen['stage::uv:UVMap.001'][loops])
        archive[label+'_sourceFaces']=faces;archive[label+'_sourceVertices']=used;archive[label+'_sourceLoops']=loops
        archive[label+'_sourceQ']=q;archive[label+'_fitQ']=fit;archive[label+'_restP']=actual['coordinates'];archive[label+'_W55']=actualW
        archive[label+'_T']=actual['triangles'];archive[label+'_UV']=actual['uv:UVMap'];archive[label+'_UV2']=actual['uv:UVMap.001']
        rows.append({'piece':label,'object':obj.name,'vertices':len(used),'faces':len(faces),'maximumProxyCorrectionMeters':max(corrections),
            'maximumInverseBindCondition':condition,'maximumInfluences':int((actualW>0).sum(1).max()),'weightSumMaxError':float(np.abs(actualW.sum(1,dtype=float)-1).max()),
            'bothOriginalCornerUVLayersExact':True,'newWeights55':True,'oldWeights20Transferred':False,'normalsRegeneratedForChangedBindShape':True})
    # Clinical clothing remains stored, but is not the player's original look.
    for obj in scene.objects:
        if obj.type=='MESH' and (obj.name.startswith(('COAT_','SCRUB_')) or obj.get('V28_original_source_name','').split('.')[0]in ['Tops','Bottoms']):
            obj.hide_render=True;obj.hide_set(True,view_layer=layer)
    scene['PREP_current_outfit']='original shirt/skirt regional-bind PILOT; conservative gaps still pending'
    scene['PREP_default_outfit']='original Thai shirt + black skirt'
    scene['PREP_optional_outfits']='lab coat + school shirt, menu integration pending'
    scene['PREP_role']='Unapproved source-garment refit/bind prototype; not a playable-map scene'
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_ORIGINAL_OUTFIT_BIND_PILOT_V30_20261028.blend';assert not path.exists()
    choose('Idle',1)
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    savedsha=sha(path);scene_name=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scene_name];window.scene=scene;layer=scene.view_layers[0]
    arm=bpy.data.objects['V28_Clinical_Standard_Rig'];garments=[bpy.data.objects[row['object']]for row in rows]
    def points(obj):
        ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v)
        M=np.array(ev.matrix_world,dtype=float);q=v.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
    choose('Idle',1)
    for obj,row in zip(garments,rows):
        q=points(obj);error=float(np.linalg.norm(q-archive[row['piece']+'_fitQ'],axis=1).max());row['freshIdleBindErrorMeters']=error;assert error<2e-5,error
    frames=[]
    for clip,frame in [('Idle',1),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}'
        frame_row={'clip':clip,'frame':frame}
        for obj,row in zip(garments,rows):
            q=points(obj);assert np.isfinite(q).all();archive[label+'_'+row['piece']+'Q']=q
            frame_row[row['piece']+'Bounds']=[q.min(0).tolist(),q.max(0).tolist()]
        ev=arm.evaluated_get(layer.depsgraph);archive[label+'_bonePose55']=np.array([np.array(ev.pose.bones[n].matrix)for n in names]);frames.append(frame_row)
    archive.update(armWorld=A,boneRest55=target['boneRestMatrices'],boneNames=np.array(names),objectWorld=np.eye(4))
    np.savez_compressed(F/'regional_bind_and_reopened_walk_samples.npz',**archive)
    images=[]
    def render(clip,frame,view,direction):
        choose(clip,frame);scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.9;targetpoint=Vector((0,0,.85));camera.location=targetpoint+Vector(direction)*3
        camera.rotation_euler=(targetpoint-camera.location).to_track_quat('-Z','Y').to_euler();output=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(output)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(output)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(output),'sha256':sha(output),'clip':clip,'frame':frame,'view':view})
    for view,direction in [('front',(0,-1,0)),('side',(-1,0,0)),('back',(0,1,0))]:render('Idle',1,view,direction)
    for frame in [1,7,13,19]:render('Walk',frame,'front',(0,-1,0))
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    result={'status':'original-garment-regional-bind-pilot-saved-reopened-awaiting-visual-QA','library':str(path),'sha256':savedsha,
        'scene':scene_name,'checkpoint':str(cp),'checkpointSha256':sha(cp),'sourceLibrary':str(source),'sourceSha256':sha(source),
        'sourceLibraryUnchanged':sha(source)==prior['sha256'],'garments':rows,'frames':frames,'images':images,
        'targetRigArchive':native_report['archive'],'targetRigArchiveSha256':native_report['archiveSha256'],
        'nativeProxyArchive':proxy_report['archive'],'nativeProxyArchiveSha256':proxy_report['archiveSha256'],
        'sourceGarmentReport':str(INPUT/'original_outfit_extraction_report_v30.json'),'sourceGarmentReportSha256':sha(INPUT/'original_outfit_extraction_report_v30.json'),
        'garmentArchive':str(F/'regional_bind_and_reopened_walk_samples.npz'),'garmentArchiveSha256':sha(F/'regional_bind_and_reopened_walk_samples.npz'),
        'oldWeights20Transferred':False,'skirtWeightsLimitedToHipsSpineAndUpperLegs':True,'sourceAtlasAndUVPreserved':True,
        'originalOutfitIsDefaultDirection':True,'clinicalVariantHiddenAndPreserved':True,'labCoatAndSchoolShirtRemainOptional':True,
        'garmentsAreCompleteOrWatertight':False,'appearanceApproved':False,'originalFootwearAdapted':False,'menuChanged':False,
        'GLBExportedOrReimported':False,'runtimeChanged':False,'masterChanged':False,'rigOrNativeActionsEdited':False,
        'MCPAvailable':False,'execution':'Blender hidden background CLI; existing GUI/MCP absent','blenderVersion':bpy.app.version_string,
        'newVisibleWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    assert sha(path)==savedsha
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}));print(json.dumps({k:v for k,v in result.items()if k not in ['images','frames']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
