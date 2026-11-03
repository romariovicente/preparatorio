"""Align four REST bones to frozen artistic scan landmarks, without changing mesh/W."""
import bpy,json,hashlib,shutil,runpy,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_joint_alignment_v26_20261027'
REPORT=ROOT/'reports/CHARACTER_THAI_JOINT_ALIGNMENT_V26_20261027.json';STATUS=ROOT/'work/v26_joint_alignment_build_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not any(p.exists()for p in(F,REPORT,STATUS))
    previous=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIX_20261027.json').read_text())
    source=Path(previous['library']);assert Path(bpy.data.filepath)==source and sha(source)==previous['sha256']and not bpy.data.is_dirty
    proposal=ROOT/'work/qa_thai_joint_alignment_v26_20261027/artistic_knee_pivot_proposal_v26.npz'
    assert sha(proposal)=='4c7351e9b0954559ad46ad0dc305546ee073b012ed322838fbd7fcf3fb39e2ac'
    with np.load(proposal)as n:p={k:n[k].copy()for k in n.files}
    work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_JOINT_ALIGNMENT_V26_20261027.blend';cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_JOINT_ALIGNMENT_V26_20261027.blend'
    assert not work.exists()and not cp.exists();shutil.copy2(source,cp);F.mkdir()
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    source_body=bpy.data.objects[previous['body']];source_arm=bpy.data.objects[previous['rig']];source_group=bpy.data.node_groups[previous['nodeGroup']];source_scene=bpy.data.scenes[previous['scene']]
    helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));body_before=helper['_snapshot'](source_body.data);old_rest=np.array([np.array(source_arm.data.bones[n].matrix_local)for n in p['group_names']])
    old_heads=np.array([list(source_arm.data.bones[n].head_local)for n in p['group_names']]);old_tails=np.array([list(source_arm.data.bones[n].tail_local)for n in p['group_names']])
    def signature(g):return[(fc.data_path,fc.driver.expression,[(v.name,v.targets[0].id.name,v.targets[0].data_path)for v in fc.driver.variables])for fc in g.animation_data.drivers]
    graph_before=signature(source_group)
    scene=bpy.data.scenes.new('REVIEW_THAI_ARTISTIC_JOINT_ALIGNMENT_V26');scene.world=source_scene.world;scene.frame_start=1;scene.frame_end=33
    scene['PREP_role']='Four artistic REST bone pivots aligned to scan; existing posture and W remain unapproved'
    arm=source_arm.copy();arm.data=source_arm.data.copy();arm.animation_data_clear();arm.name='V26_Artistic_Joint_Probe_Rig';scene.collection.objects.link(arm);arm.matrix_world=Matrix.Identity(4)
    names=[g.name for g in source_body.vertex_groups];assert names==p['group_names'].tolist()
    for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    window.scene=scene;layer=scene.view_layers[0];layer.objects.active=arm;arm.select_set(True,view_layer=layer)
    changed=p['changed_bone_indices'].astype(int);assert changed.tolist()==[2,3,5,6]
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer,active_object=arm,object=arm):
        bpy.ops.object.mode_set(mode='EDIT')
        for index,bi in enumerate(changed):
            bone=arm.data.edit_bones[names[bi]];bone.head=Vector(p['proposed_heads_world'][bi]);bone.tail=Vector(p['proposed_tails_world'][bi]);bone.align_roll(Vector(p['new_align_roll_z_world'][index]));bone.use_connect=False
        bpy.ops.object.mode_set(mode='OBJECT')
    for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    heads=np.array([list(arm.data.bones[n].head_local)for n in names]);tails=np.array([list(arm.data.bones[n].tail_local)for n in names]);rest=np.array([np.array(arm.data.bones[n].matrix_local)for n in names]);inverse=np.linalg.inv(rest)
    endpoint_error=float(max(np.linalg.norm(heads-p['proposed_heads_world'],axis=1).max(),np.linalg.norm(tails-p['proposed_tails_world'],axis=1).max()))
    assert endpoint_error<2e-6
    unchanged=np.array([i for i in range(20)if i not in changed]);unchanged_error=float(max(np.linalg.norm(heads[unchanged]-old_heads[unchanged],axis=1).max(),np.linalg.norm(tails[unchanged]-old_tails[unchanged],axis=1).max()))
    assert unchanged_error<2e-6
    for side in('L','R'):
        a,b,c=[names.index(side+'_'+suffix)for suffix in('thigh','shin','foot')]
        assert np.linalg.norm(tails[a]-heads[b])<1e-6 and np.linalg.norm(tails[b]-heads[c])<1e-6
    body=source_body.copy();body.data=source_body.data.copy();body.animation_data_clear();body.name='V26_Joint_Alignment_Normal_Prototype';scene.collection.objects.link(body);body.parent=arm;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
    group=source_group.copy();group.name='V26_CURRENT_REST_DYNAMIC_CORNER_NORMALS'
    assert group.animation_data.as_pointer()!=source_group.animation_data.as_pointer()and len(group.animation_data.drivers)==180
    next(m for m in body.modifiers if m.type=='NODES').node_group=group;next(m for m in body.modifiers if m.type=='ARMATURE').object=arm
    specs=json.loads(json.dumps(previous['driverNodes']))
    for spec in specs:
        node=group.nodes[spec['node']];path=node.outputs[0].path_from_id('default_value');fc=next(fc for fc in group.animation_data.drivers if fc.data_path==path)
        bi=spec['boneIndex'];col=spec['col'];row=spec['row'];physical='+'.join('('+repr(float(inverse[bi,k,col]))+')*p'+str(k)for k in range(3));spec['expression']=physical
        fc.driver.expression='65536.0*('+physical+')'
        for var in fc.driver.variables:
            k=int(var.name[1:]);var.targets[0].id=arm;var.targets[0].data_path='pose.bones['+json.dumps(spec['bone'])+'].matrix['+str(k)+']['+str(row)+']'
    assert signature(source_group)==graph_before
    control=source_body.copy();control.data=source_body.data.copy();control.animation_data_clear();control.name='V26_Legacy_Normal_Geometry_Control';scene.collection.objects.link(control);control.modifiers.clear();control.parent=arm;control.matrix_parent_inverse=Matrix.Identity(4);control.matrix_basis=Matrix.Identity(4)
    mod=control.modifiers.new('Armature_LBS_CONTROL','ARMATURE');mod.object=arm;mod.use_deform_preserve_volume=False;mod.use_vertex_groups=True;mod.use_bone_envelopes=False
    layer.update();control.hide_render=True;control.hide_set(True,view_layer=layer)
    action=source_arm.animation_data.action.copy();action.name='V26_DIAGNOSTIC_NORMAL_PROBES_NOT_WALK';action.use_fake_user=True;arm.animation_data_create();arm.animation_data.action=action;scene.frame_set(1);layer.update()
    assert not helper['_differences'](body_before,helper['_snapshot'](body.data))
    assert not helper['_differences'](body_before,helper['_snapshot'](source_body.data))
    weights=helper['_weights'](body.data,len(names));assert np.array_equal(weights,helper['_weights'](source_body.data,len(names)))
    assert np.array_equal(old_rest,np.array([np.array(source_arm.data.bones[n].matrix_local)for n in names]))
    camera=bpy.data.objects.new('V26_Joint_Alignment_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);camera.matrix_world=source_scene.camera.matrix_world.copy();scene.camera=camera
    for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
    note=bpy.data.texts.new('READ_ME_V26_ARTISTIC_REST_ONLY_NOT_POSTURE_FIX.txt')
    note.write('ARTISTIC REST JOINT ALIGNMENT ONLY\nOnly four REST bones changed to represent the existing scanned knee bends. Body P/W/T/UV and baseline N0 remain unchanged. The guide becomes MORE bent to match the current scan; this is not corrected posture or clinical anatomy. Hip and foot anchors remain fixed.\n\nAll 180 inverse-rest driver expressions were regenerated and target this new rig. The action is diagnostic, not Walk. New pose deformations, including inherited face flips, are not approved as healthy skinning.\n')
    old_plan=json.loads(Path(previous['plan']).read_text());old_plan['jointAlignmentSource']=str(proposal);old_plan['jointAlignmentSha256']=sha(proposal);old_plan['restLengthsIntentionallyChangedNotAnimationStretch']=True
    plan_path=F/'fixed_joint_alignment_normal_plan.json';plan_path.write_text(json.dumps(old_plan,indent=2))
    for obj in scene.objects:obj.select_set(False,view_layer=layer)
    body.select_set(True,view_layer=layer);layer.objects.active=body
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    assert sha(source)==previous['sha256']and sha(cp)==previous['sha256']
    np.savez_compressed(F/'actual_new_rest_joint_export.npz',oldRestMatrices=old_rest,newRestMatrices=rest,oldHeads=old_heads,oldTails=old_tails,newHeads=heads,newTails=tails,changedBoneIndices=changed,groupNames=np.array(names),rawWeights=weights)
    r=dict(previous);r.update(status='artistic-REST-joint-alignment-saved-pending-probes-and-QA',library=str(work),sha256=sha(work),checkpoint=str(cp),checkpointSha256=sha(cp),parentSourceV25=str(source),parentSourceV25Sha256=previous['sha256'],scene=scene.name,body=body.name,rig=arm.name,control=control.name,nodeGroup=group.name,diagnosticAction=action.name,driverNodes=specs,plan=str(plan_path),planSha256=sha(plan_path),artisticJointProposal=str(proposal),artisticJointProposalSha256=sha(proposal),changedRestBoneNames=[names[i]for i in changed],restBoneLengths={n:float(arm.data.bones[n].length)for n in names},maximumEndpointErrorToProposalMeters=endpoint_error,maximumUnchangedBoneEndpointErrorMeters=unchanged_error,allRawMeshWeightsUVNormalsAndFieldsUnchanged=True,all180InverseRestConstantsRegenerated=True,sourceV25InMemoryAndFilePreserved=True,postureFixed=False,healthySkinningApproved=False,nativeWalkValidated=False,runtimeChanged=False,masterChanged=False,scope='Four artistic knee-related REST bones only. Body posture is unchanged; motion validation is limited to normal transport and no animation stretch against the new rest lengths.')
    REPORT.write_text(json.dumps(r,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(REPORT)},indent=2));print(json.dumps({'status':r['status'],'librarySha256':r['sha256'],'endpointError':endpoint_error,'unchangedEndpointError':unchanged_error}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
