"""Preserve the unchanged V34 work session before the pose-only V35 pilot."""
import bpy,json,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_POSE_CLEARANCE_V35_STAGE_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
prior=json.loads((ROOT/'reports/CHARACTER_THAI_HAND_CLEARANCE_V34_STAGE_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(prior['working']) and not bpy.data.is_dirty and sha(prior['working'])==prior['workingSha256']
helper=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert helper['action_signatures']()==prior['actionSignatures']
assert all(helper['mesh_signature'](bpy.data.objects[n])==sig for n,sig in prior['meshSignatures'].items())
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_POSE_CLEARANCE_V35_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),copy=True,compress=True)
scene.name='REVIEW_THAI_POSE_CLEARANCE_V35'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_CLEARANCE_V35_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
r={'status':'pose-only-study-checkpointed-before-any-changes','source':prior['working'],'sourceSha256':prior['workingSha256'],
    'checkpoint':str(cp),'checkpointSha256':sha(cp),'working':str(work),'workingSha256':sha(work),'scene':scene.name,
    'meshSignatures':prior['meshSignatures'],'actionSignatures':prior['actionSignatures'],'nativeRestSHA256':prior['nativeRestSHA256'],
    'nativeArmWorld':prior['nativeArmWorld'],'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in ['meshSignatures','actionSignatures','nativeArmWorld']}))
