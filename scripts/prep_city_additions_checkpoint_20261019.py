import bpy,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve(), 'Preserve and inspect another open file before proceeding'
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
stamp=datetime.now().strftime('%H%M%S_%f')
target=ROOT/f'art/blender/checkpoints/BEFORE_CITY_ADDITIONS_20261019_{stamp}.blend'
dirty=bpy.data.is_dirty
bpy.ops.wm.save_as_mainfile(filepath=str(target),copy=True,check_existing=True)
assert target.exists() and bpy.data.filepath==str(MASTER)
state=object_state(list(bpy.data.objects))
snapshot=target.with_suffix('.objects.json');snapshot.write_text(json.dumps(state,separators=(',',':')),encoding='utf-8')
report={'source':str(MASTER),'checkpoint':str(target),'bytes':target.stat().st_size,
        'stateSnapshot':str(snapshot),'stateHash':state_hash(state),'objects':len(state),'scenes':len(bpy.data.scenes),
        'activeScene':bpy.context.scene.name,'dirtyBeforeCheckpoint':dirty,
        'guardianRegistered':bool(bpy.app.driver_namespace.get('PREPARATORIO_AUTOSAVE_GUARDIAN') and bpy.app.timers.is_registered(bpy.app.driver_namespace['PREPARATORIO_AUTOSAVE_GUARDIAN'])),
        'timeLocal':datetime.now().astimezone().isoformat()}
(ROOT/'reports/CITY_ADDITIONS_CHECKPOINT_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
