"""Continuous head/neck/chest transition for lower hair, preserving the face.

V4 made the full face rigid, but its lower-hair geodesic weights approached
only 10% head weight immediately below the 100%-head region at Z=1.38. This
revision removes that numerical discontinuity before a final visual decision.
It writes a new draft, never modifies V4 or an in-flight Blender operation.
"""
from pathlib import Path
import json,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'reports/thai_upper_refit_v4_20261023';DEST=ROOT/'reports/thai_upper_refit_v5_20261023'
DEST.mkdir(exist_ok=False)
data=np.load(SOURCE/'prepared_weights.npz');W=data['weights'].copy();P=data['vertices'];names=data['group_names'];mask=np.load(SOURCE/'texture_region_candidates.npz')
hair=mask['lowerHairCollarReview'];h=names.tolist().index('head')
old_range=[float(W[hair,h].min()),float(W[hair,h].max())]
progress=np.clip((P[hair,2]-1.28)/.10,0,1);head_weight=progress*progress*(3-2*progress)
for i,value in zip(hair,head_weight):
    row=W[i].copy();row[h]=0;total=float(row.sum());assert total>0
    row*=float(1-value)/total;row[h]=value
    keep=np.argsort(row)[-4:];limited=np.zeros_like(row);limited[keep]=row[keep];limited/=limited.sum();W[i]=limited
assert np.max((W>0).sum(1))<=4 and np.max(np.abs(W.sum(1)-1))<2e-6
assert np.all(W[mask['faceJawCandidate'],h]==1)
assert np.array_equal(W[P[:,2]<=.66],data['weights'][P[:,2]<=.66])
np.savez_compressed(DEST/'prepared_weights.npz',weights=W,vertices=P,group_names=names)
shutil.copy2(SOURCE/'texture_region_candidates.npz',DEST/'texture_region_candidates.npz')
shutil.copy2(SOURCE/'texture_region_candidates.json',DEST/'texture_region_candidates.json')
plan=json.loads((SOURCE/'prepared_weights.json').read_text());plan['status']='v5-lower-hair-continuous-feather-awaiting-blender-and-visual-qa'
plan['lowerHairFeather']={'vertices':len(hair),'zRange':[1.28,1.38],'interpolation':'smoothstep','oldHeadWeightRange':old_range,'newHeadWeightRange':[float(W[hair,h].min()),float(W[hair,h].max())],'faceJawHeadWeightsRemainExactlyOne':True,'lowerLimbWeightsPreserved':True}
(DEST/'prepared_weights.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps(plan['lowerHairFeather']))
