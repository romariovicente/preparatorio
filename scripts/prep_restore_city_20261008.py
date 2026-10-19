import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
checkpoint=ROOT/'art/blender/checkpoints/BEFORE_RESUME_20261008.blend'
checkpoint.parent.mkdir(parents=True,exist_ok=True)
if not checkpoint.exists():bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
latest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261008.blend'
if not latest.exists():latest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261007.blend'
bpy.ops.wm.open_mainfile(filepath=str(latest))
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='CONSOLE':area.type='VIEW_3D'
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_distance=160
            area.spaces.active.region_3d.view_location=(0,0,8)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.frame_end=max(scene.frame_end,6301)
dest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261008.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'saved':str(dest),'checkpoint':str(checkpoint),'scene':scene.name,'sceneObjects':len(scene.objects),'collections':[c.name for c in scene.collection.children],'version':bpy.app.version_string}
(ROOT/'reports/live_resume_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
