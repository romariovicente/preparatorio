"""Resume from the existing project master after preserving the live scene."""
import bpy
import json
from pathlib import Path

project = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
master = project / 'art/blender/PREPARATORIO_PROJETO_20261008.blend'
checkpoint = project / 'art/blender/checkpoints/BEFORE_RESUME_20261009.blend'
if not checkpoint.is_file() or not master.is_file():
    raise RuntimeError('Preserved session and existing project master are required')
bpy.ops.wm.open_mainfile(filepath=str(master))
scene = bpy.context.scene
report = {
    'blender_version': bpy.app.version_string,
    'filepath': bpy.data.filepath,
    'scene': scene.name,
    'scene_objects': len(scene.objects),
    'root_collections': [c.name for c in scene.collection.children],
    'armatures': [o.name for o in scene.objects if o.type == 'ARMATURE'],
    'units': {'system': scene.unit_settings.system, 'scale_length': scene.unit_settings.scale_length},
    'master_bytes': master.stat().st_size,
    'existing_master_not_overwritten': True,
}
(project / 'reports/blender_reopened_20261009.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
