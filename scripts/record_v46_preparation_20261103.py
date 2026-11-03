"""Preserve the later WORK save and record derivative QA; no Blender execution."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
stage=json.loads((ROOT/'reports/CHARACTER_THAI_PHASE1_V46_STAGE_20261029.json').read_text())
qp=ROOT/'work/qa_thai_nonlinear_phase1_v46_20261029/gradient_qa_nov03_v46.json'
kernel=ROOT/'work/probe_thai_nonlinear_phase1_v46_20261029/phase1_kernel_v46.py'
assert sha(qp)=='ee8820067b560cdfb226622e92e36995f8843e6f58cc8fff1a453e6d2e58d95e'
assert sha(kernel)=='60f0a2e026912b014afacdb649db95ae6588fd9c1a43d752258251e003e3df5c'
assert sha(stage['checkpoint'])==stage['checkpointSha256']
assert sha(stage['source'])==stage['sourceSha256']
working=Path(stage['working']);current=sha(working)
assert current=='e07a9cb9eea1918842ed6fb9407ce2979db3085e0ed2c74cdc9c18cdb225d9da'
preserved=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_WORK_V46_PRESERVED_20261103.blend'
assert not preserved.exists();shutil.copyfile(working,preserved);assert sha(preserved)==current
q=json.loads(qp.read_text());assert q['checks']['all_steps_pass']
result={'status':'KERNEL_AND_INITIAL_GRADIENT_QA_PASS_OPTIMIZER_NOT_EXECUTED',
 'recordedAtLocal':datetime.now().astimezone().isoformat(),'kernel':str(kernel),'kernelSHA256':sha(kernel),
 'independentQA':str(qp),'independentQASHA256':sha(qp),'finiteDifferenceChecks':q['checks'],
 'originalCheckpoint':stage['checkpoint'],'originalCheckpointSHA256':stage['checkpointSha256'],
 'preservedV45':stage['source'],'preservedV45SHA256':stage['sourceSha256'],
 'workingLibrary':str(working),'initialWorkingSHA256':stage['workingSha256'],'currentWorkingSHA256':current,
 'workingChangedSinceInitialStage':True,'workingLastWriteLocal':datetime.fromtimestamp(working.stat().st_mtime).astimezone().isoformat(),
 'laterWorkPreservedCopy':str(preserved),'laterWorkPreservedCopySHA256':sha(preserved),
 'laterWorkingGeometryAudited':False,'laterWorkSaveCauseVerified':False,
 'blenderProcessObservedRunning':False,'MCPPortObservedListening':False,'newBlenderWindowOpened':False,
 'optimizerExecuted':False,'correctionApplied':False,'poseQualityApproved':False,'continuousAnimationApproved':False,
 'gameCodeChanged':False,'remoteOperations':False,'desktopSwitched':False,'computerShutdown':False,
 'nextStep':'Audit later WORK read-only against stage signatures before any asset replacement. Preserve its later save. Then implement and run only the single frozen four-state L-BFGS pilot after the completed derivative QA; do not repeat or broaden support/gates.'}
out=ROOT/'reports/CHARACTER_THAI_PHASE1_V46_PREPARATION_20261103.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'report':str(out),'sha256':sha(out),'status':result['status']}))
