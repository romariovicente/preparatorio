"""Preserve the live scene, then open the verified saved project as today's copy."""
import bpy,json
from pathlib import Path
from datetime import datetime
root=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
source=root/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
target=root/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
if target.exists():
    raise FileExistsError('Inspect existing Oct15 copy instead of recreating it')
before={'filepath':bpy.data.filepath,'dirty':bpy.data.is_dirty,'scene':bpy.context.scene.name,'objects':len(bpy.data.objects)}
if bpy.data.filepath and Path(bpy.data.filepath)!=source:
    raise RuntimeError('Another project is open; preserve and inspect before replacing the view')
if not bpy.data.filepath and len(bpy.data.objects)!=3:
    raise RuntimeError('Unexpected unsaved scene; inspect instead of replacing it')
checkpoint=root/f'art/blender/checkpoints/BEFORE_RESUME_20261015_{datetime.now().strftime("%H%M%S_%f")}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
if not checkpoint.is_file():
    raise RuntimeError('Live checkpoint failed')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
if 'PREP_JALECO_QA_20261014' not in bpy.data.scenes:
    raise RuntimeError('Saved clothing scene missing')
bpy.ops.wm.save_as_mainfile(filepath=str(target))
report={'time_local':datetime.now().isoformat(timespec='seconds'),'before':before,'source':str(source),
        'working_copy':str(target),'checkpoint':str(checkpoint),'saved_bytes':target.stat().st_size,
        'scenes':len(bpy.data.scenes),'objects':len(bpy.data.objects),'legacy_objects':len(bpy.data.scenes['00_ARAPIRACA_CYBER_20261005'].objects)}
(root/'reports/blender_resume_20261015.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
