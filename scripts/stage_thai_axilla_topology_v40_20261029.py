"""Checkpoint actual V39 before a separate, bounded diagonal repair study."""
import bpy, json, hashlib, runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_TOPOLOGY_V40_STAGE_20261029.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
prior=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_GEOMETRY_V39_20261029.json').read_text())
original=json.loads((ROOT/'reports/CHARACTER_THAI_GEOMETRY_V39_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(prior['library']) and not bpy.data.is_dirty
assert sha(prior['library'])==prior['sha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==original['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in original['meshSignatures'].items())
body=bpy.data.objects[prior['bodyObject']]
arrays=u['helpers']['_snapshot'](body.data)['arrays'];W=u['helpers']['_weights'](body.data,55)
bind=ROOT/'reports/thai_axilla_geometry_v39_20261029/reopened_bind_actual_v39.npz'
assert sha(bind)=='826fa084e0f5c67387d1c91fa0f2dbe1129b57f13f3be9b27372b6befb0c005d'
with np.load(bind) as z:
    assert np.array_equal(arrays['coordinates'],z['actualRestWorld'])
    assert np.array_equal(arrays['triangles'],z['actualTriangles']) and np.array_equal(W,z['actualWeights55'])
window=bpy.context.window or bpy.context.window_manager.windows[0]
scene=window.scene
checkpoint=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_AXILLA_TOPOLOGY_V40_20261029.blend'
working=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_TOPOLOGY_V40_WORK_20261029.blend'
assert not checkpoint.exists() and not working.exists()
signatures={**original['meshSignatures'],body.name:u['mesh_signature'](body)}
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),compress=True,copy=True)
scene.name='REVIEW_THAI_LOCAL_AXILLA_TOPOLOGY_V40'
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(working),compress=True)
result={'source':prior['library'],'sourceSha256':prior['sha256'],'sourceBody':body.name,
        'actualSourceBind':str(bind),'actualSourceBindSha256':sha(bind),
        'poseRig':original['poseRig'],'nativeRig':original['nativeRig'],
        'checkpoint':str(checkpoint),'checkpointSha256':sha(checkpoint),
        'working':str(working),'workingSha256':sha(working),'scene':scene.name,
        'meshSignatures':signatures,'actionSignatures':original['actionSignatures'],
        'nativeRestSHA256':original['nativeRestSHA256'],
        'scope':'Separate diagonal-only study; all V39 positions and55weights fixed; not the playable map.',
        'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['meshSignatures','actionSignatures']}))
