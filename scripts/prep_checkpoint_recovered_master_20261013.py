"""Preserve recovered Oct13 master before clothes integration, without replacing it."""
import bpy
import json
from datetime import datetime
from pathlib import Path

PROJECT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
expected = PROJECT / 'art/blender/PREPARATORIO_PROJETO_20261013.blend'
if Path(bpy.data.filepath) != expected:
    raise RuntimeError(f'Expected recovered Oct13 working master, found {bpy.data.filepath}')
stamp = datetime.now().strftime('%H%M%S_%f')
checkpoint = PROJECT / f'art/blender/checkpoints/RECOVERED_MASTER_BEFORE_CLOTHING_20261013_{stamp}.blend'
if checkpoint.exists():
    raise FileExistsError(checkpoint)
original = bpy.data.filepath
report = {'time_local': datetime.now().isoformat(timespec='seconds'), 'original_filepath': original,
    'scene': bpy.context.scene.name, 'object_count': len(bpy.context.scene.objects), 'checkpoint': str(checkpoint)}
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
report.update({'operator_result': sorted(result), 'checkpoint_exists': checkpoint.is_file(),
    'checkpoint_bytes': checkpoint.stat().st_size if checkpoint.is_file() else 0,
    'filepath_after': bpy.data.filepath, 'filepath_preserved': bpy.data.filepath == original})
(PROJECT / 'reports/blender_recovered_checkpoint_20261013.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
if 'FINISHED' not in result or not report['checkpoint_bytes'] or not report['filepath_preserved']:
    raise RuntimeError('Recovery checkpoint failed')
