"""Reopen with scripts disabled; measure 19 direct and 5 native-action probes."""
import bpy,json,hashlib,runpy,math,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_dynamic_normals_v25_20261027'
BUILD=Path(globals().get('V25_BUILD_REPORT',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_20261027.json'))
OUT=Path(globals().get('V25_OUTPUT_REPORT',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_PROBES_20261027.json'))
STATUS=Path(globals().get('V25_STATUS_FILE',ROOT/'work/v25_dynamic_normal_probe_status_20261027.json'))
ARCHIVE_NAME=globals().get('V25_ARCHIVE_NAME','reopened_native_dynamic_normal_probe_archive.npz')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def angle(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64);a=a/np.linalg.norm(a,axis=1)[:,None];b=b/np.linalg.norm(b,axis=1)[:,None]
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.einsum('ij,ij->i',a,b)))
try:
    assert not OUT.exists()and not STATUS.exists()
    r=json.loads(BUILD.read_text());lib=Path(r['library']);plan=json.loads(Path(r['plan']).read_text())
    assert Path(bpy.data.filepath)==lib and sha(lib)==r['sha256']and not bpy.data.is_dirty
    assert sha(r['sourceV23'])==r['sourceV23Sha256']and sha(r['sourceV24'])==r['sourceV24Sha256']
    bpy.ops.wm.open_mainfile(filepath=str(lib),load_ui=False,use_scripts=False)
    window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
    body=bpy.data.objects[r['body']];arm=bpy.data.objects[r['rig']];control=bpy.data.objects[r['control']];group=bpy.data.node_groups[r['nodeGroup']]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    source=bpy.data.objects['V23_UNBOUND_World_Baseline_Source'];source_a=h['_snapshot'](source.data)['arrays'];body_a=h['_snapshot'](body.data)['arrays']
    for k,v in source_a.items():assert np.array_equal(body_a[k],v),k
    with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:e={k:n[k].copy()for k in n.files}
    P=e['posedWorld'];N=e['evaluatedCornerNormalsWorld'];T=e['triangles'];W=e['weights'].astype(float)
    names=[g.name for g in body.vertex_groups];supported=W.sum(1)>1e-12;wn=np.divide(W,W.sum(1)[:,None],out=np.zeros_like(W),where=W.sum(1)[:,None]>1e-12)
    assert np.array_equal(h['_weights'](body.data,len(names)),e['weights'])
    rest=np.array([np.array(arm.data.bones[n].matrix_local)for n in names]);invrest=np.linalg.inv(rest)
    assert np.array_equal(np.array(body.matrix_world),np.eye(4))and np.array_equal(np.array(arm.matrix_world),np.eye(4))
    assert [m.type for m in body.modifiers]==['NODES','ARMATURE']and body.modifiers[1].object is arm
    assert group.nodes[r['normalNode']].mode=='FREE'and group.nodes[r['normalNode']].domain=='CORNER'
    assert len(group.animation_data.drivers)==180
    driver_checks={'allDriversNativeSimpleExpressions':all(fc.driver.is_simple_expression and fc.driver.is_valid for fc in group.animation_data.drivers),'allVariablesSinglePropPoseMatricesOnOwnRig':all(v.type=='SINGLE_PROP'and v.targets[0].id is arm and 'pose.bones['in v.targets[0].data_path and '.matrix['in v.targets[0].data_path for fc in group.animation_data.drivers for v in fc.driver.variables)}
    assert all(driver_checks.values())
    scale=float(r.get('driverOutputEncodingScale',1.0));bindings=[]
    if scale!=1:
        for spec in r['driverNodes']:
            decoder=group.nodes[spec['decoderNode']];rownode=group.nodes['V25_Matrix_Row_'+spec['bone']+'_'+str(spec['row'])]
            assert decoder.operation=='MULTIPLY'and decoder.inputs[1].default_value==1.0/scale
            assert len(decoder.inputs[0].links)==1 and decoder.inputs[0].links[0].from_node.name==spec['node']
            assert len(rownode.inputs[spec['col']].links)==1 and rownode.inputs[spec['col']].links[0].from_node.name==decoder.name
    for spec in r['driverNodes']:
        node=group.nodes[spec['node']];path=node.outputs[0].path_from_id('default_value');fc=next(fc for fc in group.animation_data.drivers if fc.data_path==path)
        bindings.append({'bone':spec['bone'],'boneIndex':spec['boneIndex'],'row':spec['row'],'col':spec['col'],'node':node.name,'expression':fc.driver.expression,'simple':fc.driver.is_simple_expression,'variables':[{'name':v.name,'type':v.type,'targetObject':v.targets[0].id.name,'dataPath':v.targets[0].data_path}for v in fc.driver.variables],'encodingScale':scale,'decoderNode':spec.get('decoderNode')})
    source_sharp=np.zeros(len(source.data.edges),bool);attr=source.data.attributes.get('sharp_edge')
    if attr:attr.data.foreach_get('value',source_sharp)
    def evaluate(obj):
        ev=obj.evaluated_get(layer.depsgraph);m=ev.to_mesh();a=h['_snapshot'](m)['arrays'];M=np.array(ev.matrix_world)
        q=a['coordinates']@M[:3,:3].T+M[:3,3];d=a['cornerNormals'].astype(float)@np.linalg.inv(M[:3,:3]);d/=np.linalg.norm(d,axis=1)[:,None]
        sharp=np.zeros(len(m.edges),bool);at=m.attributes.get('sharp_edge')
        if at:at.data.foreach_get('value',sharp)
        ev.to_mesh_clear();return q,d,a,sharp
    rootrest=arm.data.bones['root'].matrix_local.copy();pivot=Vector(arm.data.bones['root'].head_local)
    def target_bases(poses):
        bases=np.repeat(np.eye(4)[None],len(names),axis=0)
        for name,axis,degrees in poses:
            if axis=='WORLD_Z':
                A=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,'Z')@Matrix.Translation(-pivot);mat=rootrest.inverted()@A@rootrest
            else:mat=Matrix.Rotation(math.radians(degrees),4,axis)
            bases[names.index(name)]=np.array(mat)
        return bases
    tests=[{'label':'baseline','kind':'baseline','poses':[]}]
    tests += [{'label':'rigid_root_Z_'+str(deg),'kind':'rigid','poses':[['root','WORLD_Z',deg]],'degrees':deg}for deg in plan['rigidRootDegrees']]
    tests += [{'label':n+'_'+axis+'_'+str(deg),'kind':'local','poses':[[n,axis,deg]]}for n,axis in plan['localBonesAndAxes']for deg in plan['localDegrees']]
    tests += [{'label':'native_action_frame_'+str(row['frame']),'kind':'action','frame':row['frame'],'poses':row['poses']}for row in plan['actionFrames']]
    action=arm.animation_data.action;assert action.name==r['diagnosticAction'];arm.animation_data.action=None
    control.hide_set(True,view_layer=layer);control.hide_render=True
    results=[];payload={};base_cv=P[T];base_cross=np.cross(base_cv[:,1]-base_cv[:,0],base_cv[:,2]-base_cv[:,0]);base_area=np.linalg.norm(base_cross,axis=1);base_unit=base_cross/np.maximum(base_area[:,None],1e-30)
    for ti,test in enumerate(tests):
        desired=target_bases(test['poses'])
        if test['kind']=='action':
            arm.animation_data.action=action;scene.frame_set(test['frame'])
        else:
            arm.animation_data.action=None
            for i,n in enumerate(names):arm.pose.bones[n].matrix_basis=Matrix(desired[i])
            layer.update();scene.frame_set(scene.frame_current)
        layer.update();arm_eval=arm.evaluated_get(layer.depsgraph)
        matrices=np.array([np.array(arm_eval.pose.bones[n].matrix)for n in names]);bases=np.array([np.array(arm_eval.pose.bones[n].matrix_basis)for n in names]);skin=matrices@invrest
        q,d,a,sharp=evaluate(body);cq,cd,ca,csharp=evaluate(control)
        blend=np.einsum('vg,gij->vij',wn,skin);blend[~supported]=np.eye(4)
        eq=np.einsum('vij,vj->vi',blend[:,:3,:3],P)+blend[:,:3,3]
        en=np.einsum('lij,lj->li',blend[T.reshape(-1),:3,:3],N);en/=np.linalg.norm(en,axis=1)[:,None]
        ne=angle(d,en);gerr=float(np.linalg.norm(q-eq,axis=1).max());controlerr=float(np.linalg.norm(q-cq,axis=1).max())
        evaluated_group=group.evaluated_get(layer.depsgraph);coeff=np.empty((len(names),3,3),float)
        raw_coeff=np.empty_like(coeff)
        for spec in r['driverNodes']:
            raw_coeff[spec['boneIndex'],spec['row'],spec['col']]=evaluated_group.nodes[spec['node']].outputs[0].default_value
            coeff[spec['boneIndex'],spec['row'],spec['col']]=raw_coeff[spec['boneIndex'],spec['row'],spec['col']]/scale
        coefficient_error=float(abs(coeff-skin[:,:3,:3]).max());bases_error=float(abs(bases-desired).max())
        check={'allPointsMatchLBSBelow1um':gerr<1e-6,'allPointsMatchLegacyGeometryControlBelow1um':controlerr<1e-6,'allCornerNormalsMatchFrozenTransportBelowPoint05':bool((ne<.05).all()),'all180NativeDriverCoefficientsMatchEvaluatedPoseBelow1eMinus6':coefficient_error<1e-6,'expectedBoneBasisIncludingActionBelow1eMinus6':bases_error<1e-6,'topologyUVMaterialsSmoothAndSharpExact':bool(all(np.array_equal(a[k],v)for k,v in source_a.items()if k not in('coordinates','cornerNormals'))and np.array_equal(sharp,source_sharp)),'allNormalsFiniteNonzero':bool(np.isfinite(d).all()and(np.linalg.norm(d,axis=1)>0).all())}
        rigid_point=rigid_norm=None
        if test['kind']=='rigid':
            R=np.array(Matrix.Rotation(math.radians(test['degrees']),4,'Z'))[:3,:3];rq=P.copy();rq[supported]=(P[supported]-np.array(pivot))@R.T+np.array(pivot)
            rn=N.copy();mask=supported[T.reshape(-1)];rn[mask]=N[mask]@R.T
            rigid_point=float(np.linalg.norm(q-rq,axis=1).max());rigid_norm=float(angle(d,rn).max());check.update(independentRigidPointOracleBelow1um=rigid_point<1e-6,independentRigidNormalOracleBelowPoint05=rigid_norm<.05)
        if test['kind']=='baseline':check.update(allBaselineWorldPointsBelow1um=float(np.linalg.norm(q-P,axis=1).max())<1e-6,allBaselineCornerNormalsBelowPoint05=float(angle(d,N).max())<.05)
        changed=int((angle(d,N)>.05).sum());expected_changed=int((angle(en,N)>.05).sum());check['normalFieldRespondsWhereModelMoves']=changed>0 if expected_changed>0 else True
        cv=q[T];cross=np.cross(cv[:,1]-cv[:,0],cv[:,2]-cv[:,0]);double_area=np.linalg.norm(cross,axis=1);unit=cross/np.maximum(double_area[:,None],1e-30);valid=base_area>1e-12
        record={'test':test,'checks':check,'allChecksPass':all(check.values()),'maximumPointErrorMeters':gerr,'maximumPointErrorVsGeometryControlMeters':controlerr,'maximumRobustNormalModelErrorDegrees':float(ne.max()),'cornersAtOrAbovePoint05':int((ne>=.05).sum()),'maximumAll180NativeDriverError':coefficient_error,'maximumBoneBasisError':bases_error,'rigidPointOracleErrorMeters':rigid_point,'rigidNormalOracleErrorDegrees':rigid_norm,'normalsChangedAbovePoint05FromBaseline':changed,'modelNormalsChangedAbovePoint05FromBaseline':expected_changed,'inheritedGeometryWarningsNotAnApproval':{'relativeFacesFlippedVsBaseline':int((((unit*base_unit).sum(1)<0)&valid).sum()),'minimumNondegenerateFaceAreaRatio':float((double_area[valid]/base_area[valid]).min()),'maximumNondegenerateFaceAreaRatio':float((double_area[valid]/base_area[valid]).max())}}
        results.append(record);key='test_'+str(ti);payload[key+'__Q']=q;payload[key+'__N']=d;payload[key+'__poseMatrices']=matrices;payload[key+'__poseBases']=bases;payload[key+'__driverCoefficients']=coeff;payload[key+'__rawEncodedNativeValues']=raw_coeff
        if ti==0:
            for k,v in a.items():payload['baseline::'+k]=v
            payload['baseline::sharpEdge']=sharp
        (ROOT/'work/v25_dynamic_normal_probe_progress_20261027.json').write_text(json.dumps({'index':ti,'label':test['label'],'allChecksPass':record['allChecksPass']}))
    arm.animation_data.action=action;scene.frame_set(1);layer.update()
    archive=F/ARCHIVE_NAME;assert not archive.exists()
    normal_attribute=body.data.attributes[r['normalAttribute']];normal_values=np.empty(len(normal_attribute.data)*3,np.float32);normal_attribute.data.foreach_get('vector',normal_values)
    field_weights=[]
    for n in names:
        values=np.empty(len(P),np.float32);body.data.attributes['prep_v25_W_'+n].data.foreach_get('value',values);field_weights.append(values)
    zero_values=np.empty(len(P),np.float32);body.data.attributes['prep_v25_unweighted'].data.foreach_get('value',zero_values)
    payload.update(vertices=P,sourceCornerNormals=N,weights=e['weights'],triangles=T,groupNames=np.array(names),restMatrices=rest,sourceSharpFlags=source_sharp,baselineNormalAttribute=normal_values.reshape(-1,3),dynamicWeightFields=np.array(field_weights).T,unweightedFallbackField=zero_values)
    np.savez_compressed(archive,**payload)
    assert sha(lib)==r['sha256']and sha(r['sourceV23'])==r['sourceV23Sha256']and sha(r['sourceV24'])==r['sourceV24Sha256']
    # Reset all transient pose evaluations to the unchanged saved work session.
    bpy.ops.wm.open_mainfile(filepath=str(lib),load_ui=False,use_scripts=False)
    result={'status':'dynamic-normal-probes-passed-awaiting-independent-qa'if all(x['allChecksPass']for x in results)else'dynamic-normal-probes-rejected','library':str(lib),'sha256':r['sha256'],'buildReport':str(BUILD),'sourceV23Preserved':True,'sourceV24AndCheckpointPreserved':True,'driverChecks':driver_checks,'driverOutputEncodingScale':scale,'driverBindings':bindings,'reopenedWithScriptsDisabled':True,'all24ProbesPass':all(x['allChecksPass']for x in results),'directProbeCount':19,'nativeActionFrameCount':5,'results':results,'archive':str(archive),'archiveSha256':sha(archive),'savedSessionRestoredWithoutSavingProbeChanges':True,'postArmatureNormalOverride':False,'nativeSimpleRNAOnly':True,'inheritedWeightSumGateStillFalse':True,'postureFixed':False,'nativeWalkValidated':False,'healthySkinningApproved':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'scope':'Normal transport only. Existing geometry deformation warnings remain, diagnostic action is not native Walk.'}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','all24ProbesPass':result['all24ProbesPass'],'report':str(OUT)},indent=2));print(json.dumps({'status':result['status'],'all24ProbesPass':result['all24ProbesPass'],'maximumNormalErrorDegrees':max(x['maximumRobustNormalModelErrorDegrees']for x in results),'maximumDriverError':max(x['maximumAll180NativeDriverError']for x in results),'archiveSha256':result['archiveSha256']}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
