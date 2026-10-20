import bpy,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert not bpy.data.filepath and not bpy.data.is_dirty and len(bpy.data.objects)==3,'Preserve unexpected live changes first'
stamp=datetime.now().strftime('%H%M%S_%f')
startup=ROOT/f'art/blender/checkpoints/DEFAULT_STARTUP_20261020_{stamp}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(startup),copy=True,compress=True)
bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False,load_ui=True)
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert bpy.data.scenes.get('PREP_AMG_ONE_20261019') and bpy.data.scenes.get('PREP_WARP_ENGINE_20261019')
assert bpy.data.scenes.get('PREP_HOSPITAL_CITY_20261019') and len(bpy.data.objects)>16600
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
state=object_state(list(bpy.data.objects));before_bytes=MASTER.stat().st_size
checkpoint=ROOT/f'art/blender/checkpoints/BEFORE_CONTINUATION_20261020_{stamp}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True,compress=True)
with bpy.data.libraries.load(str(checkpoint),link=False) as (source_data,destination_data):
    assert 'PREP_AMG_ONE_20261019' in source_data.scenes and 'PREP_WARP_ENGINE_20261019' in source_data.scenes
snapshot=checkpoint.with_suffix('.objects.json');snapshot.write_text(json.dumps(state,separators=(',',':')),encoding='utf-8')
assert state_hash(object_state(list(bpy.data.objects)))==state_hash(state)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
assert state_hash(object_state(list(bpy.data.objects)))==state_hash(state)
report={'source':str(MASTER),'checkpoint':str(checkpoint),'stateSnapshot':str(snapshot),'stateHash':state_hash(state),
 'sourceBytesBeforeCompression':before_bytes,'sourceBytes':MASTER.stat().st_size,'checkpointBytes':checkpoint.stat().st_size,
 'scenes':len(bpy.data.scenes),'objects':len(state),'activeScene':bpy.context.scene.name,
 'embeddedScriptsDisabled':True,'checkpointLibraryReadValidated':True,'objectChannelsPreserved':True,'startupCheckpoint':str(startup)}
(ROOT/'reports/CONTINUATION_CHECKPOINT_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
