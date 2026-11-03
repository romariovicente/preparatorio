"""Checkpoint V40 before a separately contracted local volume-preserving study."""
import bpy,json,hashlib,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_LOCAL_VOLUME_V41_STAGE_20261029.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
prior=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_TOPOLOGY_V40_20261029.json').read_text())
oldstage=json.loads((ROOT/'reports/CHARACTER_THAI_TOPOLOGY_V40_STAGE_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(prior['library']) and sha(prior['library'])==prior['sha256']
assert not bpy.data.is_dirty
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
assert u['action_signatures']()==oldstage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in oldstage['meshSignatures'].items())
body=bpy.data.objects[prior['bodyObject']]
arrays=u['helpers']['_snapshot'](body.data)['arrays'];W=u['helpers']['_weights'](body.data,55)
with np.load(prior['archive']) as z:
    assert np.array_equal(arrays['coordinates'],z['actualRestWorld'])
    assert np.array_equal(arrays['triangles'],z['actualTriangles']) and np.array_equal(W,z['actualWeights55'])
modifier=body.modifiers[0]
assert len(body.modifiers)==1 and modifier.type=='ARMATURE' and not modifier.use_deform_preserve_volume
api={n:{'value':getattr(modifier,n),'description':modifier.bl_rna.properties[n].description}
     for n in ['use_multi_modifier','use_deform_preserve_volume','vertex_group','invert_vertex_group','use_vertex_groups','use_bone_envelopes']}
w=bpy.context.window or bpy.context.window_manager.windows[0];scene=w.scene
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_LOCAL_VOLUME_V41_20261029.blend'
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_LOCAL_VOLUME_V41_WORK_20261029.blend'
assert not cp.exists() and not work.exists()
signatures={**oldstage['meshSignatures'],body.name:u['mesh_signature'](body)}
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(cp),compress=True,copy=True)
scene.name='REVIEW_THAI_LOCAL_VOLUME_V41'
with bpy.context.temp_override(window=w):bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
result={'source':prior['library'],'sourceSha256':prior['sha256'],'sourceBody':body.name,
 'actualSourceArchive':prior['archive'],'actualSourceArchiveSha256':prior['archiveSha256'],
 'nativeRig':oldstage['nativeRig'],'poseRig':oldstage['poseRig'],'nativeRestSHA256':oldstage['nativeRestSHA256'],
 'checkpoint':str(cp),'checkpointSha256':sha(cp),'working':str(work),'workingSha256':sha(work),
 'scene':scene.name,'actionSignatures':oldstage['actionSignatures'],'meshSignatures':signatures,
 'ArmatureRNA':api,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['meshSignatures','actionSignatures']}))
