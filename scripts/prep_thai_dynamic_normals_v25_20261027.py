"""Build a native, pose-dependent normal field before Armature, with no handlers."""
import bpy,json,hashlib,runpy,traceback,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];PRE=ROOT/'work/qa_thai_dynamic_normals_v25_20261027'
F=ROOT/'reports/thai_dynamic_normals_v25_20261027';REPORT=ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_20261027.json';STATUS=ROOT/'work/v25_dynamic_normal_build_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not any(p.exists()for p in(F,REPORT,STATUS))
    pre=json.loads((PRE/'native_pose_matrix_driver_preflight.json').read_text());assert pre['allRowsWithin1eMinus7']
    work=Path(pre['work']);assert Path(bpy.data.filepath)==work and sha(work)==pre['initialWorkSHA256']
    assert sha(pre['sourceV24'])==pre['sourceV24SHA256']and sha(pre['checkpoint'])==pre['sourceV24SHA256']
    # Drop only the temporary preflight node/driver session, never old source art.
    bpy.ops.wm.open_mainfile(filepath=str(work),load_ui=False,use_scripts=False)
    previous=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json').read_text())
    assert sha(previous['library'])==previous['sha256']
    source=bpy.data.objects[previous['body']];guide=bpy.data.objects[previous['guide']];source_scene=bpy.data.scenes[previous['scene']]
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));snap=h['_snapshot'](source.data)
    with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:e={k:n[k].copy()for k in n.files}
    W=e['weights'].astype(float);sums=W.sum(1);supported=sums>1e-12;wn=np.divide(W,sums[:,None],out=np.zeros_like(W),where=sums[:,None]>1e-12)
    names=[g.name for g in source.vertex_groups]
    F.mkdir()
    local_bones=[['L_shin','X'],['R_shin','X'],['L_thigh','X'],['R_thigh','X'],['L_upper_arm','X'],['R_upper_arm','X'],['chest','X'],['head','Y']]
    action_frames=[{'frame':1,'poses':[]},{'frame':9,'poses':[['L_shin','X',5],['head','Y',5]]},{'frame':17,'poses':[['R_thigh','X',-5],['chest','X',5]]},{'frame':25,'poses':[['root','WORLD_Z',5],['L_upper_arm','X',-5],['R_shin','X',5]]},{'frame':33,'poses':[]}]
    plan={'status':'frozen-before-dynamic-field-build','architecture':'Pose-dependent FREE CORNER normal field BEFORE Armature. No post-Armature normal override, Python driver namespace or frame handler.','normalModel':'normalize(sum(normalized original vertex weights * ((actual evaluated poseBoneMatrix @ inverse(restBoneMatrix))[:3,:3] @ frozen baseline corner normal)))','weightZeroFallback':'N0 for unsupported vertices; no change to raw stored deform weights','driverCount':len(names)*9,'driverFormula':'three SINGLE_PROP native pose-matrix RNA components per output coefficient, multiplied by frozen inverse-rest constants; simple numeric expressions only','rigidRootDegrees':[-5,5],'localBonesAndAxes':local_bones,'localDegrees':[-5,5],'actionFrames':action_frames,'gates':{'allWorldPointErrorMetersStrict':1e-6,'allWorldNormalDirectionErrorDegreesStrict':.05,'all180DriverCoefficientErrorStrict':1e-6,'rawTopologyUVWeightsMaterialsSmoothSharp':'bit exact','geometry':'match legacy Armature control and independently computed normalized LBS','world':'body and rig identity'},'notApproved':['posture','healthy weights','native Walk','clinical anatomy','complete clothing','game integration']}
    (F/'fixed_dynamic_normal_plan.json').write_text(json.dumps(plan,indent=2))
    scene=bpy.data.scenes.new('REVIEW_THAI_DYNAMIC_NORMALS_V25');scene.world=source_scene.world;scene.frame_start=1;scene.frame_end=33
    scene['PREP_role']='Dynamic normal-transport prototype only. Underlying old posture and W remain unapproved.'
    arm=guide.copy();arm.data=guide.data.copy();arm.animation_data_clear();arm.name='V25_Dynamic_Normal_Probe_Rig';scene.collection.objects.link(arm);arm.matrix_world=Matrix.Identity(4)
    for bone in arm.pose.bones:bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
    body=source.copy();body.data=source.data.copy();body.animation_data_clear();body.name='V25_Dynamic_Normal_Transport_Prototype';scene.collection.objects.link(body)
    body.parent=arm;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
    normal_attr=body.data.attributes.new('prep_v25_baseline_normal','FLOAT_VECTOR','CORNER');normal_attr.data.foreach_set('vector',e['evaluatedCornerNormalsWorld'].astype(np.float32).reshape(-1))
    attr=body.data.attributes.new('prep_v25_unweighted','FLOAT','POINT');attr.data.foreach_set('value',(~supported).astype(np.float32))
    for i,n in enumerate(names):
        a=body.data.attributes.new('prep_v25_W_'+n,'FLOAT','POINT');a.data.foreach_set('value',wn[:,i].astype(np.float32))
    group=bpy.data.node_groups.new('V25_NATIVE_DYNAMIC_CORNER_NORMALS','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    ni=group.nodes.new('NodeGroupInput');no=group.nodes.new('NodeGroupOutput')
    def attribute(name,dtype,stype):
        node=group.nodes.new('GeometryNodeInputNamedAttribute');node.data_type=dtype;node.inputs['Name'].default_value=name
        return next(s for s in node.outputs if s.name=='Attribute'and s.type==stype)
    N=attribute(normal_attr.name,'FLOAT_VECTOR','VECTOR');zero=attribute('prep_v25_unweighted','FLOAT','VALUE')
    initial=group.nodes.new('ShaderNodeVectorMath');initial.operation='SCALE';group.links.new(N,initial.inputs[0]);group.links.new(zero,initial.inputs['Scale']);acc=initial.outputs['Vector']
    rest=np.array([np.array(arm.data.bones[n].matrix_local)for n in names]);inverse=np.linalg.inv(rest);driver_nodes=[]
    for bi,n in enumerate(names):
        combined=group.nodes.new('ShaderNodeCombineXYZ');combined.name='V25_Transported_'+n
        for row in range(3):
            rownode=group.nodes.new('ShaderNodeCombineXYZ');rownode.name='V25_Matrix_Row_'+n+'_'+str(row)
            for col in range(3):
                node=group.nodes.new('ShaderNodeValue');node.name='V25_M_'+n+'_'+str(row)+'_'+str(col)
                fc=node.outputs[0].driver_add('default_value');drv=fc.driver;drv.type='SCRIPTED'
                for k in range(3):
                    var=drv.variables.new();var.name='p'+str(k);var.type='SINGLE_PROP';var.targets[0].id=arm;var.targets[0].data_path='pose.bones['+json.dumps(n)+'].matrix['+str(row)+']['+str(k)+']'
                drv.expression='+'.join('('+repr(float(inverse[bi,k,col]))+')*p'+str(k)for k in range(3))
                group.links.new(node.outputs[0],rownode.inputs[col]);driver_nodes.append({'boneIndex':bi,'bone':n,'row':row,'col':col,'node':node.name,'expression':drv.expression})
            dot=group.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';group.links.new(rownode.outputs[0],dot.inputs[0]);group.links.new(N,dot.inputs[1]);group.links.new(dot.outputs['Value'],combined.inputs[row])
        weighted=group.nodes.new('ShaderNodeVectorMath');weighted.operation='SCALE';group.links.new(combined.outputs[0],weighted.inputs[0]);group.links.new(attribute('prep_v25_W_'+n,'FLOAT','VALUE'),weighted.inputs['Scale'])
        add=group.nodes.new('ShaderNodeVectorMath');add.operation='ADD';group.links.new(acc,add.inputs[0]);group.links.new(weighted.outputs['Vector'],add.inputs[1]);acc=add.outputs['Vector']
    normalize=group.nodes.new('ShaderNodeVectorMath');normalize.operation='NORMALIZE';group.links.new(acc,normalize.inputs[0])
    setn=group.nodes.new('GeometryNodeSetMeshNormal');setn.mode='FREE';setn.domain='CORNER';setn.name='V25_Set_Dynamic_Normal_BEFORE_Armature'
    group.links.new(ni.outputs['Geometry'],setn.inputs['Mesh']);group.links.new(normalize.outputs['Vector'],setn.inputs['Custom Normal']);group.links.new(setn.outputs['Mesh'],no.inputs['Geometry'])
    gn=body.modifiers.new('01_Pose_Dependent_Corner_Normal','NODES');gn.node_group=group
    mod=body.modifiers.new('02_Armature_Linear_Blend','ARMATURE');mod.object=arm;mod.use_deform_preserve_volume=False;mod.use_vertex_groups=True;mod.use_bone_envelopes=False
    control=source.copy();control.data=source.data.copy();control.animation_data_clear();control.name='V25_Legacy_Normal_Geometry_Control';scene.collection.objects.link(control);control.parent=arm;control.matrix_parent_inverse=Matrix.Identity(4);control.matrix_basis=Matrix.Identity(4)
    cm=control.modifiers.new('Armature_LBS_CONTROL','ARMATURE');cm.object=arm;cm.use_deform_preserve_volume=False;cm.use_vertex_groups=True;cm.use_bone_envelopes=False
    window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0];layer.update();control.hide_render=True;control.hide_set(True,view_layer=layer)
    root=arm.pose.bones['root'];rootrest=root.bone.matrix_local.copy();pivot=Vector(root.bone.head_local)
    for sample in action_frames:
        for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
        for name,axis,degrees in sample['poses']:
            if axis=='WORLD_Z':
                A=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,'Z')@Matrix.Translation(-pivot);arm.pose.bones[name].matrix_basis=rootrest.inverted()@A@rootrest
            else:arm.pose.bones[name].matrix_basis=Matrix.Rotation(math.radians(degrees),4,axis)
        for bone in arm.pose.bones:
            for path in('location','rotation_quaternion','scale'):bone.keyframe_insert(data_path=path,frame=sample['frame'],group=bone.name)
    action=arm.animation_data.action;action.name='V25_DIAGNOSTIC_NORMAL_PROBES_NOT_WALK';action.use_fake_user=True
    scene.frame_set(1);layer.update()
    camera=bpy.data.objects.new('V25_Normal_Test_Camera',source_scene.camera.data.copy());scene.collection.objects.link(camera);camera.matrix_world=source_scene.camera.matrix_world.copy();scene.camera=camera
    for light in(o for o in source_scene.objects if o.type=='LIGHT'):scene.collection.objects.link(light)
    note=bpy.data.texts.new('READ_ME_V25_DYNAMIC_NORMAL_PROTOTYPE_NOT_WALK.txt')
    note.write('DYNAMIC NORMAL TRANSPORT PROTOTYPE — PENDING QA\n\nThe CORNER normal field is computed from native pose-matrix drivers, normalized original weights and frozen baseline normals, BEFORE Armature. No static normal override follows deformation. No Python callback, frame handler or custom driver function is required.\n\nThe attached 5-keyframe action is DIAGNOSTIC_NORMAL_PROBES_NOT_WALK. The existing asymmetric scan, old weights, posture and incomplete clothing remain. This does not approve skin health, native Walk or game integration.\n')
    assert not h['_differences'](snap,h['_snapshot'](source.data))and np.array_equal(h['_weights'](source.data,len(source.vertex_groups)),e['weights'])
    assert np.array_equal(h['_weights'](body.data,len(body.vertex_groups)),e['weights'])
    for obj in scene.objects:obj.select_set(False,view_layer=layer)
    body.select_set(True,view_layer=layer);layer.objects.active=body
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    assert sha(previous['library'])==previous['sha256']and sha(pre['sourceV24'])==pre['sourceV24SHA256']
    result={'status':'dynamic-native-normal-field-built-pending-reopen-and-probes','library':str(work),'sha256':sha(work),'checkpoint':pre['checkpoint'],'checkpointSha256':pre['checkpointSHA256'],'sourceV24':pre['sourceV24'],'sourceV24Sha256':pre['sourceV24SHA256'],'sourceV23':previous['library'],'sourceV23Sha256':previous['sha256'],'scene':scene.name,'body':body.name,'rig':arm.name,'control':control.name,'nodeGroup':group.name,'normalNode':setn.name,'normalAttribute':normal_attr.name,'driverNodes':driver_nodes,'driverCount':len(driver_nodes),'diagnosticAction':action.name,'diagnosticActionFrames':action_frames,'modifierOrder':[m.type for m in body.modifiers],'normalNodeBeforeArmature':True,'postArmatureNormalOverride':False,'usesCustomPythonDriverNamespaceOrHandlers':False,'plan':str(F/'fixed_dynamic_normal_plan.json'),'planSha256':sha(F/'fixed_dynamic_normal_plan.json'),'sourceAndReferenceWeightsUnchanged':True,'inheritedWeightSumGateStillFalse':True,'postureFixed':False,'nativeWalkValidated':False,'healthySkinningApproved':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}
    REPORT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(REPORT)},indent=2));print(json.dumps({'status':result['status'],'librarySha256':result['sha256'],'driverCount':len(driver_nodes)}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
