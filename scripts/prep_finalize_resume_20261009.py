"""Inspect the current live scene and preserve unsaved user work as a new copy."""
import bpy
import json
from datetime import datetime
from pathlib import Path

project = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
scene = bpy.context.scene
original_filepath = bpy.data.filepath
dirty_before = bpy.data.is_dirty
report = {
    'checked_at': datetime.now().astimezone().isoformat(),
    'blender_version': bpy.app.version_string,
    'filepath': original_filepath,
    'scene': scene.name,
    'scene_objects': len(scene.objects),
    'root_collections': [c.name for c in scene.collection.children],
    'armatures': [o.name for o in scene.objects if o.type == 'ARMATURE'],
    'material_datablocks': len(bpy.data.materials),
    'units': {'system': scene.unit_settings.system, 'scale_length': scene.unit_settings.scale_length},
    'unsaved_changes_before': dirty_before,
    'current_file_not_overwritten': True,
    'new_geometry_created': False,
}
if dirty_before:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    checkpoint = project / 'art/blender/checkpoints' / f'LIVE_PRESERVED_{stamp}.blend'
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if checkpoint.exists():
        raise FileExistsError(checkpoint)
    result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
    if 'FINISHED' not in result or not checkpoint.is_file():
        raise RuntimeError('Current Blender session could not be preserved')
    report['checkpoint'] = str(checkpoint)
    report['checkpoint_bytes'] = checkpoint.stat().st_size
report['original_filepath_preserved'] = bpy.data.filepath == original_filepath
master = project / 'art/blender/PREPARATORIO_PROJETO_20261008.blend'
report['master_bytes_now'] = master.stat().st_size if master.is_file() else None
(project / 'reports/blender_final_state_20261009.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
