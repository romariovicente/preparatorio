"""Checkpoint the rejected corrective pilot before independent full-vector repair."""
import bpy,json,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_V38_STAGE_20261028.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_CORRECTIVE_V37_20261028.json').read_text());prior=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_V37_STAGE_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])and not bpy.data.is_dirty and sha(r['library'])==r['sha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));assert u['action_signatures']()==prior['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==v for n,v in prior['meshSignatures'].items())
signatures={**prior['meshSignatures'],r['bodyObject']:u['mesh_signature'](bpy.data.objects[r['bodyObject']])}
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_FULL_AXILLA_WEIGHTS_V38_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_FULL_AXILLA_WEIGHTS_V38'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_FULL_AXILLA_WEIGHTS_V38_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:prior[k]for k in ['actionSignatures','nativeRestSHA256','sourceBody','poseRig','nativeRig']}
result.update(status='full-vector-local-repair-stage-before-solve',source=r['library'],sourceSha256=r['sha256'],checkpoint=str(cp),checkpointSha256=sha(cp),
    working=str(work),workingSha256=sha(work),scene=scene.name,meshSignatures=signatures,studyBodiesToHide=[r['bodyObject']],
    MCPUsed=True,newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False)
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['meshSignatures','actionSignatures']}))
