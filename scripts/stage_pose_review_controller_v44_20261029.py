"""Checkpoint the live V43 snapshot before adding review controls to a copy."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_STAGE_20261029.json'
assert not OUT.exists()
previous=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_POISSON_V43_20261029.json').read_text())
old=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_POISSON_V43_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(previous['library'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==old['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in old['meshSignatures'].items())
actor=bpy.data.objects[previous['bodyObject']]
a=u['helpers']['_snapshot'](actor.data)['arrays'];W=u['helpers']['_weights'](actor.data,55)
with np.load(previous['archive']) as z:
    assert np.array_equal(a['coordinates'],z['actualRestWorld']) and np.array_equal(a['triangles'],z['actualTriangles'])
    assert np.array_equal(W,z['actualWeights55']), 'Preserve possible human weight edits before continuing'
signatures={**old['meshSignatures'],actor.name:u['mesh_signature'](actor)}
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_REVIEW_CONTROLLER_V44_20261029.blend'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REVIEW_CONTROLLER_V44_WORK_20261029.blend'
assert not cp.exists() and not work.exists()
source=bpy.data.filepath;source_sha=sha(source)
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_POSE_CONTROLS_V44'
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={k:old[k] for k in ['nativeRig','poseRig','nativeRestSHA256','actualSourceArchive','actualSourceArchiveSha256','actionSignatures']}
result.update(source=source,sourceSha256=source_sha,sourceHashMatchesKnownV43=source_sha==previous['sha256'],
 sourceBody=actor.name,meshSignatures=signatures,checkpoint=str(cp),checkpointSha256=sha(cp),working=str(work),workingSha256=sha(work),
 scene=scene.name,candidate=previous['candidate'],candidateSha256=previous['candidateSha256'],
 actualV43Snapshots=previous['archive'],actualV43SnapshotsSha256=previous['archiveSha256'],
 newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False,MCPUsed=True)
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['meshSignatures','actionSignatures']}))
