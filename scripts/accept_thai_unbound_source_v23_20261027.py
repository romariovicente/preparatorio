"""Seal only the validated static source; never mark its rig or posture fixed."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_rebind_stage_v23_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_ACCEPTANCE_20261027.json'
MAN=F/'evidence_manifest.json'
assert not OUT.exists()and not MAN.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json').read_text())
qa_path=ROOT/'work/qa_thai_rebind_stage_v23_review_20261027/unbound_v23_independent_acceptance.json'
assert sha(qa_path)=='ae29d126b3507582821ee3f187a42a2636d2e4a612ecf8bec3cb114fd5d8d77b'
qa=json.loads(qa_path.read_text())
assert len(qa['checks'])==36 and all(type(v)is bool and v for v in qa['checks'].values())
assert qa['status']=='ACCEPTED_UNBOUND_STATIC_ONLY_BOUND_STAGE_REMAINS_REJECTED'
assert not qa['inheritedGateResults']['allWeightSumsWithin1eMinus7']
assert sha(r['library'])==r['sha256']==qa['librarySHA256']
assert sha(r['source'])==r['sourceSha256']==qa['sourceWORKSHA256']and sha(r['checkpoint'])==r['sourceSha256']
appearance=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_APPEARANCE_20261027.json').read_text())
assert appearance['normalDirectionGatePassed']and appearance['maximumNormalDirectionErrorVsFrozenExportDegrees']<.05
reopen=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_REOPEN_PREVIEW_20261027.json').read_text())
assert len(reopen['images'])==6 and reopen['savedSessionRestoredWithoutSavingPreviewChanges']
for im in reopen['images']:assert sha(im['path'])==im['sha256']
inv=json.loads((F/'local_invariants.json').read_text(encoding='utf-8-sig'))
assert inv['CloudWatcherCount']==0 and not inv['CloudSyncStartupShortcut']and inv['PausedShortcutPresent']
for old,new in((qa_path,F/'independent_unbound_acceptance.json'),(ROOT/'work/qa_thai_rebind_stage_v23_20261027/current_pose_frame_preflight_v23.json',F/'current_pose_frame_preflight.json'),(ROOT/'work/qa_thai_rebind_stage_v23_20261027/normal_node_rna.json',F/'normal_node_rna_read_only.json')):
    assert not new.exists();shutil.copy2(old,new)
result={'status':'accepted-unbound-static-source-only-no-functional-rig-or-posture-approval','library':r['library'],'sha256':r['sha256'],'checkpoint':r['checkpoint'],'checkpointSha256':r['checkpointSha256'],'scene':r['scene'],'body':r['body'],'separateGuide':r['guide'],'independentQAChecks':36,'independentQASHA256':sha(qa_path),'allWorldPositionsExact':True,'maximumRobustWorldNormalDirectionErrorDegrees':appearance['maximumNormalDirectionErrorVsFrozenExportDegrees'],'allUVTopologyWeightsMaterialSmoothAndSharpFlagsPreserved':True,'meshUnboundNoParentModifierActionOrConstraint':True,'guideSnapshotOnly':True,'sixMatchedPreviewsAcceptedAsBaselineOnly':True,'sourceAndCheckpointPreserved':True,'boundStageRemainsRejected':True,'inheritedWeightSumGateStillFalse':True,'postureFixed':False,'weightsRepaired':False,'functionalRigApproved':False,'nativeWalkValidated':False,'runtimeOrMasterIntegration':False,'remoteOperations':False,'MCPUsed':True,'GUIWindowDesktop1ConfirmedWithoutFocusOrMove':True,'scope':'Exact static evaluated surface and separate guide prepared for subsequent rebind study. Not an animated character delivery.'}
OUT.write_text(json.dumps(result,indent=2))
paths=list(F.rglob('*'))+[OUT,ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_20261027.json',ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_REOPEN_PREVIEW_20261027.json',ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_APPEARANCE_20261027.json',ROOT/'scripts/prep_thai_rebind_stage_v23_20261027.py',ROOT/'scripts/finalize_thai_unbound_source_v23_20261027.py',ROOT/'scripts/validate_render_thai_unbound_v23_20261027.py',ROOT/'scripts/measure_thai_unbound_v23_appearance_20261027.py',Path(__file__)]
MAN.write_text(json.dumps({'status':'sealed-local-static-source-evidence','library':r['library'],'librarySHA256':r['sha256'],'files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in paths if p.is_file()]},indent=2))
print(json.dumps(result))
