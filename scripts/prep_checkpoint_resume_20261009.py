"""Preserve the live Blender session before resuming work, without changing it."""
import bpy
import json
from pathlib import Path

project = Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
checkpoint = project / 'art/blender/checkpoints/BEFORE_RESUME_20261009.blend'
if checkpoint.exists():
    raise FileExistsError(f'Checkpoint already exists: {checkpoint}')
checkpoint.parent.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
report = {
    'blender_version': bpy.app.version_string,
    'original_filepath': bpy.data.filepath,
    'scene': scene.name,
    'scene_objects': len(scene.objects),
    'root_collections': [c.name for c in scene.collection.children],
    'armatures': [o.name for o in scene.objects if o.type == 'ARMATURE'],
    'material_datablocks': len(bpy.data.materials),
    'units': {'system': scene.unit_settings.system, 'scale_length': scene.unit_settings.scale_length},
    'checkpoint': str(checkpoint),
}
result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
if 'FINISHED' not in result or not checkpoint.is_file():
    raise RuntimeError('Live Blender checkpoint was not saved')
report['checkpoint_bytes'] = checkpoint.stat().st_size
report['original_filepath_preserved'] = bpy.data.filepath == report['original_filepath']
(project / 'reports/blender_resume_20261009.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
