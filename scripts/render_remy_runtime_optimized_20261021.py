"""Render the optimized SENAC runtime GLB in independently reimported poses."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'frontend/public/assets/characters/runtime/CHR_Remy_Senac_Uniform_Web_20261021.glb'
OUT = ROOT / 'reports/costumes'
OUT.mkdir(parents=True, exist_ok=True)


def render(mode):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET))
    scene = bpy.context.scene
    armature = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    for obj in scene.objects:
        if obj.name.startswith(('Tops', 'Bottoms')):
            obj.hide_render = True
        if obj.name.startswith('COAT_'):
            obj.hide_render = mode == 'scrubs'
        if obj.name.startswith('SCRUB_'):
            obj.hide_render = mode != 'scrubs' and 'Trouser' not in obj.name
    if armature.animation_data:
        armature.animation_data.action = None
        requested = 'Walk' if mode == 'walk' else 'Idle'
        for track in armature.animation_data.nla_tracks:
            track.mute = requested not in track.name
    scene.frame_set(13 if mode == 'walk' else 1)
    bpy.context.view_layer.update()
    scene.world = bpy.data.worlds.new('RuntimeReviewWorld')
    scene.world.color = (0.18, 0.18, 0.18)
    for location, power in [((2, -3, 3), 450), ((-2, -2, 2.5), 250)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        bpy.context.object.data.energy = power
        bpy.context.object.data.size = 4
    focus = Vector((0, -0.15, 0.9))
    bpy.ops.object.camera_add(location=(1.7, -4, 1.65))
    camera = bpy.context.object
    camera.rotation_euler = (focus - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.15
    scene.camera = camera
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / f'remy_uniform_runtime_{mode}_20261021.png')
    bpy.ops.render.render(write_still=True)
    print('RUNTIME_UNIFORM_PREVIEW ' + json.dumps({'pose': mode, 'file': scene.render.filepath}))


for mode in ['scrubs', 'walk']:
    render(mode)
