"""File-only integrator acceptance; no Blender, network, solver or game mutation."""
import json,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rawpath=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json';raw=json.loads(rawpath.read_text())
qpath=ROOT/'work/qa_pose_review_controller_v44_20261029/v44_independent_controller_review.json';q=json.loads(qpath.read_text())
ppath=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_20261029.json';p=json.loads(ppath.read_text())
ipath=ROOT/'reports/pose_review_controller_v44_20261029/window_capture_final_v44.json';image=json.loads(ipath.read_text())
assert sha(qpath)=='757c864bfa6ed214230fd57c000c28fef693b40d3038bae533e2f1efdebfa34e'
assert q['functionalEvidenceAccepted'] and q['exact32CombinationCoverage']
assert q['integrationReportSHA256']==sha(rawpath)
checks=[]
for name,path,expected in [('functionalLibrary',raw['library'],raw['sha256']),('controller',raw['controller'],raw['controllerSha256']),('archive32',raw['archive'],raw['archiveSha256']),('checkpoint',raw['checkpoint'],raw['checkpointSha256']),('readyLibrary',p['library'],p['sha256']),('presentationCheckpoint',p['presentationCheckpoint'],p['presentationCheckpointSHA256']),('windowImage',image['path'],image['sha256'])]:
    actual=sha(path);assert actual==expected,(name,actual,expected)
    checks.append({'kind':name,'path':path,'sha256':actual,'matches':True})
assert all(p['bindAndDefaultPoseChecks'].values()) and p['sourceMeshesAnd2200CurvesExact']
assert p['headMaximumDifferenceMeters']<p['headToleranceMeters']
result={'status':'LOCAL_REVIEW_TOOL_ACCEPTED_ONLY_POSE_AND_CLOTHES_STILL_PENDING','recordedAtLocal':datetime.now().astimezone().isoformat(),'functionalControllerAccepted':True,'savedOpenLibrary':p['library'],'savedOpenLibrarySHA256':p['sha256'],'hashChecks':checks,'independentQA':{'path':str(qpath),'sha256':sha(qpath),'scope':'Original functional library07151 and32API samples; not a repeat32case review of READY','all32PointsBitExact':all(row['pointsBitExact'] for row in q['realPointAndStateCases']),'threeDistinctRejectionsPreservedState':q['allThreeNegativeCaseCoverage']},'presentationIntegratorReadback':{'path':str(ppath),'sha256':sha(ppath),'bindAndDefaultPoseChecks':p['bindAndDefaultPoseChecks'],'sourceMeshesAnd2200CurvesExact':True,'headPointsBitExact':p['headPointsBitExact'],'headMaximumDifferenceMeters':p['headMaximumDifferenceMeters'],'headToleranceMeters':p['headToleranceMeters'],'initialOverstrictHeadAssertionFailurePreserved':True,'all32OperationsRepeatedOnReady':False},'visualInspection':{'source':'Blender window buffer only; no OS focus/desktop switching','path':image['path'],'sha256':image['sha256'],'fullCharacterAndEightPoseButtonsVisible':True,'boneDisplayObstructionRemoved':True,'rejectedOutfitSourcesHiddenOnlyInStudy':True,'humanPanelClicksClaimed':False},'accepted':{'localReviewController':True,'presentation':True,'poseGeometry':False,'continuousAnimation':False,'defaultClothes':False,'GLB':False,'runtime':False,'masterMap':False,'realism':False,'Mixamo':False},'operations':{'localOnly':True,'remoteOperations':False,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'newSolverExecuted':False,'gameCodeChanged':False,'computerShutdown':False},'nextStep':'Locate remaining orientation/fan/interface failures before another physical method; keep V40 baseline. Preserve Thai face/hair and original white shirt/black skirt direction, optional coat/school uniform. No promotion to game yet.'}
out=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_ACCEPTANCE_20261029.json'
assert not out.exists();out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'report':str(out),'sha256':sha(out),'readyLibrary':p['library'],'readyLibrarySHA256':p['sha256']}))
