"""Repair the visually rejected V3 head/shoulder restrictions using UV regions."""
import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'reports/thai_upper_refit_v4_20261023'
mask_path=FOLDER/'texture_region_candidates.npz'
assert hashlib.sha256(mask_path.read_bytes()).hexdigest()=='29e85a8ee5fc1254fd300bfc3f0648ee36f26fbee05b19ebc13814914f8e6e43'
mask=np.load(mask_path);baseline=np.load(ROOT/'reports/thai_upper_refit_20261023/baseline_mesh.npz');P=baseline['vertices']
whole=mask['wholeHeadCandidate'];face=mask['faceJawCandidate']
rigid=mask['rigidHeadCandidate']
plan=json.loads((FOLDER/'texture_region_candidates.json').read_text())
ns={'__file__':str(ROOT/'scripts/prepare_thai_upper_weights_20261023.py'),'__name__':'__main__',
 'PREP_OUTPUT_FOLDER':FOLDER,'PREP_HEAD_GUARD_IDS':whole,'PREP_RIGID_HEAD_IDS':rigid,
 'PREP_LANDMARK_OVERRIDES':{'neck':plan['candidateNeckBase'],'head':plan['candidateHeadPivot']}}
script=Path(ns['__file__']);exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
prepared=json.loads((FOLDER/'prepared_weights.json').read_text());prepared.update(
 status='v4-semantic-head-and-free-sleeve-weights-awaiting-blender-review',
 maskSourceSha256=plan['maskSha256'],maskSemantics='Whole face/jaw and hair separated from white collar/sleeve; lower hair remains blended.',
 rigidHeadVertices=len(rigid),lowerHairVerticesBlended=len(mask['lowerHairCollarReview']))
(FOLDER/'prepared_weights.json').write_text(json.dumps(prepared,indent=2),encoding='utf-8')
print(json.dumps({'rigidHeadVertices':len(rigid),'headGuardVertices':len(whole),'whiteClothAllowedToFollowArms':len(mask['oldHeadWhiteClothExcluded'])}))
