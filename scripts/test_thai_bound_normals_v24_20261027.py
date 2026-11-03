"""Compare two native normal representations BEFORE Armature deformation.

The experiment plan and transport model were frozen before this script ran.
No normal field is inserted after Armature. Existing W remains unapproved.
"""
import bpy,json,hashlib,runpy,traceback,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_bound_normals_v24_20261027'
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BOUND_NORMALS_V24_WORK_20261027.blend'
REPORT=ROOT/'reports/CHARACTER_THAI_BOUND_NORMALS_V24_20261027.json'
STATUS=ROOT/'work/v24_bound_normal_experiment_retry2_status_20261027.json'
PRE=ROOT/'work/qa_thai_bound_normals_v24_20261027'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def directions(a,b):
    a=a.astype(np.float64);b=b.astype(np.float64)
    a/=np.linalg.norm(a,axis=1)[:,None];b/=np.linalg.norm(b,axis=1)[:,None]
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.einsum('ij,ij->i',a,b)))
try:
    assert not REPORT.exists()and not STATUS.exists()and Path(bpy.data.filepath)==WORK
    setup=json.loads((PRE/'native_node_sockets.json').read_text());plan=json.loads((PRE/'root_experiment_plan.json').read_text())
    assert sha(WORK)==setup['initialWorkSHA256']and sha(plan['source'])==plan['sourceSHA256']and sha(plan['checkpoint'])==plan['sourceSHA256']
    if F.exists():
        # Previous setup stopped before any probe at hide_set's missing layer.
        # Reload only our exact initial WORK copy, discarding that unsaved setup.
        failure=json.loads((ROOT/'work/v24_bound_normal_experiment_status_20261027.json').read_text())
        assert failure['status']=='error'and 'cannot be hidden' in failure['error']
        assert {p.name for p in F.iterdir()}=={'fixed_experiment_plan.json'}
        assert json.loads((F/'fixed_experiment_plan.json').read_text())==plan
        bpy.ops.wm.open_mainfile(filepath=str(WORK),load_ui=False,use_scripts=False)
    else:F.mkdir()
    (F/'fixed_experiment_plan.json').write_text(json.dumps(plan,indent=2))
    previous=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json').read_text())
    source=bpy.data.objects[previous['body']];source_guide=bpy.data.objects[previous['guide']];source_scene=bpy.data.scenes[previous['scene']]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    source_snap=h['_snapshot'](source.data);source_w=h['_weights'](source.data,len(source.vertex_groups))
    assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in source_snap['arrays'].items()}==previous['bodyArraysSha256']
    with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:e={k:n[k].copy()for k in n.files}
    P=e['posedWorld'];N=e['evaluatedCornerNormalsWorld'];T=e['triangles'];W=e['weights'].astype(float)
    names=[g.name for g in source.vertex_groups];sums=W.sum(1);supported=sums>1e-12;wn=np.divide(W,sums[:,None],out=np.zeros_like(W),where=sums[:,None]>1e-12)
    scene=bpy.data.scenes.new('REVIEW_THAI_BOUND_NORMALS_V24_PROTOTYPE');scene.world=source_scene.world
    scene['PREP_role']='Normal representation experiment only; no repaired posture, W health or native Walk approval'
    arm=source_guide.copy();arm.data=source_guide.data.copy();arm.animation_data_clear();arm.name='V24_Normal_Test_Rig';scene.collection.objects.link(arm);arm.matrix_world=Matrix.Identity(4)
    body=source.copy();body.data=source.data.copy();body.name='V24_Normal_Transport_Prototype';body.animation_data_clear();scene.collection.objects.link(body)
    body.parent=arm;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
    attr=body.data.attributes.new('prep_v24_baseline_world_normal','FLOAT_VECTOR','CORNER');attr.data.foreach_set('vector',N.astype(np.float32).reshape(-1))
    group=bpy.data.node_groups.new('V24_CORNER_NORMAL_BEFORE_ARMATURE','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    ni=group.nodes.new('NodeGroupInput');no=group.nodes.new('NodeGroupOutput');sn=group.nodes.new('GeometryNodeSetMeshNormal');sn.mode='FREE';sn.domain='CORNER'
    named=group.nodes.new('GeometryNodeInputNamedAttribute');named.data_type='FLOAT_VECTOR';named.inputs['Name'].default_value=attr.name
    group.links.new(ni.outputs['Geometry'],sn.inputs['Mesh']);group.links.new(named.outputs['Attribute'],sn.inputs['Custom Normal']);group.links.new(sn.outputs['Mesh'],no.inputs['Geometry'])
    gn=body.modifiers.new('01_Native_Corner_Normal_Field','NODES');gn.node_group=group
    deform=body.modifiers.new('02_Armature_LBS','ARMATURE');deform.object=arm;deform.use_deform_preserve_volume=False;deform.use_vertex_groups=True;deform.use_bone_envelopes=False
    control=source.copy();control.data=source.data.copy();control.name='V24_Legacy_Normal_Geometry_Control';scene.collection.objects.link(control);control.parent=arm;control.matrix_parent_inverse=Matrix.Identity(4);control.matrix_basis=Matrix.Identity(4)
    cm=control.modifiers.new('Armature_LBS_CONTROL','ARMATURE');cm.object=arm;cm.use_deform_preserve_volume=False;cm.use_vertex_groups=True;cm.use_bone_envelopes=False
    window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0];layer.update()
    control.hide_render=True;control.hide_set(True,view_layer=layer)
    def evaluated(obj):
        layer.update();ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh();a=h['_snapshot'](m)['arrays'];M=np.array(ev.matrix_world)
        q=a['coordinates']@M[:3,:3].T+M[:3,3];d=a['cornerNormals'].astype(float)@np.linalg.inv(M[:3,:3]);d/=np.linalg.norm(d,axis=1)[:,None]
        sharp=m.attributes.get('sharp_edge');flags=np.zeros(len(m.edges),bool)
        if sharp:sharp.data.foreach_get('value',flags)
        ev.to_mesh_clear();return q,d,a,flags
    def reset():
        for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
        layer.update()
    rest=np.array([np.array(arm.data.bones[n].matrix_local)for n in names]);invrest=np.linalg.inv(rest)
    sharp=source.data.attributes.get('sharp_edge');source_sharp=np.zeros(len(source.data.edges),bool)
    if sharp:sharp.data.foreach_get('value',source_sharp)
    source_normal_masks=supported[T.reshape(-1)]
    poses=[{'label':'baseline','kind':'baseline','degrees':0}]
    poses += [{'label':'rigid_root_Z_'+str(deg),'kind':'rigid','degrees':deg}for deg in plan['rigidRootWorldZDegrees']]
    poses += [{'label':bone+'_'+axis+'_'+str(deg),'kind':'local','bone':bone,'axis':axis,'degrees':deg}for bone,axis in plan['localProbeBonesAndAxes']for deg in plan['localDegrees']]
    all_results=[];payload={};mode_summaries=[]
    for mode in plan['modes']:
        sn.mode=mode;sn.domain='CORNER';reset()
        mode_results=[]
        for pi,pose in enumerate(poses):
            reset();expected_rigid_q=None;expected_rigid_n=None
            if pose['kind']=='rigid':
                root_index=names.index('root');pivot=Vector(arm.data.bones['root'].head_local)
                R=Matrix.Rotation(math.radians(pose['degrees']),4,'Z');A=Matrix.Translation(pivot)@R@Matrix.Translation(-pivot)
                arm.pose.bones['root'].matrix_basis=arm.data.bones['root'].matrix_local.inverted()@A@arm.data.bones['root'].matrix_local
                expected_rigid_q=P.copy();expected_rigid_q[supported]=(P[supported]-np.array(pivot))@np.array(R)[:3,:3].T+np.array(pivot)
                expected_rigid_n=N.copy();expected_rigid_n[source_normal_masks]=N[source_normal_masks]@np.array(R)[:3,:3].T
            elif pose['kind']=='local':arm.pose.bones[pose['bone']].matrix_basis=Matrix.Rotation(math.radians(pose['degrees']),4,pose['axis'])
            layer.update();q,d,a,flags=evaluated(body);cq,cd,ca,cflags=evaluated(control)
            skin=np.array([np.array(arm.pose.bones[n].matrix)for n in names])@invrest
            blended=np.einsum('vg,gij->vij',wn,skin)
            blended[~supported]=np.eye(4)
            expected_q=np.einsum('vij,vj->vi',blended[:,:3,:3],P)+blended[:,:3,3]
            linear=blended[T.reshape(-1),:3,:3]
            ref_n=np.einsum('lij,lj->li',linear,N);ref_n/=np.linalg.norm(ref_n,axis=1)[:,None]
            normal_model_error=directions(d,ref_n)
            geometry_control=float(np.linalg.norm(q-cq,axis=1).max());geometry_lbs=float(np.linalg.norm(q-expected_q,axis=1).max())
            uv_topology_material_smooth=all(np.array_equal(a[k],v)for k,v in source_snap['arrays'].items()if k not in('coordinates','cornerNormals'))
            base_error=float(np.linalg.norm(q-P,axis=1).max())if pose['kind']=='baseline'else None
            base_n=float(directions(d,N).max())if pose['kind']=='baseline'else None
            rigid_q=float(np.linalg.norm(q-expected_rigid_q,axis=1).max())if expected_rigid_q is not None else None
            rigid_n=float(directions(d,expected_rigid_n).max())if expected_rigid_n is not None else None
            checks={'topologyUVMaterialsSmoothAndSharpExact':bool(uv_topology_material_smooth and np.array_equal(flags,source_sharp)),'geometryMatchesLegacyControlBelow1um':geometry_control<1e-6,'geometryMatchesFrozenLBSModelBelow1um':geometry_lbs<1e-6,'allNormalVectorsFinite':bool(np.isfinite(d).all()),'normalTransportMatchesFrozenDirectBlendModelBelowPoint05':bool((normal_model_error<.05).all())}
            if base_error is not None:checks.update(baselineAllPointsBelow1um=base_error<1e-6,baselineAllCornerNormalsBelowPoint05=base_n<.05)
            if rigid_q is not None:checks.update(rigidOracleAllPointsBelow1um=rigid_q<1e-6,rigidOracleAllCornerNormalsBelowPoint05=rigid_n<.05)
            record={'mode':mode,'pose':pose,'checks':checks,'allChecksPass':all(checks.values()),'maximumPointErrorVsControlMeters':geometry_control,'maximumPointErrorVsLBSModelMeters':geometry_lbs,'maximumWorldNormalErrorVsFrozenDirectBlendModelDegrees':float(normal_model_error.max()),'cornersOverPoint05VsFrozenDirectBlendModel':int((normal_model_error>=.05).sum()),'baselinePointErrorMeters':base_error,'baselineNormalErrorDegrees':base_n,'rigidOraclePointErrorMeters':rigid_q,'rigidOracleNormalErrorDegrees':rigid_n}
            mode_results.append(record);all_results.append(record)
            key=mode+'__'+str(pi);payload[key+'__Q']=q;payload[key+'__N']=d;payload[key+'__skinMatrices']=skin
            if pose['kind']=='baseline':
                for k,v in a.items():payload[mode+'__baseline::'+k]=v
                payload[mode+'__baseline::sharpEdge']=flags
            (ROOT/'work/v24_normal_probe_progress_20261027.json').write_text(json.dumps({'mode':mode,'pose':pose['label']}))
        mode_summaries.append({'mode':mode,'all'+str(len(poses))+'ProbesPass':all(row['allChecksPass']for row in mode_results),'baselinePass':mode_results[0]['allChecksPass'],'maximumNormalTransportErrorDegrees':max(row['maximumWorldNormalErrorVsFrozenDirectBlendModelDegrees']for row in mode_results)})
    reset()
    passing=[summary['mode']for summary in mode_summaries if list(summary.values())[1]]
    selected=passing[0]if passing else None
    if selected:sn.mode=selected;body['PREP_acceptance_scope']='Baseline plus fixed normal transport probes only; no healthy W, posture or native Walk approval'
    else:sn.mode='FREE';body['PREP_acceptance_scope']='REJECTED_ALL_NORMAL_MODES; do not integrate'
    body['PREP_selected_normal_mode']=selected or 'NONE';body['PREP_old_weight_sum_gate_passed']=False
    control.hide_set(True,view_layer=layer);control.hide_render=True
    camera=bpy.data.objects.new('V24_Normal_Test_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);camera.matrix_world=source_scene.camera.matrix_world.copy();scene.camera=camera
    for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
    note=bpy.data.texts.new('READ_ME_V24_NORMAL_TRANSPORT_PROTOTYPE_ONLY.txt')
    note.write('NORMAL REPRESENTATION PROTOTYPE ONLY\nSetMeshNormal reads the baseline CORNER field BEFORE Armature. No static normal override exists after deformation. Selected mode: '+str(selected)+'\n\nFixed baseline, rigid-root and local bone probes are numerical transport tests, NOT native Walk, correct posture, healthy weights, complete clothing or clinical anatomy approval. Old W is unchanged and its inherited sum precision gate remains false. Source V23 and checkpoint are intact. Do not integrate into the game before separate acceptance.\n')
    assert not h['_differences'](source_snap,h['_snapshot'](source.data))and np.array_equal(h['_weights'](source.data,len(source.vertex_groups)),source_w)
    for obj in scene.objects:obj.select_set(False,view_layer=layer)
    body.select_set(True,view_layer=layer);layer.objects.active=body
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
    payload.update(vertices=P,sourceCornerNormals=N,triangles=T,weights=e['weights'],groupNames=np.array(names),restMatrices=rest,sourceSharpFlags=source_sharp)
    archive=F/'two_mode_normal_transport_probe_archive.npz';np.savez_compressed(archive,**payload)
    assert sha(plan['source'])==plan['sourceSHA256']and sha(plan['checkpoint'])==plan['sourceSHA256']
    result={'status':'normal-modes-tested-awaiting-independent-qa','library':str(WORK),'sha256':sha(WORK),'source':plan['source'],'sourceSha256':plan['sourceSHA256'],'checkpoint':plan['checkpoint'],'checkpointSha256':sha(plan['checkpoint']),'scene':scene.name,'body':body.name,'rig':arm.name,'control':control.name,'nodeGroup':group.name,'normalNode':sn.name,'normalAttribute':attr.name,'modifierOrder':[m.type for m in body.modifiers],'normalNodeBeforeArmature':True,'postArmatureNormalOverride':False,'planSha256':sha(PRE/'root_experiment_plan.json'),'probesPerMode':len(poses),'modeSummaries':mode_summaries,'selectedMode':selected,'results':all_results,'archive':str(archive),'archiveSha256':sha(archive),'sourceAtomsAndFilesPreserved':True,'sourceWeightsUnchanged':True,'inheritedWeightSumGateStillFalse':True,'postureFixed':False,'nativeWalkValidated':False,'healthySkinningApproved':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'scope':'Native normal representation prototype with frozen vector transport probes. Does not correct the underlying scan, posture, clothing or weights.'}
    REPORT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','selectedMode':selected,'report':str(REPORT)},indent=2));print(json.dumps({'status':result['status'],'modeSummaries':mode_summaries,'selectedMode':selected,'librarySHA256':result['sha256'],'archiveSHA256':result['archiveSha256']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
