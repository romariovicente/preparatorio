"""Full-vector local axilla weight repair on copied body; export both native/3deg poses.

Original body/weights, native actions/rest and V35 constraints are preserved.
Final quality is decided only after independent real saved/reopened QA.
"""
import bpy,bmesh,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'work/qa_thai_axilla_full_weights_v38_20261028/axilla_weights_candidate_v38.npz'
F=ROOT/'reports/thai_axilla_weights_v38_20261028';OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_WEIGHTS_V38_20261028.json'
STATUS=ROOT/'work/v38_axilla_weights_status_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p)as f:return {k:f[k].copy()for k in f.files}
try:
    assert I.exists()and not F.exists()and not OUT.exists()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_V38_STAGE_20261028.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working'])and not bpy.data.is_dirty and sha(stage['working'])==stage['workingSha256']
    utility=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));sig=utility['mesh_signature'];actions=utility['action_signatures'];h=utility['helpers']
    assert actions()==stage['actionSignatures'];assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    base_path=ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz';base=load(base_path);payload=load(I)
    assert str(payload['sourceBodyBindSHA256'])==sha(base_path)
    assert np.array_equal(payload['restWorld'],base['restWorld'])and np.array_equal(payload['triangles'],base['triangles'])and np.array_equal(payload['names55'],base['names55'])
    W=payload['weights55Candidate'];changed=payload['changedVertexIndices'].astype(np.int32);editable=payload['editableVertexIndices'].astype(np.int32)
    assert W.shape==base['weights55'].shape and np.isfinite(W).all()and W.min()>=0
    assert np.max((W>0).sum(1))<=4 and np.max(np.abs(W.sum(1,dtype=float)-1))<1e-6
    assert np.array_equal(np.flatnonzero(np.any(W!=base['weights55'],axis=1)),changed)
    outside=np.ones(len(W),bool);outside[editable]=False;assert np.array_equal(W[outside],base['weights55'][outside])
    assert np.isin(changed,editable).all();names=base['names55'].tolist();R=base['boneRest55']
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0];assert scene.name==stage['scene']
    native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']];source=bpy.data.objects[stage['sourceBody']]
    body=source.copy();body.data=source.data.copy();body.name='V38_Complete_Body_Local_Axilla_Weights';body.data.name='V38_Bind_V32_Exact_Local_Axilla_Weights'
    scene.collection.objects.link(body);body.hide_render=False;body.hide_set(False,view_layer=layer);source.hide_render=True;source.hide_set(True,view_layer=layer)
    for name in stage.get('studyBodiesToHide',[]):
        bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True,view_layer=layer)
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();bm.verts.index_update();dw=bm.verts.layers.deform.verify()
    for index in changed:
        v=bm.verts[int(index)];v[dw].clear()
        for j in np.flatnonzero(W[index]>0):v[dw][int(j)]=float(W[index,j])
    bm.to_mesh(body.data);bm.free();body.data.update()
    actual=h['_snapshot'](body.data)['arrays'];actualW=h['_weights'](body.data,55)
    assert np.array_equal(actual['coordinates'],base['restWorld'])and np.array_equal(actual['triangles'],base['triangles'])and np.array_equal(actualW,W)
    modifier=next(m for m in body.modifiers if m.type=='ARMATURE');assert modifier.object==rig
    def choose(clip,frame):
        a=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.data.pose_position='POSE';arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
            for tr in arm.animation_data.nla_tracks:tr.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1);body['PREP_local_axilla_weight_repair_pilot']=True;body['PREP_geometry_rest_exact_against_V32']=True
    scene['PREP_role']='Local axilla weight repair on V35 pose; both native and corrected baselines exported; original clothes pending'
    scene['PREP_appearance_approved']=False
    path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_WEIGHTS_V38_20261028.blend';assert not path.exists();F.mkdir()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    library_sha=sha(path);bodyname=body.name;scenename=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scenename];window.scene=scene;layer=scene.view_layers[0]
    native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']];body=bpy.data.objects[bodyname]
    head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved'];skirt=bpy.data.objects['V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape']
    modifier=next(m for m in body.modifiers if m.type=='ARMATURE')
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p);M=np.array(ev.matrix_world,dtype=float)
        q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    old=load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/live_validation/fresh_live_motion_samples_v32.npz')
    previous=load(ROOT/'reports/thai_pose_clearance_v35_20261028/fresh_live_motion_samples_v35.npz')
    archive={'restWorld':base['restWorld'],'triangles':base['triangles'],'weights55':actualW,'weights55Original':base['weights55'],
        'names55':base['names55'],'boneRest55':R,'armWorld':base['armWorld'],'objectWorld':base['objectWorld'],
        'changedVertexIndices':changed,'editableVertexIndices':editable,'skirtTriangles':h['_snapshot'](skirt.data)['arrays']['triangles']}
    rows=[];images=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}'
        modifier.object=native;body.update_tag();layer.update();qn,Mn=points(body);evn=native.evaluated_get(layer.depsgraph)
        Pn=np.array([np.array(evn.pose.bones[n].matrix,dtype=float)for n in names]);An=np.array(evn.matrix_world,dtype=float)
        modifier.object=rig;body.update_tag();layer.update();q,M=points(body);hq,_=points(head);sq,_=points(skirt);ev=rig.evaluated_get(layer.depsgraph)
        P=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names]);A=np.array(ev.matrix_world,dtype=float)
        errors=[]
        for qq,MM,PP,AA in [(qn,Mn,Pn,An),(q,M,P,A)]:
            D=AA@PP@np.linalg.inv(R)@np.linalg.inv(AA)@MM;blend=np.einsum('vj,jab->vab',actualW,D)
            cpu=np.einsum('vab,vb->va',blend,np.c_[base['restWorld'],np.ones(len(q))])[:,:3];error=float(np.linalg.norm(qq-cpu,axis=1).max());assert error<2e-5;errors.append(error)
        hd=float(np.linalg.norm(hq-old[label+'_headQ'],axis=1).max());assert hd<2e-5
        drift=float(np.linalg.norm(qn-old[label+'_bodyQ'],axis=1).max());assert drift<=.015003
        exterior=float(np.linalg.norm(q[outside]-previous[label+'_bodyQ'][outside],axis=1).max());assert exterior<2e-6
        archive[label+'_nativeBodyQ']=qn;archive[label+'_bodyQ']=q;archive[label+'_headQ']=hq;archive[label+'_skirtQ']=sq
        archive[label+'_nativePose55']=Pn;archive[label+'_pose55']=P;archive[label+'_nativeArmWorld']=An;archive[label+'_armWorld']=A
        archive[label+'_nativeBodyWorld']=Mn;archive[label+'_bodyWorld']=M
        rows.append({'clip':clip,'frame':frame,'nativeCPUErrorMeters':errors[0],'correctedCPUErrorMeters':errors[1],
            'headIdentityDriftMeters':hd,'fullWeightRepairNativeVsOldNativeMaximumMeters':drift,'outsideROIvsV35MaximumMeters':exterior,
            'bodyMinimumZ':float(q[:,2].min()),'fullBodyHeadHeight':float(max(q[:,2].max(),hq[:,2].max())-min(q[:,2].min(),hq[:,2].min()))})
    ar=F/'fresh_live_dual_baselines_v38.npz';np.savez_compressed(ar,**archive)
    gray=bpy.data.materials.new('V38_QA_Gray_Not_Default_Outfit');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    original_material=body.data.materials[0]
    outfits=[o for o in scene.objects if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_'))or o.get('V28_original_source_name','').split('.')[0]=='Shoes']
    visibility={o.name:o.hide_render for o in outfits}
    def render(clip,frame,view,direction,detail=False,diagnostic=True):
        choose(clip,frame);modifier.object=rig;layer.update()
        for o in outfits:o.hide_render=True if diagnostic else visibility[o.name]
        body.data.materials[0]=gray if diagnostic else original_material
        camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.65 if detail else 1.93
        target=Vector((0,0,1.2 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        output=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(output);STATUS.write_text(json.dumps({'status':'rendering','path':str(output)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(output),'sha256':sha(output),'clip':clip,'frame':frame,'view':view,'grayDiagnosticOnly':diagnostic})
    for view,direction in [('gray_front',(0,-1,0)),('gray_side',(-1,0,0)),('gray_back',(0,1,0))]:render('Idle',1,view,direction)
    render('Idle',101,'axilla_detail_front',(0,-1,0),True);render('Walk',19,'axilla_detail_back',(0,1,0),True)
    render('Idle',1,'dressed_front',(0,-1,0),False,False)
    for frame in [1,7,13,19]:render('Walk',frame,'gray_front',(0,-1,0))
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    assert actions()==stage['actionSignatures'];assert all(sig(bpy.data.objects[n])==v for n,v in stage['meshSignatures'].items())
    assert sha(stage['source'])==stage['sourceSha256']and sha(stage['working'])==stage['workingSha256']and sha(path)==library_sha
    r={'status':'local-axilla-weight-candidate-saved-reopened-awaiting-dual-baseline-QA','library':str(path),'sha256':library_sha,'scene':scenename,
        'bodyObject':bodyname,'rig':stage['poseRig'],'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'payload':str(I),'payloadSha256':sha(I),'archive':str(ar),'archiveSha256':sha(ar),'changedVertices':len(changed),'editableVertices':len(editable),
        'sourceMeshAndActionsPreserved':True,'restGeometryAndTopologyPreserved':True,'weightsOutsideROIBitExact':True,
        'bothNativeAnd3DegreeBaselinesExported':True,'samples':rows,'images':images,'appearanceApproved':False,
        'originalOutfitStillUnfinished':True,'coatAndSchoolShirtOptional':True,'constraintsBakedForExport':False,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(r,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in r.items()if k not in ['samples','images']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
