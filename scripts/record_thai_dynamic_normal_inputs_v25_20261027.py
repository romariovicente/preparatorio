"""Record the frozen bind inputs so future mesh/weight edits cannot reuse them silently."""
import json,hashlib
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_dynamic_normals_v25_20261027';OUT=F/'frozen_normal_field_inputs.json'
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_DYNAMIC_NORMALS_V25_RNA_FIXED_PROBES_20261027.json').read_text())
with np.load(r['archive'])as n:a={k:n[k].copy()for k in('vertices','triangles','weights','restMatrices','baselineNormalAttribute','dynamicWeightFields','unweightedFallbackField','groupNames')}
w=a['weights'].astype(float);s=w.sum(1);expected=np.divide(w,s[:,None],out=np.zeros_like(w),where=s[:,None]>1e-12).astype(np.float32)
assert np.array_equal(expected,a['dynamicWeightFields'])and np.array_equal((s<=1e-12).astype(np.float32),a['unweightedFallbackField'])
result={'status':'frozen-bind-inputs-recorded-for-future-invalidation','library':r['library'],'librarySHA256':r['sha256'],'arrays':{k:{'shape':list(v.shape),'dtype':v.dtype.str,'sha256':hashlib.sha256(v.tobytes()).hexdigest()}for k,v in a.items()},'pointNormalWeightsExactlyDerivedFromOriginalStoredDeformWeights':True,'rawDeformWeightsWereNotChangedOrNormalized':True,'regenerateBeforeUsingAfterChanges':['bone rest matrices/pivots/scale or bone order','stored deform weights or vertex group order','rest mesh shape, topology or baseline corner normals'],'reason':'Normal weight fields and inverse-rest coefficients are frozen bind inputs. Pose is dynamic; editing W/rest/mesh without rebuilding the field would make normals stale.','BlenderOnlyAuthoringScope':'This native node/driver graph is not a validated runtime GLB asset. Export/reimport and native Walk require separate validation.'}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({'status':result['status'],'arrays':len(a)}))
