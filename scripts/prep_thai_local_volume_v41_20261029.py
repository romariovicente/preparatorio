"""Local dual-quaternion blend study, actual saved/reopened Blender evidence.

Geometry,55 deforming weights and source actions remain exact. Metadata masks
do not correspond to bones. The second Armature reuses the first one's input.
"""
import bpy,bmesh,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'work/probe_thai_local_volume_v41_20261029/local_volume_candidate_v41.npz'
OUT=ROOT/'reports/CHARACTER_THAI_LOCAL_VOLUME_V41_20261029.json'
F=ROOT/'reports/thai_local_volume_v41_20261029'
STATUS=ROOT/'work/v41_local_volume_status_20261029.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    with np.load(p) as z:return {k:z[k].copy() for k in z.files}
try:
    assert PAYLOAD.exists() and not OUT.exists() and not F.exists()
    stage=json.loads((ROOT/'reports/CHARACTER_THAI_LOCAL_VOLUME_V41_STAGE_20261029.json').read_text())
    assert Path(bpy.data.filepath)==Path(stage['working']) and sha(stage['working'])==stage['workingSha256']
    u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
    h=u['helpers'];sig=u['mesh_signature'];actions=u['action_signatures']
    assert actions()==stage['actionSignatures']
    assert all(sig(bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
    base=load(Path(stage['actualSourceArchive']));trial=load(PAYLOAD)
    assert bool(trial['acceptedPose']), 'V41 candidates were all rejected; this prepared integrator was not executed and must not promote them.'
    mask=trial['localMaskBase'].astype(np.float32);selected=float(trial['selectedStrength']);tag=str(trial['selectedTag'])
    assert np.array_equal(trial['strengthValues'],np.array([.25,.5,1.]))
    assert selected in [.25,.5,1.] and tag in ['f025','f050','f100']
    assert mask.shape==(len(base['actualRestWorld']),) and np.isfinite(mask).all() and mask.min()>=0 and mask.max()<=1
    P=base['actualRestWorld'];T=base['actualTriangles'];W=base['actualWeights55']
    names=base['actualNames55'].tolist();R=base['actualBoneRest55'];outside=mask==0
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene;layer=scene.view_layers[0]
    source=bpy.data.objects[stage['sourceBody']];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    body=source.copy();body.data=source.data.copy();body.name='V41_Local_Dual_Quaternion_Volume_Study'
    body.data.name='V41_V40_Exact_Mesh_With_NonBone_Local_DQ_Masks';scene.collection.objects.link(body)
    assert len(body.vertex_groups)==55 and len(body.modifiers)==1
    group=body.vertex_groups.new(name='V41_Local_DQ_Mask')
    assert group.index==55 and rig.data.bones.get(group.name) is None
    groups={name:(group,value) for name,value in [('f025',.25),('f050',.5),('f100',1.)]}
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();bm.verts.index_update();dw=bm.verts.layers.deform.verify()
    for i in np.flatnonzero(mask>0):
        bm.verts[int(i)][dw][group.index]=float(np.float32(mask[i]*selected))
    bm.to_mesh(body.data);bm.free();body.data.update()
    actual=h['_snapshot'](body.data)['arrays'];actualW=h['_weights'](body.data,56)
    assert np.array_equal(actual['coordinates'],P) and np.array_equal(actual['triangles'],T)
    assert np.array_equal(actualW[:,:55],W)
    assert np.array_equal(actualW[:,group.index],np.asarray(mask*selected,dtype=np.float32))
    first=body.modifiers[0];assert first.type=='ARMATURE' and first.object==rig
    first.use_deform_preserve_volume=False;first.vertex_group=''
    second=body.modifiers.new('V41_Local_DQ_Preserve_Volume_Multi','ARMATURE');second.object=rig
    second.use_vertex_groups=True;second.use_bone_envelopes=False
    second.use_multi_modifier=True;second.use_deform_preserve_volume=True;second.vertex_group=groups[tag][0].name
    body.hide_render=False;body.hide_set(False,view_layer=layer)
    source.hide_render=True;source.hide_set(True,view_layer=layer)
    body['PREP_local_volume_study']=True;body['PREP_selected_strength']=selected
    body['PREP_animation_appearance_and_runtime_approved']=False
    body['PREP_source_payload_sha256']=sha(PAYLOAD)
    scene['PREP_role']='Local LBS/DQ blend study. V40 Rest geometry preserved; native actions exact; no runtime approval.'
    def choose(clip,frame):
        action=bpy.data.actions[clip+'.002']
        for arm in [native,rig]:
            arm.animation_data.action=action;arm.animation_data.action_slot=action.slots[0]
            for track in arm.animation_data.nla_tracks:track.mute=True
        scene.frame_set(frame);layer.update()
    choose('Idle',1)
    library=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_LOCAL_VOLUME_V41_PROBE_20261029.blend'
    assert not library.exists();F.mkdir()
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(library),compress=True)
    saved_sha=sha(library);body_name=body.name;scene_name=scene.name
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[scene_name];window.scene=scene;layer=scene.view_layers[0]
    body=bpy.data.objects[body_name];native=bpy.data.objects[stage['nativeRig']];rig=bpy.data.objects[stage['poseRig']]
    first,second=body.modifiers;head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
    group=body.vertex_groups['V41_Local_DQ_Mask']
    groups={name:(group,value) for name,value in [('f025',.25),('f050',.5),('f100',1.)]}
    a=h['_snapshot'](body.data)['arrays'];ww=h['_weights'](body.data,56)
    rr=np.array([np.array(native.data.bones[n].matrix_local,dtype=float) for n in names])
    assert np.array_equal(a['coordinates'],P) and np.array_equal(a['triangles'],T) and np.array_equal(ww[:,:55],W) and np.array_equal(rr,R)
    archive={'actualRestWorld':a['coordinates'],'actualTriangles':a['triangles'],'actualWeights55':ww[:,:55],
        'actualNames55':np.asarray(names),'actualBoneRest55':rr,'actualBodyWorld':np.array(body.matrix_world,dtype=float),
        'localMaskBase':mask,'selectedStrength':np.array(selected),'selectedTag':np.array(tag),'sourceBodyBindSHA256':np.array(stage['actualSourceArchiveSha256'])}
    archive['selected_actualMask']=ww[:,group.index]
    core=np.flatnonzero(mask==1).tolist();transition=np.flatnonzero((mask>0)&(mask<1))
    def set_strength(value):
        group.add(core,value,'REPLACE')
        values=np.asarray(mask*value,dtype=np.float32)
        for index in transition:group.add([int(index)],float(values[index]),'REPLACE')
    def points(o):
        ev=o.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p)
        M=np.array(ev.matrix_world,dtype=float);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q,M
    rows=[]
    for clip,frame in [('Idle',1),('Idle',51),('Idle',101),('Idle',151),('Walk',1),('Walk',7),('Walk',13),('Walk',19)]:
        choose(clip,frame);label=f'{clip}_{frame}';row={'sample':label}
        for branch,arm in [('native',native),('corrected',rig)]:
            first.object=arm;second.object=arm;first.use_deform_preserve_volume=False;second.show_viewport=False;second.show_render=False
            body.update_tag();layer.update();qlbs,M=points(body)
            assert np.linalg.norm(qlbs-base[label+'_'+branch+'BodyQ'],axis=1).max()<2e-6
            arm_ev=arm.evaluated_get(layer.depsgraph);poses=np.array([np.array(arm_ev.pose.bones[n].matrix,dtype=float) for n in names]);A=np.array(arm_ev.matrix_world,dtype=float)
            first.use_deform_preserve_volume=True;body.update_tag();layer.update();qdq,_=points(body)
            first.use_deform_preserve_volume=False;second.show_viewport=True;second.show_render=True
            archive[label+'_'+branch+'Qpre']=qlbs;archive[label+'_'+branch+'Qdq']=qdq
            archive[label+'_'+branch+'Pose55']=poses;archive[label+'_'+branch+'ArmWorld']=A;archive[label+'_'+branch+'BodyWorld']=M
            dq_error=float(np.linalg.norm(qdq-trial[label+'_'+branch+'Qdq'],axis=1).max());assert dq_error<2e-5
            r={'dqCPUErrorMeters':dq_error,'strengths':{}}
            for name,(group,value) in groups.items():
                set_strength(value)
                if name+'_actualMask' not in archive:
                    archive[name+'_actualMask']=h['_weights'](body.data,56)[:,group.index]
                    assert np.array_equal(archive[name+'_actualMask'],np.asarray(mask*value,dtype=np.float32))
                second.vertex_group=group.name;body.update_tag();layer.update();q,_=points(body)
                expected=trial[name+'_'+label+'_'+branch+'Qpost'];error=float(np.linalg.norm(q-expected,axis=1).max())
                assert error<2e-5 and np.array_equal(q[outside],qlbs[outside])
                archive[name+'_'+label+'_'+branch+'Qpost']=q
                r['strengths'][name]={'CPUErrorMeters':error,'outsideMaskDriftMeters':0.,'maximumChangeVsLBSMeters':float(np.linalg.norm(q-qlbs,axis=1).max())}
            row[branch]=r
        hq,_=points(head);assert np.array_equal(hq,base[label+'_headQ'])
        archive[label+'_headQ']=hq;rows.append(row)
        STATUS.write_text(json.dumps({'status':'sampling','sample':label}))
    ar=F/'saved_reopened_local_volume_v41.npz';np.savez_compressed(ar,**archive)
    first.object=rig;second.object=rig;first.use_deform_preserve_volume=False;second.show_viewport=True;second.show_render=True;second.vertex_group=groups[tag][0].name
    set_strength(selected)
    gray=bpy.data.materials.new('V41_QA_Gray_Not_Default_Outfit');gray.use_nodes=True
    next(n for n in gray.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.28,.35,.40,1)
    body.data.materials[0]=gray
    for o in scene.objects:
        if o.name.startswith(('V30_ORIGINAL_','V33_ORIGINAL_')) or o.get('V28_original_source_name','').split('.')[0]=='Shoes':o.hide_render=True
    images=[]
    def render(clip,frame,view,direction,detail=False):
        choose(clip,frame);body.update_tag();layer.update();camera=scene.camera
        camera.data.type='ORTHO';camera.data.ortho_scale=.58 if detail else 1.93
        target=Vector((0,0,1.27 if detail else .84));camera.location=target+Vector(direction)*3
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=720;scene.render.resolution_percentage=100
        scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
        path=F/f'{clip}_{frame}_{view}.png';scene.render.filepath=str(path)
        STATUS.write_text(json.dumps({'status':'rendering','path':str(path)}))
        with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.render.render(write_still=True)
        images.append({'path':str(path),'sha256':sha(path),'diagnosticOnly':True})
    render('Idle',1,'gray_front',(0,-1,0));render('Idle',101,'axilla_front',(0,-1,0),True);render('Walk',19,'axilla_back',(0,1,0),True)
    bpy.ops.wm.open_mainfile(filepath=str(library),load_ui=False,use_scripts=False)
    assert actions()==stage['actionSignatures'] and all(sig(bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
    assert sha(library)==saved_sha and sha(stage['source'])==stage['sourceSha256']
    result={'status':'local-DQ-volume-study-saved-reopened-awaiting-independent-QA','library':str(library),'sha256':saved_sha,
        'scene':scene_name,'bodyObject':body_name,'checkpoint':stage['checkpoint'],'checkpointSha256':stage['checkpointSha256'],
        'payload':str(PAYLOAD),'payloadSha256':sha(PAYLOAD),'archive':str(ar),'archiveSha256':sha(ar),'selectedStrength':selected,
        'selectedTag':tag,'maskVertices':int((mask>0).sum()),'geometryAnd55BoneWeightsPreserved':True,
        'maskGroupsAreMetadataNotBones':True,'sourceMeshesRestAndActionsPreserved':True,'samples':rows,'images':images,
        'animationApproved':False,'appearanceApproved':False,'clothesApproved':False,'GLBExportedOrReimported':False,
        'runtimeChanged':False,'masterChanged':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'ready-for-independent-QA','report':str(OUT)}))
    print(json.dumps({k:v for k,v in result.items() if k not in ['samples','images']}))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
