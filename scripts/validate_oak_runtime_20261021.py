import bpy
import json
from mathutils import Vector
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'frontend/public/assets/environment/runtime/ENV_Oak_Small_001_LOD0_20261021.glb'
REPORT = ROOT / 'reports/OAK_RUNTIME_20261021.json'
PREVIEW = ROOT / 'reports/oak_small_001_lod0_20261021.png'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(TARGET))
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
triangles = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in meshes)
if len(meshes) != 2 or triangles != 1217:
    raise AssertionError({'meshes': len(meshes), 'triangles': triangles})
corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
minimum = Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners)))
maximum = Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))
size = maximum - minimum
if abs((minimum.x + maximum.x) / 2) > .001 or abs((minimum.y + maximum.y) / 2) > .001 or abs(minimum.z) > .001:
    raise AssertionError({'min': list(minimum), 'max': list(maximum)})

scene.world = bpy.data.worlds.new('OakRuntimeReviewWorld'); scene.world.color = (.08, .1, .08)
bpy.ops.object.light_add(type='AREA', location=(size.x, -size.y, maximum.z + size.z * .5))
bpy.context.object.data.energy = 1100; bpy.context.object.data.size = max(size.x, size.y, 4)
center = (minimum + maximum) / 2
bpy.ops.object.camera_add(location=(size.x * 1.8, -size.y * 2.4, center.z + size.z * .35))
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'; camera.data.ortho_scale = max(size) * 1.25; scene.camera = camera
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = 700; scene.render.resolution_y = 800
scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = 'PNG'; scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)

report = json.loads(REPORT.read_text(encoding='utf-8'))
report.update({'reimportValidated': True, 'triangles': triangles, 'meshCount': len(meshes),
               'bounds': {'min': list(minimum), 'max': list(maximum), 'size': list(size)}, 'preview': str(PREVIEW)})
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('OAK_RUNTIME_VALIDATED ' + json.dumps({'meshes': len(meshes), 'triangles': triangles, 'bounds': report['bounds'], 'preview': str(PREVIEW)}))
