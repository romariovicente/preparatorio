"""Preserve the live diagnostic review before a separate pose-space study."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_POSE_POISSON_V43_STAGE_20261029.json'
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_GRADIENT_REVIEW_V42_20261029.json').read_text())
old=json.loads((ROOT/'reports/CHARACTER_THAI_GRADIENT_V42_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==old['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in old['meshSignatures'].items())
review=bpy.data.objects[r['bodyObject']]
arrays=u['helpers']['_snapshot'](review.data)['arrays'];W=u['helpers']['_weights'](review.data,55)
with np.load(r['archive']) as z:
    assert np.array_equal(arrays['coordinates'],z['actualRestWorld']) and np.array_equal(arrays['triangles'],z['actualTriangles'])
    assert np.array_equal(W,z['actualWeights55']), 'Preserve possible human Weight Paint edits; do not overwrite'
signatures={**old['meshSignatures'],review.name:u['mesh_signature'](review)}
source=bpy.data.filepath;source_sha=sha(source)
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_POSE_POISSON_V43_20261029.blend'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_POISSON_V43_WORK_20261029.blend'
assert not cp.exists() and not work.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_LOCAL_POSE_POISSON_V43'
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:old[k] for k in ['sourceBody','nativeRig','poseRig','nativeRestSHA256','actualSourceArchive','actualSourceArchiveSha256','actionSignatures']}
result.update(source=source,sourceSha256=source_sha,sourceDiskHashMatchesKnownReview=source_sha==r['sha256'],
              meshSignatures=signatures,diagnosticBodyToHide=review.name,checkpoint=str(cp),checkpointSha256=sha(cp),
              working=str(work),workingSha256=sha(work),scene=scene.name,
              newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False,MCPUsed=True)
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['meshSignatures','actionSignatures']}))
