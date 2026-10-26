"""Finish interrupted V11 reimport and deformation evidence in a hidden library job."""
from pathlib import Path
import bpy,json,hashlib,runpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
record=json.loads((ROOT/'reports/CHARACTER_THAI_GARMENT_V11_20261023.json').read_text())
scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023']
bpy.context.window.scene=scene
mesh=next(o for o in scene.objects if o.type=='MESH')
arm=next(o for o in scene.objects if o.type=='ARMATURE')
helper=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
snapshot=helper['_snapshot'](mesh.data)
array_hashes={key:hashlib.sha256(value.tobytes()).hexdigest() for key,value in snapshot['arrays'].items()}
expected_hashes=record['weightCopyPreservation']['arraySha256']
array_changes=[key for key,value in expected_hashes.items() if array_hashes.get(key)!=value]
data=np.load(ROOT/'reports/thai_garment_v11_validation_20261026/prepared_weights.npz')
names=[g.name for g in mesh.vertex_groups]
weight_error=float(np.abs(helper['_weights'](mesh.data,len(names))-data['weights']).max())
expected=np.load(ROOT/'reports/thai_garment_v11_validation_20261026/posed_surface.npz')['posed']
ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated=ev.to_mesh()
coords=np.empty(len(evaluated.vertices)*3,dtype=np.float32);evaluated.vertices.foreach_get('co',coords)
world=np.array(ev.matrix_world);ev.to_mesh_clear()
coords=coords.reshape(-1,3)@world[:3,:3].T+world[:3,3]
pose_error=float(np.linalg.norm(coords-expected,axis=1).max())
preflight={'status':'pass' if not array_changes and weight_error==0 and pose_error<1e-5 else 'fail',
 'sourceSavedAfterOriginalExport':True,'authoredArrayChanges':array_changes,
 'authoredArrayHashes':array_hashes,'weightMaxError':weight_error,
 'groupNamesIdentical':names==data['group_names'].tolist(),'standingPoseMaxError':pose_error,
 'scope':'Numeric authoring state check; saved GUI/UI differences were preserved, not reverted.'}
(ROOT/'reports/thai_garment_v11_validation_20261026/saved_source_preflight.json').write_text(json.dumps(preflight,indent=2),encoding='utf-8')
assert preflight['status']=='pass' and preflight['groupNamesIdentical'],preflight
script=ROOT/'scripts/validate_thai_standing_seams_20261023.py'
ns={'__file__':str(script),'__name__':'__main__',
 'PREP_WORK':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_V11_QA_20261026.blend',
 'PREP_OUT':ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_GARMENT_V11_PROBES_20261026.blend',
 'PREP_FOLDER':ROOT/'reports/thai_garment_v11_validation_20261026',
 'PREP_SOURCE_REPORT':ROOT/'reports/CHARACTER_THAI_GARMENT_V11_20261023.json',
 'PREP_QA_SCENE':'VALIDATE_THAI_GARMENT_BIND_V11_20261026',
 'PREP_EXTRA_HEAD_TURN':True,
 'PREP_SCOPE':'local-garment-scan-seams-not-neutral-pose-or-runtime',
 'PREP_REPORT':ROOT/'reports/CHARACTER_THAI_GARMENT_V11_REIMPORT_20261026.json'}
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),ns)
