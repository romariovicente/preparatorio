"""Checkpoint the exact live project before local arm/hand surface correction."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_HAND_CLEARANCE_V34_STAGE_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_CONTINUOUS_SKIRT_V33_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library']) and sha(r['library'])==r['sha256'] and not bpy.data.is_dirty
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=window.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_HAND_CLEARANCE_V34_20261028.blend';assert not cp.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(cp),copy=True,compress=True)
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
def signature(obj):
    return {'arrays':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](obj.data)['arrays'].items()},
        'groups':list(obj.vertex_groups.keys()),'weights':hashlib.sha256(h['_weights'](obj.data,len(obj.vertex_groups)).tobytes()).hexdigest()}
def action_signatures():
    rows={}
    for clip in ['Idle.002','Walk.002','Dance.002','Interact.002']:
        action=bpy.data.actions[clip];curves=[]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        points=[]
                        for k in fc.keyframe_points:points.append([*k.co,*k.handle_left,*k.handle_right,k.interpolation,k.easing,k.handle_left_type,k.handle_right_type])
                        curves.append([fc.data_path,fc.array_index,fc.extrapolation,points])
        assert curves,clip
        rows[clip]={'curveCount':len(curves),'sha256':hashlib.sha256(json.dumps(curves,separators=(',',':')).encode()).hexdigest()}
    return rows
body=bpy.data.objects['V32_Complete_Standard_Body_Prototype'];arm=bpy.data.objects['V28_Clinical_Standard_Rig']
with np.load(ROOT/'reports/thai_complete_anatomical_base_v32_20261028/derived_body_bind_v32.npz')as f:
    assert np.array_equal(h['_snapshot'](body.data)['arrays']['coordinates'],f['restWorld'])
    assert np.array_equal(h['_weights'](body.data,55),f['weights55'])
    names=f['names55'].tolist();R=f['boneRest55'].copy();A=f['armWorld'].copy()
assert np.array_equal(np.array([np.array(arm.data.bones[n].matrix_local,dtype=float)for n in names]),R)
assert np.max(np.abs(np.array(arm.matrix_world,dtype=float)-A))<1e-7
preserve=['V32_Complete_Standard_Body_Prototype','V28_Thai_Face_And_Hair_Preserved','V30_ORIGINAL_SHIRT_Regional_Bind_Pilot',
    'V30_ORIGINAL_SKIRT_Regional_Bind_Pilot','V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape']
signatures={n:signature(bpy.data.objects[n])for n in preserve};actions=action_signatures()
scene.name='REVIEW_THAI_HAND_CLEARANCE_V34'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_HAND_CLEARANCE_V34_WORK_20261028.blend';assert not work.exists()
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={'status':'checkpoint-and-local-hand-correction-work-copy-created','source':r['library'],'sourceSha256':r['sha256'],
    'checkpoint':str(cp),'checkpointSha256':sha(cp),'working':str(work),'workingSha256':sha(work),'scene':scene.name,
    'meshSignatures':signatures,'actionSignatures':actions,'nativeArmWorld':A.tolist(),'nativeRestSHA256':hashlib.sha256(R.tobytes()).hexdigest(),
    'sourceUnchanged':sha(r['library'])==r['sha256'],'bodyBaseMatchesV32':True,'newWindowOpened':False,
    'MCPUsed':True,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['meshSignatures','nativeArmWorld']}))
