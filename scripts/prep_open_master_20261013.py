"""Restore only the independently validated 2026-10-13 working master."""
import bpy
import json
from datetime import datetime
from pathlib import Path

PROJECT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
checkpoint = json.loads((PROJECT / 'reports/blender_master_resume_checkpoint_20261013.json').read_text(encoding='utf-8'))
copy_report = json.loads((PROJECT / 'reports/blender_master_copy_20261013.json').read_text(encoding='utf-8'))
master = Path(copy_report['target'])
if not Path(checkpoint['checkpoint']).is_file() or not checkpoint['original_filepath_preserved']:
    raise RuntimeError('Validated live checkpoint is required')
if not copy_report['hashes_match'] or not master.is_file() or master.stat().st_size != copy_report['target_bytes']:
    raise RuntimeError('Validated working copy is required')
if bpy.data.is_dirty:
    raise RuntimeError('Live session changed after checkpoint; audit and preserve it before reopening')
bpy.ops.wm.open_mainfile(filepath=str(master), load_ui=False, use_scripts=False)
report = {'time_local': datetime.now().isoformat(timespec='seconds'), 'filepath': bpy.data.filepath,
    'blender_version': bpy.app.version_string, 'scene': bpy.context.scene.name,
    'scene_objects': len(bpy.context.scene.objects), 'all_scene_names': [s.name for s in bpy.data.scenes],
    'root_collections': [c.name for c in bpy.context.scene.collection.children],
    'armatures': [o.name for o in bpy.context.scene.objects if o.type == 'ARMATURE'],
    'units': {'system': bpy.context.scene.unit_settings.system, 'scale_length': bpy.context.scene.unit_settings.scale_length},
    'master_bytes': master.stat().st_size, 'opened_new_copy_only': bpy.data.filepath == str(master),
    'prior_live_checkpoint': checkpoint['checkpoint'], 'scripts_disabled_on_load': True}
(PROJECT / 'reports/blender_master_recovered_20261013.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
