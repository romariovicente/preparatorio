import bpy,json
from pathlib import Path
from datetime import datetime
root=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
report={'time_local':datetime.now().isoformat(timespec='seconds'),'blender':bpy.app.version_string,
        'filepath':bpy.data.filepath,'dirty':bpy.data.is_dirty,'scene':bpy.context.scene.name,
        'objects':len(bpy.context.scene.objects),'all_objects':len(bpy.data.objects),
        'scenes':[s.name for s in bpy.data.scenes],'armatures':len([o for o in bpy.context.scene.objects if o.type=='ARMATURE'])}
(root/'reports/blender_audit_after_powercut_20261014.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
