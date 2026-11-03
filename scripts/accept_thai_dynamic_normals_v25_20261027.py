"""Seal the limited normal-transport milestone, never posture or runtime skinning."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_dynamic_normals_v25_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_ACCEPTANCE_20261027.json';MAN=F/'evidence_manifest.json'
assert not OUT.exists()and not MAN.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
build=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIX_20261027.json').read_text())
probes=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIXED_PROBES_20261027.json').read_text())
renders=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RENDERS_20261027.json').read_text())
qa_path=ROOT/'work/qa_thai_dynamic_normals_v25_review_20261027/native_dynamic_normals_v25_independent_acceptance_corrected.json'
assert sha(qa_path)=='145b40c1b432b3dc504a7ccdd1a0794c0e1292651546647a30b4708a68346045'
qa=json.loads(qa_path.read_text());assert len(qa['checks'])==56 and all(type(v)is bool and v for v in qa['checks'].values())
assert qa['status']=='ACCEPTED_V25_FIXED_NATIVE_DYNAMIC_NORMAL_TRANSPORT_MODEL_ONLY'
assert probes['all24ProbesPass']and len(probes['results'])==24 and all(x['allChecksPass']for x in probes['results'])
assert sha(build['library'])==build['sha256']==qa['librarySHA256']==probes['sha256']==renders['sha256']
for p,key in((build['sourceV23'],'sourceV23Sha256'),(build['sourceV24'],'sourceV24Sha256'),(build['rejectedOriginalV25Library'],'rejectedOriginalV25Sha256')):assert sha(p)==build[key]
assert sha(build['checkpoint'])==build['checkpointSha256']
assert sha(probes['archive'])==probes['archiveSha256']==qa['archiveSHA256']
dep=json.loads((F/'no_frame_advance_dependency_check.json').read_text());assert dep['allThreePass']and not dep['sceneFrameSetOrNodeTreeUpdateTagUsedDuringProbes']
assert len(renders['images'])==10
for image in renders['images']:assert sha(image['path'])==image['sha256']
old_mode=json.loads((ROOT/'reports/CHARACTER_THAI_BOUND_NORMALS_V24_20261027.json').read_text());assert old_mode['selectedMode']is None
for old,new in((qa_path,F/'independent_normal_transport_acceptance.json'),(ROOT/'work/qa_thai_dynamic_normals_v25_review_20261027/native_dynamic_normals_v25_independent_acceptance.json',F/'initial_qa_report_with_extra_maximum_metric_gate.json'),(ROOT/'work/qa_thai_bound_normals_v24_20261027/bound_corner_normal_diagnosis_v24.json',F/'source_fan_diagnostic_v24.json')):
    assert not new.exists();shutil.copy2(old,new)
warnings=[x['inheritedGeometryWarningsNotAnApproval']for x in probes['results']]
result={'status':'accepted-native-dynamic-normal-transport-model-only','library':build['library'],'sha256':build['sha256'],'scene':build['scene'],'body':build['body'],'rig':build['rig'],'checkpoint':build['checkpoint'],'checkpointSha256':build['checkpointSha256'],'independentQAChecks':56,'independentQASha256':sha(qa_path),'directAndNativeActionProbeCount':24,'sameFrameDependencyProbes':3,'rawMatrixFixtureAll180ComponentsAtFourSignedStates':True,'driverCount':180,'nativeRNAPathCount':540,'driverOutputPowerOfTwoEncoding':65536,'normalFieldBeforeArmature':True,'staticNormalOverrideAfterArmature':False,'requiresCustomPythonNamespaceOrFrameHandler':False,'sourceWeightsUnchanged':True,'inheritedWeightSumGateStillFalse':True,'maximumIndependentPointErrorMeters':max(x['pointErrorMeters']for x in qa['results']),'maximumIndependentRobustNormalErrorDegrees':max(x['maximumNormalErrorDegrees']for x in qa['results']),'maximumIndependentCoefficientError':max(x['coefficientError']for x in qa['results']),'tenMatchedAndDiagnosticFramesReviewed':True,'maximumInheritedRelativeFaceFlipsInProbes':max(x['relativeFacesFlippedVsBaseline']for x in warnings),'rejectedV24AndFirstV25Preserved':True,'postureFixed':False,'healthySkinningApproved':False,'nativeWalkValidated':False,'fullClothingApproved':False,'runtimeOrMasterIntegration':False,'remoteOperations':False,'MCPUsed':True,'scope':'Only dynamic normal transport on the frozen bind inputs and tested poses. Current scan defects, bad posture and old geometry deformation remain.','futureBindChangesRequireRegeneration':'Raw W, bone rest/pivots, mesh or baseline normals changes require rebuilding the explicit weight fields, inverse-rest constants and baseline normal field.'}
OUT.write_text(json.dumps(result,indent=2))
paths=list(F.rglob('*'))+[OUT,ROOT/'reports/CHARACTER_THAI_BOUND_NORMALS_V24_20261027.json',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_20261027.json',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_PROBES_20261027.json',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIX_20261027.json',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIXED_PROBES_20261027.json',ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RENDERS_20261027.json',ROOT/'scripts/prep_thai_dynamic_normals_v25_20261027.py',ROOT/'scripts/fix_thai_normal_driver_rna_v25_20261027.py',ROOT/'scripts/validate_thai_dynamic_normals_v25_20261027.py',ROOT/'scripts/render_thai_dynamic_normals_v25_20261027.py',Path(__file__)]
MAN.write_text(json.dumps({'status':'sealed-local-normal-transport-evidence-only','library':build['library'],'librarySha256':build['sha256'],'files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in paths if p.is_file()]},indent=2))
print(json.dumps(result))
