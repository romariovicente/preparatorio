"""Extract one audited game-ready oak from the supplied 17-variant LOD pack."""
import bpy
import hashlib
import json
from mathutils import Vector
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:/Users/Senac/Downloads/NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode/Tudo pra colocar no jogo/Floresta pro Jogo/oak_trees_pack_17var_lods_seasons_gameready.glb')
TARGET = ROOT / 'frontend/public/assets/environment/runtime/ENV_Oak_Small_001_LOD0_20261021.glb'
LIBRARY = ROOT / 'art/blender/libraries/ENV_Oak_Small_001_LOD0_20261021.blend'
PREVIEW = ROOT / 'reports/oak_small_001_lod0_20261021.png'
REPORT = ROOT / 'reports/OAK_RUNTIME_20261021.json'
TARGET.parent.mkdir(parents=True, exist_ok=True)
LIBRARY.parent.mkdir(parents=True, exist_ok=True)

source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene
root = bpy.data.objects.get('Small_oak_tree__001_LOD0')
if not root:
    raise RuntimeError('Expected Small_oak_tree__001_LOD0 hierarchy is absent')

def descendants(obj):
    result = []
    for child in obj.children:
        result.append(child)
        result.extend(descendants(child))
    return result

selected = [root, *descendants(root)]
meshes = [obj for obj in selected if obj.type == 'MESH']
if len(meshes) != 2:
    raise AssertionError(f'Expected bark and cluster meshes, found {len(meshes)}')
triangles = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in meshes)
if triangles != 1217:
    raise AssertionError(f'Unexpected triangle count: {triangles}')

# Detach the selected LOD root while preserving its world transform. This keeps
# no dependency on the rest of the 153 MB source hierarchy.
world = root.matrix_world.copy()
root.parent = None
root.matrix_world = world
# Normalize the isolated tree around the origin with its lowest point on Z=0.
source_corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
source_min = Vector((min(point.x for point in source_corners), min(point.y for point in source_corners), min(point.z for point in source_corners)))
source_max = Vector((max(point.x for point in source_corners), max(point.y for point in source_corners), max(point.z for point in source_corners)))
root.location += Vector((-(source_min.x + source_max.x) / 2, -(source_min.y + source_max.y) / 2, -source_min.z))
bpy.context.view_layer.update()
for image in bpy.data.images:
    if image.name in {'Render Result', 'Viewer Node'} or not image.has_data:
        continue
    longest = max(image.size)
    if longest > 1024:
        scale = 1024 / longest
        image.scale(max(1, round(image.size[0] * scale)), max(1, round(image.size[1] * scale)))

for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in selected:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.wm.save_as_mainfile(filepath=str(LIBRARY), compress=True)
bpy.ops.export_scene.gltf(
    filepath=str(TARGET), export_format='GLB', use_selection=True,
    export_yup=True, export_animations=False, export_lights=False,
    export_cameras=False, export_extras=True,
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != source_hash:
    raise AssertionError('Supplied source changed during extraction')

# Reimport the output for bounds and render validation.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(TARGET))
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
triangles_after = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in meshes)
if triangles_after != triangles:
    raise AssertionError(f'Exported triangles changed: {triangles_after}')
corners = []
for obj in meshes:
    corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
minimum = Vector((min(point.x for point in corners), min(point.y for point in corners), min(point.z for point in corners)))
maximum = Vector((max(point.x for point in corners), max(point.y for point in corners), max(point.z for point in corners)))
size = maximum - minimum
center = (minimum + maximum) / 2
scene.world = bpy.data.worlds.new('OakReviewWorld')
scene.world.color = (0.08, 0.1, 0.08)
bpy.ops.object.light_add(type='AREA', location=(center.x + size.x, center.y - size.y, maximum.z + size.z * .5))
bpy.context.object.data.energy = 1100
bpy.context.object.data.size = max(size.x, size.y, 4)
bpy.ops.object.camera_add(location=(center.x + size.x * 1.8, center.y - size.y * 2.4, center.z + size.z * .35))
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = max(size.x, size.y, size.z) * 1.25
scene.camera = camera
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 700
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)

record = {
    'date': '2026-10-21',
    'passed': True,
    'id': 'ENV_Oak_Small_001_LOD0_20261021',
    'url': '/assets/environment/runtime/ENV_Oak_Small_001_LOD0_20261021.glb',
    'bytes': TARGET.stat().st_size,
    'sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
    'triangles': triangles_after,
    'meshCount': len(meshes),
    'bounds': {'min': list(minimum), 'max': list(maximum), 'size': list(size)},
    'source': str(SOURCE),
    'sourceBytes': SOURCE.stat().st_size,
    'sourceSha256': source_hash,
    'sourceNode': 'Small_oak_tree__001_LOD0',
    'sourceLicense': 'CC-BY-4.0',
    'sourceAuthor': 'LOLIPOP (https://sketchfab.com/lolipop_1707)',
    'sourceUrl': 'https://sketchfab.com/3d-models/oak-trees-pack-17var-lods-seasons-gameready-a5e4e64f9f1d4089bdcc6170a9333393',
    'library': str(LIBRARY),
    'preview': str(PREVIEW),
    'method': 'One authored LOD0 hierarchy extracted in Blender; textures capped at 1024 px; source preserved.',
}
REPORT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('OAK_RUNTIME_READY ' + json.dumps(record, ensure_ascii=False))
