"""Preserve the current project session before a local skirt reconstruction."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_SKIRT_V33_STAGE_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
ui=json.loads((ROOT/'reports/CHARACTER_THAI_V32_REVIEW_SESSION_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(ui['reviewFile'])
source_path=bpy.data.filepath;source_hash=sha(source_path);was_dirty=bpy.data.is_dirty
window=bpy.context.window or bpy.context.window_manager.windows[0]
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_SKIRT_V33_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
def signature(obj):
    return {'arrays':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](obj.data)['arrays'].items()},
        'groups':list(obj.vertex_groups.keys()),'weights':hashlib.sha256(h['_weights'](obj.data,len(obj.vertex_groups)).tobytes()).hexdigest()}
body=bpy.data.objects['V32_Complete_Standard_Body_Prototype'];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
actual={'body':signature(body),'head':signature(head)}
assert actual==ui['beforeAfterDataSignatures'],'Live body/head changed; checkpoint preserved, do not overwrite these edits'
with np.load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')as n:
    expectedA=n['armWorld'].copy();expectedR=n['boneRest55'].copy();names=n['names55'].tolist()
arm=bpy.data.objects['V28_Clinical_Standard_Rig']
assert np.max(np.abs(np.array(arm.matrix_world)-expectedA))<1e-7
assert np.array_equal(np.array([np.array(arm.data.bones[name].matrix_local,dtype=float)for name in names]),expectedR)
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_SKIRT_RECONSTRUCTION_V33_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
scene=window.scene;scene.name='REVIEW_THAI_SKIRT_RECONSTRUCTION_V33'
result={'status':'current-project-preserved-and-skirt-work-copy-created','working':str(work),'workingSha256':sha(work),
    'checkpoint':str(cp),'checkpointSha256':sha(cp),'priorReviewFile':source_path,'priorReviewSha256':source_hash,
    'priorReviewFileUnchanged':sha(source_path)==source_hash,'priorLiveDirty':was_dirty,
    'bodyHeadWeightsUVExactlyMatchReviewedV32':True,'nativeRestAndArmWorldMatchV32':True,'scene':scene.name,
    'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'runtimeChanged':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps(result))
