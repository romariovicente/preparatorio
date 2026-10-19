"""Read live scene state before integrating the user's newly supplied assets."""
import bpy,json
from datetime import datetime
from pathlib import Path
ROOT=Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
report={'timeLocal':datetime.now().astimezone().isoformat(timespec='seconds'),'filepath':bpy.data.filepath,
        'dirty':bpy.data.is_dirty,'objects':len(bpy.data.objects),'scenes':[{'name':s.name,'objects':len(s.objects)} for s in bpy.data.scenes],
        'windows':[w.scene.name for w in bpy.context.window_manager.windows],'version':bpy.app.version_string,
        'timerRegistered':bool(bpy.app.driver_namespace.get('PREPARATORIO_AUTOSAVE_GUARDIAN') and bpy.app.timers.is_registered(bpy.app.driver_namespace['PREPARATORIO_AUTOSAVE_GUARDIAN']))}
(ROOT/'reports/BLENDER_LIVE_AUDIT_20261016.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
