"""Open the latest existing master only after preserving the live session."""
import bpy
import json
from datetime import datetime
from pathlib import Path

project = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
preserved = json.loads((project / 'reports/blender_final_state_20261009.json').read_text(encoding='utf-8'))
if preserved['unsaved_changes_before'] and not Path(preserved['checkpoint']).is_file():
    raise RuntimeError('Live session checkpoint is required before restoration')
master = project / 'art/blender/PREPARATORIO_PROJETO_20261008.blend'
if not master.is_file():
    raise FileNotFoundError(master)
size_before = master.stat().st_size
bpy.ops.wm.open_mainfile(filepath=str(master))
scene = bpy.context.scene
report = {
    'checked_at': datetime.now().astimezone().isoformat(),
    'blender_version': bpy.app.version_string,
    'filepath': bpy.data.filepath,
    'scene': scene.name,
    'scene_objects': len(scene.objects),
    'root_collections': [c.name for c in scene.collection.children],
    'armatures': [o.name for o in scene.objects if o.type == 'ARMATURE'],
    'material_datablocks': len(bpy.data.materials),
    'units': {'system': scene.unit_settings.system, 'scale_length': scene.unit_settings.scale_length},
    'master_bytes': master.stat().st_size,
    'existing_master_not_overwritten': master.stat().st_size == size_before,
    'prior_live_checkpoint': preserved.get('checkpoint'),
}
(project / 'reports/blender_final_reopen_20261009.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
