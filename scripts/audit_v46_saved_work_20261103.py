"""Read the preserved later WORK in isolated background Blender. Never save it."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_V46_LATER_WORK_AUDIT_20261103.json'
assert not OUT.exists()
stage_path=ROOT/'reports/CHARACTER_THAI_PHASE1_V46_STAGE_20261029.json'
stage=json.loads(stage_path.read_text())
preserved=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_WORK_V46_PRESERVED_20261103.blend'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected='e07a9cb9eea1918842ed6fb9407ce2979db3085e0ed2c74cdc9c18cdb225d9da'
assert bpy.app.background and Path(bpy.data.filepath)==preserved and sha(preserved)==expected
assert sha(stage['working'])==expected
assert sha(stage['checkpoint'])==stage['checkpointSha256']
assert sha(stage['source'])==stage['sourceSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
mesh_checks={}
for name,reference in stage['meshSignatures'].items():
    obj=bpy.data.objects.get(name)
    if obj is None:
        mesh_checks[name]={'present':False,'exact':False};continue
    current=u['mesh_signature'](obj)
    mesh_checks[name]={'present':True,'exact':current==reference,
      'differentArrays':[k for k in set(current['arrays'])|set(reference['arrays']) if current['arrays'].get(k)!=reference['arrays'].get(k)],
      'groupsExact':current['groups']==reference['groups'],'weightsExact':current['weights']==reference['weights']}
curves=u['action_signatures']()
body=bpy.data.objects[stage['sourceBody']]
scene=bpy.data.scenes.get(stage['scene']) or bpy.context.scene
layer=scene.view_layers[0]
arrays=h['_snapshot'](body.data)['arrays'];weights=h['_weights'](body.data,55)
names=list(body.vertex_groups.keys())
rigs=[bpy.data.objects[stage['nativeRig']],bpy.data.objects[stage['poseRig']]]
native_rest=np.array([np.array(rigs[0].data.bones[n].matrix_local,dtype=float) for n in names])
pose_rest=np.array([np.array(rigs[1].data.bones[n].matrix_local,dtype=float) for n in names])
with np.load(stage['actualSourceArchive']) as z:
    bind={'coordinatesExact':np.array_equal(arrays['coordinates'],z['actualRestWorld']),
      'trianglesExact':np.array_equal(arrays['triangles'],z['actualTriangles']),
      'weights55Exact':np.array_equal(weights,z['actualWeights55']),
      'names55Exact':np.array_equal(np.asarray(names),z['actualNames55']),
      'nativeRestExact':np.array_equal(native_rest,z['actualBoneRest55']),
      'poseRestExact':np.array_equal(pose_rest,z['actualBoneRest55'])}
metadata={'sceneFrame':scene.frame_current,'clip':body.get('PREP_snapshot_clip'),
 'snapshotFrame':body.get('PREP_snapshot_frame'),'branch':body.get('PREP_snapshot_branch'),
 'variant':body.get('PREP_review_variant'),'rigActions':[r.animation_data.action.name if r.animation_data.action else None for r in rigs],
 'rigSlots':[r.animation_data.action_slot.identifier if r.animation_data.action_slot else None for r in rigs],
 'targetArmature':body.modifiers[0].object.name,'GNenabled':body.modifiers[1].show_viewport}
layer.update();ev=body.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
points=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',points)
matrix=np.array(ev.matrix_world,dtype=float);q=points.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3];ev.to_mesh_clear()
key=f"{metadata['clip']}_{metadata['snapshotFrame']}_{metadata['branch']}_{metadata['variant']}Q"
with np.load(stage['sourceV44Cases']) as z:
    if key in z:
        ref=z[key];err=float(np.linalg.norm(q-ref,axis=1).max())
        pose={'referenceKey':key,'referenceAvailable':True,'pointsBitExact':bool(np.array_equal(q,ref)),'maximumDifferenceMeters':err,'within20Microns':err<2e-5}
    else:pose={'referenceKey':key,'referenceAvailable':False,'pointsBitExact':False,'within20Microns':False}
colors=body.data.color_attributes.get('V45_Remaining_Union_Diagnostic_Color')
overlay={}
with np.load(stage['sourceV45Readback']) as z:
    for short in ['Relative','AreaNormal','Fan','Any']:
        attr=body.data.attributes.get('V45_Remaining_'+short)
        values=np.empty(len(body.data.polygons),np.bool_)
        if attr is None:overlay[short]=False
        else:
            attr.data.foreach_get('value',values);overlay[short]=bool(np.array_equal(values,z['actualFace'+short+'Mask']))
    if colors is not None:
        values=np.empty(len(colors.data)*4,np.float32);colors.data.foreach_get('color',values)
        overlay['colorsExact']=bool(np.array_equal(values.reshape(-1,4),z['actualCornerColors']))
    else:overlay['colorsExact']=False
F=ROOT/'reports/v46_later_work_audit_20261103';assert not F.exists();F.mkdir()
ar=F/'read_only_actual_bind_pose.npz'
np.savez_compressed(ar,actualRestWorld=arrays['coordinates'],actualTriangles=arrays['triangles'],actualWeights55=weights,
 actualNames55=np.asarray(names),actualNativeRest55=native_rest,actualPoseRest55=pose_rest,actualCurrentQ=q)
assert sha(preserved)==expected and sha(stage['working'])==expected
passed=all(v['exact'] for v in mesh_checks.values()) and all(bind.values()) and curves==stage['actionSignatures'] and pose['within20Microns']
result={'status':'READ_ONLY_LATER_WORK_CORE_AND_POSE_MATCH' if passed else 'READ_ONLY_DIFFERENCES_REQUIRE_REVIEW',
 'loadedLibrary':str(preserved),'loadedLibrarySHA256':expected,'workingLibrary':stage['working'],'workingLibrarySHA256':sha(stage['working']),
 'initialWorkingSHA256':stage['workingSha256'],'stageReportSHA256':sha(stage_path),'stageFile':str(stage_path),
 'blenderVersion':bpy.app.version_string,'blenderBinary':bpy.app.binary_path,'background':bpy.app.background,
 'autoExecutionDisabled':not bpy.context.preferences.filepaths.use_scripts_auto_execute,
 'autoExecutionFailureReported':bool(bpy.app.autoexec_fail),
 'meshChecks':mesh_checks,'bindChecks':{k:bool(v) for k,v in bind.items()},'actionSignatures':curves,
 'source2200CurvesExact':curves==stage['actionSignatures'],'metadata':metadata,'currentPoseCheck':pose,'overlayChecks':overlay,
 'coreAndCurrentPoseAuditAccepted':bool(passed),'entireFileEqualToOldStage':False,
 'saveCauseDetermined':False,'otherMetadataOrUIChangesExcluded':False,
 'archive':str(ar),'archiveSHA256':sha(ar),'inputFilesUnchanged':True,'fileSavedByThisScript':False,
 'optimizerExecuted':False,'newCorrectionApplied':False,'MCPUsed':False,'BlenderCLIUsed':True,'newVisibleWindowOpened':False,
 'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'report':str(OUT),'status':result['status'],'sourceMeshes':len(mesh_checks),'pose':pose,'blenderVersion':bpy.app.version_string}))
