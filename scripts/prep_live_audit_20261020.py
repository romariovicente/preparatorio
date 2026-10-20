import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
report={'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'scenes':len(bpy.data.scenes),'objects':len(bpy.data.objects),
 'activeScene':bpy.context.scene.name,'windows':len(bpy.context.window_manager.windows),
 'newScenes':[s.name for s in bpy.data.scenes if s.name.startswith(('PREP_AMG_ONE','PREP_WARP','PREP_CITY_LIVING','PREP_CHARACTERS_CITY'))],
 'guardianRegistered':bool(bpy.app.driver_namespace.get('PREPARATORIO_AUTOSAVE_GUARDIAN') and bpy.app.timers.is_registered(bpy.app.driver_namespace['PREPARATORIO_AUTOSAVE_GUARDIAN']))}
(ROOT/'reports/BLENDER_LIVE_AUDIT_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
