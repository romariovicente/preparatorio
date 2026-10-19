import bpy,json
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
assert Path(bpy.data.filepath).resolve()==(ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend').resolve()
p=ROOT/('art/blender/checkpoints/BEFORE_MANUAL_RESUME_20261016_'+datetime.now().strftime('%H%M%S_%f')+'.blend')
before=bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(p),copy=True,check_existing=True)
assert bpy.data.filepath==before and p.stat().st_size>1000000
report={'path':str(p),'bytes':p.stat().st_size,'currentFile':bpy.data.filepath,'objects':len(bpy.data.objects),'scenes':len(bpy.data.scenes),'timeLocal':datetime.now().astimezone().isoformat()}
(ROOT/'reports/CHECKPOINT_MANUAL_RESUME_20261016.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
