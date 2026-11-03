"""Preserve actual live V40 before a diagnostic-only gradient review library."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_GRADIENT_V42_STAGE_20261029.json'
assert not OUT.exists()
prior=json.loads((ROOT/'reports/CHARACTER_THAI_LOCAL_VOLUME_V41_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(prior['source'])
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==prior['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in prior['meshSignatures'].items())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_GRADIENT_REVIEW_V42_20261029.blend'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_GRADIENT_REVIEW_V42_WORK_20261029.blend'
assert not cp.exists() and not work.exists()
source=bpy.data.filepath;source_sha=sha(source);dirty_before=bpy.data.is_dirty
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_SKINNING_GRADIENT_V42_DIAGNOSTIC'
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:prior[k] for k in ['sourceBody','nativeRig','poseRig','nativeRestSHA256','meshSignatures','actionSignatures','actualSourceArchive','actualSourceArchiveSha256']}
result.update(source=source,sourceSha256=source_sha,sourceDirtyFlagBefore=dirty_before,
              sourceDiskHashMatchesKnownV40=source_sha==prior['sourceSha256'],
              checkpoint=str(cp),checkpointSha256=sha(cp),working=str(work),workingSha256=sha(work),
              scene=scene.name,diagnosticOnly=True,newWindowOpened=False,windowFocusedOrMoved=False,
              desktopSwitched=False,remoteOperations=False,MCPUsed=True)
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['meshSignatures','actionSignatures']}))
