"""File-only acceptance of diagnostic evidence, not a new body correction."""
from pathlib import Path
from datetime import datetime
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rp=ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json';r=json.loads(rp.read_text())
qp=ROOT/'work/qa_thai_remaining_failures_v45_20261029/v45_independent_remaining_review.json';q=json.loads(qp.read_text())
assert sha(qp)=='fcee88f22365325119dc583e9ef4b4c0b13ac52d5e0a6dc2e09127c898be91da'
assert q['diagnosticEvidenceAccepted'] and q['savedReopenedOverlayValidation']['evidenceAccepted']
checks=[]
for name,path,expected in [('library',r['library'],r['sha256']),('checkpoint',r['checkpoint'],r['checkpointSha256']),('sourceReady',r['sourceLibrary'],r['sourceLibrarySha256']),('maskArchive',r['maskArchive'],r['maskArchiveSha256']),('classification',r['classificationReport'],r['classificationReportSha256']),('actualReadback',r['archive'],r['archiveSha256'])]:
    actual=sha(path);assert actual==expected,(name,actual,expected);checks.append({'kind':name,'path':path,'sha256':actual,'matches':True})
imagepath=ROOT/'reports/thai_remaining_review_v45_20261029/window_capture_back_v45.json';image=json.loads(imagepath.read_text())
assert sha(image['path'])==image['sha256']
out=ROOT/'reports/CHARACTER_THAI_REMAINING_V45_ACCEPTANCE_20261029.json';assert not out.exists()
result={'status':'DIAGNOSTIC_AND_STATIC_OVERLAY_ACCEPTED_NO_NEW_POSE_CORRECTION','recordedAtLocal':datetime.now().astimezone().isoformat(),'library':r['library'],'librarySHA256':r['sha256'],'hashChecks':checks,'independentQA':{'path':str(qp),'sha256':sha(qp),'diagnosticEvidenceAccepted':True,'savedReopenedOverlayEvidenceAccepted':True},'occurrenceCounts':q['occurrences'],'uniqueCandidateUnionFaces':271,'overlappingFamilyFaces':92,'eightRealControlQExact':True,'V44ThirtyTwoCasesRepeatedOrInherited':False,'twoFixedFacesWitness':[13083,26008],'fixedQAndSameTargetAllZeroAbsoluteGateInfeasible':q['zeroAbsoluteGateInfeasibleWithSameFixedQAndTarget'],'rootVisualInspection':{'path':image['path'],'sha256':image['sha256'],'inspected':True,'markedBandsVisibleAtPosteriorAxillae':True,'staticUnionAllEightSamplesDeclared':True,'legendAndPoseControlsVisible':True,'backNavigationSavedIntoLibrary':False,'humanClicksClaimed':False},'chronology':q['chronology'],'accepted':{'diagnostic':True,'staticOverlay':True,'newGeometryCorrection':False,'bodyFinal':False,'continuousAnimation':False,'clothes':False,'GLB':False,'gameRuntime':False,'masterMap':False,'realism':False},'nextMethodExecuted':False,'pinsOrROIChanged':False,'newSolverExecuted':False,'gameCodeChanged':False,'remoteOperations':False,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'computerShutdown':False}
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'report':str(out),'sha256':sha(out),'library':r['library'],'librarySHA256':r['sha256']}))
