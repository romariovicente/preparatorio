"""Record the bounded native read-only audit and preserve all input saves."""
import json,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rp=ROOT/'reports/CHARACTER_THAI_V46_LATER_WORK_AUDIT_20261103.json'
assert sha(rp)=='80a1efbef2adb75626e8c06027df49ea1a2f824098744997ea4fbbe1ac4754e8'
r=json.loads(rp.read_text());assert r['coreAndCurrentPoseAuditAccepted']
assert len(r['meshChecks'])==13 and all(v['exact'] for v in r['meshChecks'].values())
assert all(r['bindChecks'].values()) and r['source2200CurvesExact']
assert r['currentPoseCheck']['pointsBitExact'] and r['currentPoseCheck']['maximumDifferenceMeters']==0
assert sha(r['loadedLibrary'])==r['loadedLibrarySHA256']
assert sha(r['workingLibrary'])==r['workingLibrarySHA256']
assert sha(r['archive'])==r['archiveSHA256']
assert sha(r['stageFile'])==r['stageReportSHA256']
out=ROOT/'reports/CHARACTER_THAI_V46_AUDIT_ACCEPTANCE_20261103.json';assert not out.exists()
result={'status':'LATER_WORK_CORE_AND_CURRENT_SAVED_POSE_AUDIT_ACCEPTED','recordedAtLocal':datetime.now().astimezone().isoformat(),
 'auditReport':str(rp),'auditReportSHA256':sha(rp),'savedWork':r['workingLibrary'],'savedWorkSHA256':r['workingLibrarySHA256'],
 'preservedCopy':r['loadedLibrary'],'preservedCopySHA256':r['loadedLibrarySHA256'],
 'nativeReadback':r['archive'],'nativeReadbackSHA256':r['archiveSHA256'],
 'sourceMeshCount':13,'allSourceMeshSignaturesExact':True,'bindRestWeightsNamesExact':True,'source2200CurvesExact':True,
 'currentSavedPose':r['currentPoseCheck'],'overlayColorsAndMasksExact':all(r['overlayChecks'].values()),
 'independentReview':{'agent':'/root/phase1_gradient_qa_nov03','scope':'Report/script/hash linkage and saved-pose scope; no second Blender run or independent pose recomputation','accepted':True},
 'blenderMethod':'Existing prepared Blender5.2.2 CLI, factory-startup/disable-autoexec/background; process exited normally',
 'MCPUsed':False,'newVisibleWindowOpened':False,'desktopSwitched':False,'windowFocusedOrMoved':False,
 'fileSavedOrOverwritten':False,'inputFilesUnchanged':True,'optimizerExecuted':False,'newCorrectionApplied':False,
 'causeOfByteDifferenceDetermined':False,'allAnimationStatesRevalidated':False,'newPoseQualityApproved':False,
 'nextStep':'Reuse preserved later WORK as copy source without discarding its later save. The kernel derivative QA remains valid. Implement the single frozen L-BFGS four-state pilot; compare all four live baseline states before asset integration. No need to repeat this current-saved-pose audit while hashes remain the same.'}
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'report':str(out),'sha256':sha(out),'status':result['status']}))
