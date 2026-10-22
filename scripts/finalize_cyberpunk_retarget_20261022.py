"""Freeze legacy facial morph tracks; export only the accepted locomotion set."""
import bpy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
blend=ROOT/'art/blender/libraries/PREP_CHARACTER_CYBERPUNK_REMY_RETARGET_20261022_v2.blend'
glb=ROOT/'art/character_retarget_20261022/CHR_Cyberpunk_Remy_Retarget_20261022_v2.glb'
report_path=ROOT/'reports/CHARACTER_CYBERPUNK_REMY_RETARGET_20261022_v2.json'
assert Path(bpy.data.filepath).resolve()==blend.resolve()
scene=bpy.data.scenes['PREP_CHARACTER_CYBERPUNK_REMY_RETARGET_20261022']
bpy.context.window.scene=scene
arm=next(obj for obj in scene.objects if obj.type=='ARMATURE')
for track in arm.animation_data.nla_tracks:
    track.mute=track.name!='Idle'
scene.frame_set(1)
bpy.context.view_layer.update()
removed=[]
for obj in scene.objects:
    if obj.type!='MESH' or obj.parent!=arm:
        continue
    keys=obj.data.shape_keys
    if keys and keys.animation_data:
        values={key.name:key.value for key in keys.key_blocks}
        keys.animation_data_clear()
        for key in keys.key_blocks:
            key.value=values[key.name]
        removed.append(obj.name)
for track in arm.animation_data.nla_tracks:
    track.mute=False
bpy.ops.object.select_all(action='DESELECT')
root=arm
while root.parent:
    root=root.parent
for obj in [root,*root.children_recursive]:
    obj.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,use_active_scene=True,
                         export_yup=True,export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',
                         export_cameras=False,export_lights=False,export_extras=True)
for track in arm.animation_data.nla_tracks:
    track.mute=track.name!='Idle'
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
report=json.loads(report_path.read_text(encoding='utf-8'))
for key,path in [('blend',blend),('glb',glb)]:
    report[key]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
report['legacyFacialMorphTracksFrozen']=removed
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'legacyFacialMorphTracksFrozen':len(removed),'glb':report['glb']}))
