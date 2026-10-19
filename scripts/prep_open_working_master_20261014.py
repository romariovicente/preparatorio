"""Checkpoint current live state, then resume the preserved master as a new file."""
import bpy
import json
from datetime import datetime
from pathlib import Path

project=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
source=project/'art/blender/PREPARATORIO_PROJETO_20261013.blend'
target=project/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
if target.exists():
    raise FileExistsError(f'New master already exists; inspect before resuming: {target}')
if bpy.data.filepath or len(bpy.data.objects)!=3:
    raise RuntimeError(f'Live state changed since audit: {bpy.data.filepath}, {len(bpy.data.objects)} objects')
stamp=datetime.now().strftime('%H%M%S_%f')
checkpoint=project/f'art/blender/checkpoints/BEFORE_RESUME_20261014_{stamp}.blend'
checkpoint.parent.mkdir(parents=True,exist_ok=True)
saved=bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
if 'FINISHED' not in saved or not checkpoint.is_file():
    raise RuntimeError('Pre-resume checkpoint failed')
opened=bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
if 'FINISHED' not in opened:
    raise RuntimeError('Could not recover master')
scene=bpy.context.scene
saved=bpy.ops.wm.save_as_mainfile(filepath=str(target))
report={'source':str(source),'target':str(target),'checkpoint':str(checkpoint),
        'scene':scene.name,'scene_objects':len(scene.objects),'all_objects':len(bpy.data.objects),
        'scenes':len(bpy.data.scenes),'blender':bpy.app.version_string,
        'save_result':sorted(saved),'saved_bytes':target.stat().st_size,'scripts_enabled':False}
(project/'reports/blender_master_resume_20261014.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
