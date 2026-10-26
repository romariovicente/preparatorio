"""Reuse the read-only near-seam standing/head15 probe for the V12 library."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'scripts/probe_thai_v11_near_seams_20261026.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_INPUT_LIBRARY':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SEAM_AREA_V12_PROBES_20261026.blend',
 'PREP_FOLDER':ROOT/'reports/thai_seam_area_v12_20261026',
 'PREP_QA_SCENE':'VALIDATE_THAI_SEAM_AREA_BIND_V12_20261026'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
# Inspect the actual saved reimport, not the solver's predicted surface.
import json
import numpy as np
F=ROOT/'reports/thai_seam_area_v12_20261026'
prepared=np.load(F/'prepared_weights.npz');P=prepared['vertices'];Q=ns['standing']
T=np.load(ROOT/'reports/thai_upper_refit_20261023/baseline_mesh.npz')['triangles']
branch=np.load(ROOT/'reports/thai_upper_refit_20261023/head_hand_graph_masks.npz')['rightHand']
pilot=json.loads((ROOT/'reports/CHARACTER_THAI_SEAM_AREA_V12_20261026.json').read_text())
def doubled_area(points):return np.linalg.norm(np.cross(points[T[:,1]]-points[T[:,0]],points[T[:,2]]-points[T[:,0]]),axis=1)
original_area=doubled_area(P);ratio=doubled_area(Q)/np.maximum(original_area*pilot['uniformScaleFactor']**2,1e-20)
editable=np.zeros(len(P),bool);editable[prepared['editable_vertices']]=True
edited_triangles=editable[T].any(1)&(original_area>1e-8)
collar=(P[:,2]>1.10)&(P[:,2]<1.48);collar[branch]=False
collar_triangles=collar[T].all(1)&(original_area>1e-8)
targets=[17772,17896,17897]
gates={'editableTrianglesAbove4xAtMost23':int((ratio[edited_triangles]>4).sum())<=23,
 'collarTrianglesAbove4xAtMost128':int((ratio[collar_triangles]>4).sum())<=128,
 'threeTargetAreasBelow4x':bool((ratio[targets]<4).all()),
 'editableMaximumAtMostV11':float(ratio[edited_triangles].max())<=8.5151}
measurement={'status':'actual-exported-reimport-area-gates-pass' if all(gates.values()) else 'actual-exported-reimport-area-gates-fail',
 'gates':gates,'editableAreaAbove4x':int((ratio[edited_triangles]>4).sum()),
 'collarAreaAbove4x':int((ratio[collar_triangles]>4).sum()),'editableMaximumAreaRatio':float(ratio[edited_triangles].max()),
 'threeTargetAreaRatios':{str(t):float(ratio[t]) for t in targets},
 'scope':'Measured on the actual saved reimport. Local seam-area criteria only; full apparel/pose/Walk remain unaccepted.',
 'nativeWalkValidated':False,'runtimeChanged':False}
out=F/'actual_export_area_gates.json';assert not out.exists()
out.write_text(json.dumps(measurement,indent=2),encoding='utf-8')
assert all(gates.values()),measurement
print(json.dumps(measurement))
