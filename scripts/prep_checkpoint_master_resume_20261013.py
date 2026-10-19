"""Save one unique copy of the current Blender session; preserve its active path."""
import bpy
import json
from datetime import datetime
from pathlib import Path

PROJECT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
checkpoint = PROJECT / f'art/blender/checkpoints/BEFORE_MASTER_RESUME_20261013_{stamp}.blend'
if checkpoint.exists():
    raise FileExistsError(f'Checkpoint exists; refusing replacement: {checkpoint}')
checkpoint.parent.mkdir(parents=True, exist_ok=True)
original_filepath = bpy.data.filepath
selected = [o.name for o in bpy.context.selected_objects]
active = bpy.context.active_object.name if bpy.context.active_object else None
report = {'time_local': datetime.now().isoformat(timespec='seconds'), 'original_filepath': original_filepath,
    'scene': bpy.context.scene.name, 'object_count': len(bpy.context.scene.objects), 'checkpoint': str(checkpoint),
    'copy_requested': True, 'selected_before': selected, 'active_before': active}
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
report['operator_result'] = sorted(result)
report['checkpoint_exists'] = checkpoint.is_file()
report['checkpoint_bytes'] = checkpoint.stat().st_size if checkpoint.is_file() else 0
report['filepath_after'] = bpy.data.filepath
report['original_filepath_preserved'] = bpy.data.filepath == original_filepath
report['selection_preserved'] = [o.name for o in bpy.context.selected_objects] == selected
report['active_preserved'] = (bpy.context.active_object.name if bpy.context.active_object else None) == active
report_path = PROJECT / 'reports/blender_master_resume_checkpoint_20261013.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
if 'FINISHED' not in result or not report['checkpoint_exists'] or not report['checkpoint_bytes'] or not report['original_filepath_preserved']:
    raise RuntimeError('Checkpoint save or active filepath preservation failed; inspect the report')
