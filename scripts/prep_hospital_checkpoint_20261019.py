import bpy, json, sys
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert 'PREP_HOSPITAL_CITY_20261019' not in bpy.data.scenes, 'Inspect the existing integration before editing again'
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state, state_hash
stamp=datetime.now().strftime('%H%M%S_%f')
checkpoint=ROOT/f'art/blender/checkpoints/BEFORE_HOSPITAL_CITY_20261019_{stamp}.blend'
assert not checkpoint.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True,check_existing=True)
assert bpy.data.filepath==str(MASTER) and checkpoint.stat().st_size>1_000_000_000
state=object_state(list(bpy.data.objects))
snapshot=ROOT/f'art/blender/checkpoints/HOSPITAL_CITY_OBJECTS_20261019_{stamp}.json'
snapshot.write_text(json.dumps(state,separators=(',',':')),encoding='utf-8')
report={'checkpoint':str(checkpoint),'bytes':checkpoint.stat().st_size,
        'stateSnapshot':str(snapshot),'stateHash':state_hash(state),'objects':len(state),
        'scenes':len(bpy.data.scenes),'source':str(MASTER),'activeScene':bpy.context.scene.name,
        'timeLocal':datetime.now().astimezone().isoformat()}
(ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
