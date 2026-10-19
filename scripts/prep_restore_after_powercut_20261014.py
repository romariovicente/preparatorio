"""Reopen the last completed master, preserving the fresh live session first."""
import bpy,json
from pathlib import Path
from datetime import datetime
root=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
master=root/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
if bpy.data.filepath or len(bpy.data.objects)!=3 or bpy.data.is_dirty:
    raise RuntimeError('Live session changed after recovery audit; preserve and inspect before opening')
stamp=datetime.now().strftime('%H%M%S_%f')
checkpoint=root/f'art/blender/checkpoints/AFTER_POWERCUT_LIVE_20261014_{stamp}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
if not checkpoint.is_file():
    raise RuntimeError('Fresh session checkpoint failed')
result=bpy.ops.wm.open_mainfile(filepath=str(master),load_ui=True,use_scripts=False)
if 'FINISHED' not in result or Path(bpy.data.filepath)!=master:
    raise RuntimeError('Saved master did not reopen successfully')
scene=bpy.data.scenes.get('PREP_JALECO_QA_20261014')
if scene is None:
    raise RuntimeError('Saved jaleco scene missing; keep recovered file for inspection')
bpy.context.window.scene=scene
legacy=bpy.data.scenes.get('00_ARAPIRACA_CYBER_20261005')
helpers=[o for o in scene.objects if o.get('character_helper_hidden')]
report={'time_local':datetime.now().isoformat(timespec='seconds'),'filepath':bpy.data.filepath,
        'blender':bpy.app.version_string,'active_scene':scene.name,'scene_objects':len(scene.objects),
        'all_scenes':len(bpy.data.scenes),'all_objects':len(bpy.data.objects),
        'legacy_objects':len(legacy.objects) if legacy else None,
        'armatures':[{'name':o.name,'bones':len(o.data.bones)} for o in scene.objects if o.type=='ARMATURE'],
        'auxiliary_helpers_preserved_hidden':all(o.hide_render for o in helpers),'helper_count':len(helpers),
        'metric':scene.unit_settings.system,'scale_length':scene.unit_settings.scale_length,
        'source_not_overwritten':True,'master_bytes':master.stat().st_size,'checkpoint':str(checkpoint)}
(root/'reports/blender_recovered_after_powercut_20261014.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
