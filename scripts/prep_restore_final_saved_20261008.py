"""Restore the saved master after a fresh Blender launch; preserve current scene."""
import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
master=ROOT/'art/blender/PREPARATORIO_PROJETO_20261008.blend'
assert master.is_file() and master.stat().st_size>1_000_000_000
if Path(bpy.data.filepath or '').resolve()!=master.resolve():
    checkpoint=ROOT/'art/blender/checkpoints/BEFORE_FINAL_RESTORE_20261008.blend'
    index=0
    while checkpoint.exists():
        index+=1;checkpoint=checkpoint.with_name(f'BEFORE_FINAL_RESTORE_20261008_{index:03}.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
    bpy.ops.wm.open_mainfile(filepath=str(master))
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='SOLID'
            area.spaces.active.shading.color_type='MATERIAL'
report={'file':bpy.data.filepath,'version':bpy.app.version_string,'scene':scene.name,'objects':len(scene.objects),'rootCollections':[c.name for c in scene.collection.children],'metric':{'system':scene.unit_settings.system,'scale':scene.unit_settings.scale_length},'vehicleInstanceNames':[o.name for o in scene.objects if o.name.startswith('INTERACTIVE_')],'originalVehicleNames':[o.name for o in scene.objects if o.name.startswith(('SUPPLACE_','VEH_'))],'materialCount':len(bpy.data.materials),'totalArmatures':len([o for o in scene.objects if o.type=='ARMATURE'])}
assert report['objects']>=6521,report
(ROOT/'reports/blender_final_state_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
