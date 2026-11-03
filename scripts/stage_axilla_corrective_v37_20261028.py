"""Preserve the rejected weight-study work copy before a separate corrective pilot."""
import bpy,json,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_V37_STAGE_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not OUT.exists()
previous=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_V36_STAGE_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(previous['working'])and not bpy.data.is_dirty and sha(previous['working'])==previous['workingSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==previous['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==v for n,v in previous['meshSignatures'].items())
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_AXILLA_CORRECTIVE_V37_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_LOCAL_AXILLA_CORRECTIVE_V37'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_CORRECTIVE_V37_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:previous[k]for k in ['meshSignatures','actionSignatures','nativeRestSHA256','sourceBody','poseRig','nativeRig']}
result.update(status='separate-local-corrective-study-checkpointed',source=previous['working'],sourceSha256=previous['workingSha256'],
    checkpoint=str(cp),checkpointSha256=sha(cp),working=str(work),workingSha256=sha(work),scene=scene.name,
    MCPUsed=True,newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False)
OUT.write_text(json.dumps(result,indent=2))
properties={}
for p in bpy.types.CorrectiveSmoothModifier.bl_rna.properties:
    properties[p.identifier]={'type':p.type,'description':p.description}
    if p.type=='ENUM':properties[p.identifier]['items']=[x.identifier for x in p.enum_items]
print(json.dumps({'stage':str(OUT),'checkpointSha256':sha(cp),'properties':properties}))
