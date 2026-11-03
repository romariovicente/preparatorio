"""Checkpoint current V45 before a separate nonlinear pose-space pilot."""
import bpy,json,hashlib,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_PHASE1_V46_STAGE_20261029.json';assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json').read_text())
old=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_V45_STAGE_20261029.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path(bpy.data.filepath)==Path(r['library']) and sha(r['library'])==r['sha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==old['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in old['meshSignatures'].items())
module=sys.modules['preparatorio_review_v44'];body=module.actor(bpy.context.scene);module._verify_bind(body,module._candidate());assert body.name==r['actor']
signatures={**old['meshSignatures'],body.name:u['mesh_signature'](body)}
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_NONLINEAR_V46_20261029.blend'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_NONLINEAR_V46_WORK_20261029.blend';assert not cp.exists() and not work.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(cp),copy=True,compress=True)
scene.name='REVIEW_THAI_NONLINEAR_PHASE_I_V46'
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:old[k] for k in ['nativeRig','poseRig','nativeRestSHA256','actualSourceArchive','actualSourceArchiveSha256','actionSignatures','candidate','candidateSha256','actualV43Snapshots','actualV43SnapshotsSha256','sourceV44Cases','sourceV44CasesSha256']}
result.update(source=r['library'],sourceSha256=r['sha256'],sourceBody=body.name,sourceV45Readback=r['archive'],sourceV45ReadbackSHA256=r['archiveSha256'],meshSignatures=signatures,checkpoint=str(cp),checkpointSha256=sha(cp),working=str(work),workingSha256=sha(work),scene=scene.name,newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False,MCPUsed=True)
OUT.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['actionSignatures','meshSignatures']}))
