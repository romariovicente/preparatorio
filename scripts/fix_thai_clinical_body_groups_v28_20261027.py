"""Restore native vertex-group name mapping after replacing a Blender mesh."""
import bpy,json,hashlib,shutil,runpy
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_CLINICAL_GROUP_FIX_V28_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_CLINICAL_IDENTITY_V28_20261027.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library']) and sha(r['library'])==r['sha256']
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_GROUP_NAME_FIX_V28_20261027.blend'
assert not cp.exists();shutil.copy2(r['library'],cp)
scene=bpy.data.scenes[r['scene']];window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0]
body=bpy.data.objects[r['bodyObject']];source=bpy.data.objects['Body.003'];arm=bpy.data.objects[r['rig']]
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
assert len(body.vertex_groups)==0 and len(source.vertex_groups)==55
before=h['_weights'](body.data,55)
for vg in source.vertex_groups:body.vertex_groups.new(name=vg.name)
after=h['_weights'](body.data,55)
assert np.array_equal(before,after) and list(body.vertex_groups.keys())==list(source.vertex_groups.keys())
idle=bpy.data.actions[r['nativeClips']['Idle']['action']];arm.animation_data.action=idle;arm.animation_data.action_slot=idle.slots[0]
scene.frame_set(1);layer.update()
body['PREP_native_vertex_group_names_restored']=True
path=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_CLINICAL_BODY_V28_GROUPS_FIXED_20261027.blend'
assert not path.exists()
with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
result={'status':'native-group-name-mapping-restored-awaiting-render','library':str(path),'sha256':sha(path),
        'checkpoint':str(cp),'checkpointSha256':sha(cp),'previousLibrary':r['library'],'previousSha256':r['sha256'],
        'restoredGroupNames':list(body.vertex_groups.keys()),'rawWeightsBitExact':True,'nativeRigOrActionsEdited':False,
        'runtimeChanged':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps(result))
