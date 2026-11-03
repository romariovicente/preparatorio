"""Correct RNA matrix array order, after a full 180-component native fixture.

Mathutils uses matrix[row][column]; RNA driver matrix paths resolve column first.
The mathematical transport model and all tolerances remain unchanged.
"""
import bpy,json,hashlib,shutil,math,traceback
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_dynamic_normals_v25_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIX_20261027.json';STATUS=ROOT/'work/v25_rna_matrix_fix_scaled_retry2_status_20261027.json'
SCALE=65536.0
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()and not STATUS.exists()
    original=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_20261027.json').read_text())
    failed=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_PROBES_20261027.json').read_text());assert not failed['all24ProbesPass']
    source=Path(original['library']);assert sha(source)==original['sha256']
    work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIXED_20261027.blend';cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_RNA_FIX_V25_20261027.blend'
    window=bpy.context.window or bpy.context.window_manager.windows[0]
    if not work.exists():
        assert not cp.exists()and Path(bpy.data.filepath)==source and not bpy.data.is_dirty
        shutil.copy2(source,cp)
        with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    else:
        assert Path(bpy.data.filepath)==work and sha(cp)==original['sha256']
        previous_failure=json.loads((ROOT/'work/v25_rna_matrix_fix_status_20261027.json').read_text())
        assert previous_failure['status']=='error'and '9.409884' in previous_failure['error']
        scaled_fixture=json.loads((F/'native_matrix_scaled_value_diagnostic.json').read_text())
        assert scaled_fixture['nativeDriverEncodingScale']==SCALE and all(x['driverVsEvaluatedMax']<1e-7 for x in scaled_fixture['results'])
    arm=bpy.data.objects[original['rig']];scene=bpy.data.scenes[original['scene']];window.scene=scene;layer=scene.view_layers[0];group=bpy.data.node_groups[original['nodeGroup']]
    names=[g.name for g in bpy.data.objects[original['body']].vertex_groups];action=arm.animation_data.action;arm.animation_data.action=None
    saved=[bone.matrix_basis.copy()for bone in arm.pose.bones];root=arm.pose.bones['root'];rest=root.bone.matrix_local.copy();pivot=Vector(root.bone.head_local)
    temporary=[];rows=[];raw_archive={}
    for spec in original['driverNodes']:
        node=group.nodes.new('ShaderNodeValue');node.name='V25_FIXTURE_RAW_'+spec['bone']+'_'+str(spec['row'])+'_'+str(spec['col'])
        driver=node.outputs[0].driver_add('default_value').driver;driver.type='SCRIPTED'
        var=driver.variables.new();var.name='value';var.type='SINGLE_PROP';var.targets[0].id=arm
        var.targets[0].data_path='pose.bones['+json.dumps(spec['bone'])+'].matrix['+str(spec['col'])+']['+str(spec['row'])+']';driver.expression=repr(SCALE)+'*value'
        temporary.append((node,spec))
    try:
        for index,deg in enumerate((0,-5,5,0)):
            for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
            A=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(deg),4,'Z')@Matrix.Translation(-pivot);root.matrix_basis=rest.inverted()@A@rest
            layer.update();scene.frame_set(scene.frame_current);layer.update()
            eval_arm=arm.evaluated_get(layer.depsgraph);expected=np.array([np.array(eval_arm.pose.bones[n].matrix)[:3,:3]for n in names])
            eval_group=group.evaluated_get(layer.depsgraph);actual=np.empty_like(expected)
            for node,spec in temporary:actual[spec['boneIndex'],spec['row'],spec['col']]=eval_group.nodes[node.name].outputs[0].default_value/SCALE
            error=float(abs(actual-expected).max());valid=all(node.outputs[0].id_data.animation_data is not None for node,spec in temporary)
            rows.append({'degrees':deg,'all180RawMatrixComponentMaxError':error,'all180Within1eMinus7':error<1e-7})
            raw_archive['fixture_'+str(index)+'__expectedPoseLinear']=expected;raw_archive['fixture_'+str(index)+'__nativeRNAValues']=actual
    finally:
        for node,spec in temporary:node.outputs[0].driver_remove('default_value');group.nodes.remove(node)
        arm.animation_data.action=action;scene.frame_set(1);layer.update()
    assert all(row['all180Within1eMinus7']for row in rows),rows
    for spec in original['driverNodes']:
        node=group.nodes[spec['node']]
        data_path=node.outputs[0].path_from_id('default_value')
        fc=next(fc for fc in group.animation_data.drivers if fc.data_path==data_path)
        encoded_expression=repr(SCALE)+'*('+spec['expression']+')'
        assert fc.driver.expression in(spec['expression'],encoded_expression)
        for var in fc.driver.variables:
            k=int(var.name[1:]);var.targets[0].data_path='pose.bones['+json.dumps(spec['bone'])+'].matrix['+str(k)+']['+str(spec['row'])+']'
        fc.driver.expression=encoded_expression
        decoder_name='V25_DECODE_'+spec['bone']+'_'+str(spec['row'])+'_'+str(spec['col'])
        decoder=group.nodes.get(decoder_name)or group.nodes.new('ShaderNodeMath');decoder.operation='MULTIPLY';decoder.name=decoder_name;decoder.inputs[1].default_value=1.0/SCALE
        rownode=group.nodes['V25_Matrix_Row_'+spec['bone']+'_'+str(spec['row'])]
        links=list(rownode.inputs[spec['col']].links);assert len(links)==1 and links[0].from_node.name in(node.name,decoder.name)
        group.links.remove(links[0]);group.links.new(node.outputs[0],decoder.inputs[0]);group.links.new(decoder.outputs[0],rownode.inputs[spec['col']])
        spec['decoderNode']=decoder.name;spec['driverEncodingScale']=SCALE
    layer.update();scene.frame_set(1);layer.update()
    eval_arm=arm.evaluated_get(layer.depsgraph);eval_group=group.evaluated_get(layer.depsgraph)
    rest_matrices=np.array([np.array(arm.data.bones[n].matrix_local)for n in names]);pose=np.array([np.array(eval_arm.pose.bones[n].matrix)for n in names]);skin=pose@np.linalg.inv(rest_matrices);coeff=np.empty((20,3,3),float)
    for spec in original['driverNodes']:coeff[spec['boneIndex'],spec['row'],spec['col']]=eval_group.nodes[spec['node']].outputs[0].default_value/SCALE
    corrected_error=float(abs(coeff-skin[:,:3,:3]).max());assert corrected_error<1e-6,corrected_error
    archive=F/'native_rna_column_first_matrix_fixture.npz';np.savez_compressed(archive,**raw_archive)
    fixture={'status':'all180-native-matrix-components-verified-column-first','mathematicalIndex':'poseMatrix[row][column]','nativeRNADriverPath':'pose.bones[name].matrix[column][row]','nativeDriverOutputEncodingScale':SCALE,'encodingReason':'Unscaled native value-driver outputs empirically zeroed small coefficients. Exact power-of-two output encoding and inverse scale in the node field preserve them; no tolerance changed.','rows':rows,'archive':str(archive),'archiveSha256':sha(archive),'all180CorrectedDeformCoefficientsBaselineError':corrected_error,'originalRejectedProbeArchive':failed['archive'],'originalRejectedProbeArchiveSha256':failed['archiveSha256'],'originalFailurePreserved':True,'mathematicalModelOrGatesChanged':False}
    fixture_path=F/'native_rna_column_first_matrix_fixture.json';fixture_path.write_text(json.dumps(fixture,indent=2))
    with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
    assert sha(source)==original['sha256']and sha(cp)==original['sha256']
    result=dict(original);result.update(status='native-RNA-matrix-index-implementation-fixed-pending-full-retest',library=str(work),sha256=sha(work),checkpoint=str(cp),checkpointSha256=sha(cp),rejectedOriginalV25Library=str(source),rejectedOriginalV25Sha256=original['sha256'],rnaMatrixIndexConvention='column-first RNA path; row-first mathutils/numpy',driverOutputEncodingScale=SCALE,rnaFixture=str(fixture_path),rnaFixtureSha256=sha(fixture_path),all180NativeComponentsVerifiedAtFourSignedRootPoses=True,originalRejectedProbeArchivePreserved=True,mathematicalTransportModelAndAllGatesUnchanged=True)
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps({'status':result['status'],'librarySha256':result['sha256'],'rawFixtureRows':rows,'correctedBaselineCoefficientError':corrected_error}))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
