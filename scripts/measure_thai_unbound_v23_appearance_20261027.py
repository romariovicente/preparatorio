"""Robust direction metric and matched-image evidence; no Blender/file edits."""
import json,hashlib
import numpy as np
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'reports/thai_rebind_stage_v23_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_APPEARANCE_20261027.json'
assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reopen=json.loads((ROOT/'reports/CHARACTER_THAI_UNBOUND_REBIND_SOURCE_V23_REOPEN_PREVIEW_20261027.json').read_text())
assert sha(reopen['fullReopenExport'])==reopen['fullReopenExportSha256']
with np.load(reopen['fullReopenExport'])as n:
    stage=n['evaluatedCornerNormalsWorld'].astype(np.float64)
    source=n['sourceEvaluatedCornerNormalsWorld'].astype(np.float64)
    q=n['posedWorld'].copy();sq=n['sourcePosedWorld'].copy()
    edges=n['stage::edges'].copy();triangles=n['stage::triangles'].copy()
with np.load(ROOT/'work/qa_thai_rebind_stage_v23_20261027/evaluated_baseline.npz')as n:target=n['evaluatedCornerNormalsWorld'].astype(np.float64)
def angles(a,b):
    a=a/np.linalg.norm(a,axis=1)[:,None];b=b/np.linalg.norm(b,axis=1)[:,None]
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.einsum('ij,ij->i',a,b)))
vs_export=angles(stage,target);vs_reopened_source=angles(stage,source)
assert len(vs_export)==len(triangles)*3 and np.array_equal(q,sq)
assert max(vs_export.max(),vs_reopened_source.max())<.05
images=[]
for view in('front','right','back'):
    before=F/'matched_previews'/(view+'_before_source.png')
    after=F/'matched_previews'/(view+'_after_unbound.png')
    a=np.array(Image.open(before).convert('RGB'),np.float64)
    b=np.array(Image.open(after).convert('RGB'),np.float64)
    assert a.shape==b.shape
    delta=np.abs(b-a)
    images.append({'view':view,'beforeSHA256':sha(before),'afterSHA256':sha(after),'resolution':list(a.shape),'meanAbsoluteRGBByteDifference':float(delta.mean()),'rmsRGBByteDifference':float(np.sqrt(np.mean(delta**2))),'maximumRGBByteDifference':float(delta.max()),'fractionPixelsAnyChannelDifferenceOver8':float((delta.max(2)>8).mean()),'differencePercentilesRGBByte':np.percentile(delta,[50,95,99,99.9]).tolist()})
result={'status':'robust-baseline-direction-metric-and-paired-image-evidence-recorded','library':reopen['library'],'librarySha256':reopen['sha256'],'fullReopenExportSha256':reopen['fullReopenExportSha256'],'maximumAllVertexWorldPointDifferenceMeters':float(np.linalg.norm(q-sq,axis=1).max()),'allCornerCount':len(vs_export),'normalDirectionFormula':'float64 normalize BOTH vectors, then degrees(atan2(norm(cross(a,b)),dot(a,b)))','maximumNormalDirectionErrorVsFrozenExportDegrees':float(vs_export.max()),'maximumNormalDirectionErrorVsReopenedSourceDegrees':float(vs_reopened_source.max()),'normalDirectionGateDegrees':.05,'normalDirectionGatePassed':bool((vs_export<.05).all()and(vs_reopened_source<.05).all()),'normalMetricErratum':'Earlier build/reopen arccos(dot) without renormalizing both inputs reported .02839156deg; robust directional maximum is recorded here. The .05deg gate is unchanged.','edgeCount':len(edges),'triangleCount':len(triangles),'images':images,'imageMetricsRole':'Supporting evidence only; inspect the three matched views as well as complete geometry/normal/UV checks.','acceptanceScope':'Static unbound source only. Bound stage remains rejected; no repaired posture or Walk.','sourceFilesChanged':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps(result))
