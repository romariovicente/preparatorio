"""Checkpoint the actual V35 session before any local weight repair."""
import bpy,json,hashlib,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_AXILLA_V36_STAGE_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_CLEARANCE_V35_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])and not bpy.data.is_dirty and sha(r['library'])==r['sha256']
utils=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
v35stage=json.loads((ROOT/'reports/CHARACTER_THAI_POSE_CLEARANCE_V35_STAGE_20261028.json').read_text())
assert utils['action_signatures']()==v35stage['actionSignatures']
preserve=list(v35stage['meshSignatures'])+[r['newBody']]
signatures={n:utils['mesh_signature'](bpy.data.objects[n])for n in preserve}
assert all(signatures[n]==s for n,s in v35stage['meshSignatures'].items())
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_AXILLA_V36_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),copy=True,compress=True)
scene.name='REVIEW_THAI_AXILLA_WEIGHT_REPAIR_V36'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_V36_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={'status':'local-axilla-repair-checkpoint-created','source':r['library'],'sourceSha256':r['sha256'],
    'checkpoint':str(cp),'checkpointSha256':sha(cp),'working':str(work),'workingSha256':sha(work),'scene':scene.name,
    'meshSignatures':signatures,'actionSignatures':v35stage['actionSignatures'],'nativeRestSHA256':v35stage['nativeRestSHA256'],
    'sourceBody':r['newBody'],'poseRig':r['newRig'],'nativeRig':'V28_Clinical_Standard_Rig',
    'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['meshSignatures','actionSignatures']}))
