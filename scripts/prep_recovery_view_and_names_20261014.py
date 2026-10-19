"""Verify the recovered file and render genuine cloth name close-ups."""
import bpy,json
from pathlib import Path
from datetime import datetime
from mathutils import Vector
root=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
master=root/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
if Path(bpy.data.filepath)!=master:
    raise RuntimeError('Expected recovered working master')
scene=bpy.data.scenes['PREP_JALECO_QA_20261014']
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_perspective='CAMERA'
checkpoint=root/f'art/blender/checkpoints/RECOVERED_POWERCUT_20261014_{datetime.now().strftime("%H%M%S_%f")}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
if not checkpoint.is_file():
    raise RuntimeError('Recovery checkpoint failed')
for obj in scene.objects:
    if obj.type=='FONT':
        if obj.data.body in ('Romario Vicente Amaro','Ana Clara'):
            obj.location.y=.30
            obj.location.z=1.77
            obj.data.size=.075
        if obj.data.body=='55 ossos | 1,70 m':
            obj.hide_render=True
            obj.hide_set(True)
camera=scene.camera
saved_matrix=camera.matrix_world.copy()
saved_scale=camera.data.ortho_scale
saved_path=scene.render.filepath
saved_size=(scene.render.resolution_x,scene.render.resolution_y)
closeups=[]
scene.render.resolution_x=1024
scene.render.resolution_y=1024
for key in ('ROMARIO','ANA'):
    mesh=bpy.data.objects[f'{key}_COAT_NAME_Remy_Player']
    depsgraph=bpy.context.evaluated_depsgraph_get()
    evaluated=mesh.evaluated_get(depsgraph)
    points=[evaluated.matrix_world@Vector(v) for v in evaluated.bound_box]
    focus=sum(points,Vector())/8
    camera.location=focus+Vector((0,-2,.02))
    camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=.32
    scene.render.filepath=str(root/f'reports/costumes/jaleco_nome_{key.lower()}_20261014.png')
    bpy.ops.render.render(write_still=True,scene=scene.name)
    closeups.append(scene.render.filepath)
camera.matrix_world=saved_matrix
camera.data.ortho_scale=saved_scale
scene.render.resolution_x,scene.render.resolution_y=saved_size
scene.render.filepath=saved_path
bpy.ops.render.render(write_still=True,scene=scene.name)
bpy.ops.wm.save_as_mainfile(filepath=str(master))
legacy=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
helpers=[o for o in scene.objects if o.get('character_helper_hidden')]
report={'time_local':datetime.now().isoformat(timespec='seconds'),'filepath':str(master),'master_bytes':master.stat().st_size,
        'active_scene':scene.name,'scene_objects':len(scene.objects),'legacy_objects_preserved':len(legacy.objects),
        'scenes':len(bpy.data.scenes),'all_objects':len(bpy.data.objects),'metric':scene.unit_settings.system,
        'scale_length':scene.unit_settings.scale_length,'rigs':[{'name':o.name,'bones':len(o.data.bones)} for o in scene.objects if o.type=='ARMATURE'],
        'helper_count':len(helpers),'helpers_hidden':all(o.hide_render for o in helpers),'checkpoint':str(checkpoint),
        'closeups':closeups,'preview':saved_path,'save_verified':master.is_file()}
(root/'reports/blender_recovered_after_powercut_20261014.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
