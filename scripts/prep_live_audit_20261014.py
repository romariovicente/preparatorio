"""Read-only audit of the Blender MCP instance before resuming work."""
import bpy
import json
from datetime import datetime
from pathlib import Path

project = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
report = {
    'time_local': datetime.now().isoformat(timespec='seconds'),
    'blender_version': bpy.app.version_string,
    'filepath': bpy.data.filepath,
    'dirty': bpy.data.is_dirty,
    'scene': bpy.context.scene.name,
    'scene_objects': len(bpy.context.scene.objects),
    'all_objects': len(bpy.data.objects),
    'scenes': [{'name': s.name, 'objects': len(s.objects)} for s in bpy.data.scenes],
    'armatures': len([o for o in bpy.context.scene.objects if o.type == 'ARMATURE']),
    'materials': len(bpy.data.materials),
    'collections': len(bpy.data.collections),
    'metric': bpy.context.scene.unit_settings.system,
    'scale_length': bpy.context.scene.unit_settings.scale_length,
    'selection': [o.name for o in bpy.context.selected_objects],
}
(project / 'reports/blender_live_audit_20261014.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
