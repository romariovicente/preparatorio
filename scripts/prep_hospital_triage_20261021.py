import bpy
import hashlib
import json
import math
from pathlib import Path

from mathutils import Vector


ROOT = Path(r'C:/Users/Senac/Documents/Codex/2026-09-28/referenced-chatgpt-conversation-this-is-an/outputs/preparatorio')
MASTER = ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend'
CHECKPOINT = ROOT / 'art/blender/checkpoints/BEFORE_HOSPITAL_TRIAGE_20261021_1124.blend'
ASSET = ROOT / 'frontend/public/assets/additions20261021/PROP_Hospital_Triage_Terminal_20261021.glb'
LIBRARY = ROOT / 'art/blender/libraries/PREP_HOSPITAL_TRIAGE_TERMINAL_20261021.blend'
PREVIEW = ROOT / 'reports/hospital_triage_terminal_20261021.png'
REPORT = ROOT / 'reports/HOSPITAL_TRIAGE_BLENDER_20261021.json'
SCENE_NAME = 'PREP_HOSPITAL_TRIAGE_TERMINAL_20261021'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def move_to_collection(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def material(name, color, metallic=0.0, roughness=0.45, emission=None):
    value = bpy.data.materials.new(name)
    value.diffuse_color = (*color, 1.0)
    value.use_nodes = True
    principled = next(node for node in value.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    principled.inputs['Base Color'].default_value = (*color, 1.0)
    principled.inputs['Metallic'].default_value = metallic
    principled.inputs['Roughness'].default_value = roughness
    if emission:
        principled.inputs['Emission Color'].default_value = (*emission, 1.0)
        principled.inputs['Emission Strength'].default_value = 3.0
    return value


def finish_mesh(obj, collection, mat, bevel=0.0):
    move_to_collection(obj, collection)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('HSP21_SoftEdges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.select_set(False)
    obj.parent = root
    return obj


def box(name, location, scale, collection, mat, bevel=0.012, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_mesh(obj, collection, mat, bevel)


def cylinder(name, location, radius, depth, collection, mat, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, collection, mat, min(radius * 0.16, 0.008))


def text_mesh(name, body, location, size, collection, mat, rotation=(math.radians(90), 0, 0)):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = 'CENTER'
    obj.data.align_y = 'CENTER'
    obj.data.size = size
    obj.data.extrude = 0.004
    obj.data.bevel_depth = 0.001
    bpy.ops.object.convert(target='MESH')
    return finish_mesh(obj, collection, mat)


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()


if Path(bpy.data.filepath).resolve() != MASTER.resolve():
    raise RuntimeError(f'Unexpected live file: {bpy.data.filepath}')
if not CHECKPOINT.is_file() or CHECKPOINT.stat().st_size != MASTER.stat().st_size:
    raise RuntimeError('Verified pre-triage checkpoint is missing or has the wrong size')
partial = bpy.data.scenes.get(SCENE_NAME)
if partial:
    if REPORT.exists() or ASSET.exists():
        raise RuntimeError('Completed triage terminal output already exists; refusing duplicate work')
    partial_objects = list(partial.objects)
    bpy.data.scenes.remove(partial)
    for obj in partial_objects:
        if obj.users == 0:
            bpy.data.objects.remove(obj)
    for collection in list(bpy.data.collections):
        if collection.name.startswith('HSP21_') and collection.users == 0:
            bpy.data.collections.remove(collection)
    for value in list(bpy.data.materials):
        if value.name.startswith('HSP21_') and value.users == 0:
            bpy.data.materials.remove(value)

old_objects = list(bpy.data.objects)
old_scenes = list(bpy.data.scenes)
old_state = {
    obj.as_pointer(): (
        tuple(round(value, 9) for row in obj.matrix_world for value in row),
        obj.hide_viewport,
        obj.hide_render,
    )
    for obj in old_objects
}

scene = bpy.data.scenes.new(SCENE_NAME)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene['preparatorio_role'] = 'hospital-triage-training-terminal'
scene['clinical_certification'] = False
scene['workflow'] = 'identificacao,registro_simulado,encaminhamento'
for window in bpy.context.window_manager.windows:
    window.scene = scene

model = bpy.data.collections.new('HSP21_TRIAGE_MODEL')
scene.collection.children.link(model)
root = bpy.data.objects.new('HSP21_TRIAGE_ROOT', None)
model.objects.link(root)
root['training_only'] = True
root['no_diagnosis'] = True
root['interaction_steps'] = 3

white = material('HSP21_WhitePolymer', (0.72, 0.82, 0.86), metallic=0.08, roughness=0.30)
dark = material('HSP21_DarkHousing', (0.018, 0.034, 0.045), metallic=0.45, roughness=0.24)
screen = material('HSP21_Screen', (0.015, 0.09, 0.12), metallic=0.12, roughness=0.20, emission=(0.02, 0.60, 0.72))
teal = material('HSP21_Teal', (0.02, 0.48, 0.55), metallic=0.18, roughness=0.28, emission=(0.02, 0.38, 0.46))
green = material('HSP21_Green', (0.04, 0.62, 0.28), roughness=0.28, emission=(0.04, 0.55, 0.20))
yellow = material('HSP21_Yellow', (0.92, 0.60, 0.04), roughness=0.30, emission=(0.75, 0.35, 0.02))
red = material('HSP21_Red', (0.72, 0.05, 0.05), roughness=0.30, emission=(0.55, 0.02, 0.02))

box('HSP21_BASE', (0, 0, 0.035), (0.56, 0.38, 0.07), model, dark, 0.025)
box('HSP21_KEYBOARD', (0, -0.17, 0.11), (0.43, 0.20, 0.045), model, white, 0.016, (math.radians(10), 0, 0))
box('HSP21_SCREEN_CASE', (0, 0.005, 0.30), (0.53, 0.09, 0.35), model, dark, 0.025)
box('HSP21_SCREEN_FACE', (0, -0.046, 0.30), (0.45, 0.012, 0.27), model, screen, 0.010)
box('HSP21_CARD_READER', (0.25, -0.14, 0.12), (0.10, 0.14, 0.07), model, dark, 0.012)
cylinder('HSP21_SENSOR_POST', (-0.235, 0.035, 0.12), 0.018, 0.17, model, white)
cylinder('HSP21_SENSOR_HEAD', (-0.235, 0.035, 0.215), 0.045, 0.065, model, teal, rotation=(math.radians(90), 0, 0))
for name, x, mat in [('GREEN', -0.12, green), ('YELLOW', 0.0, yellow), ('RED', 0.12, red)]:
    cylinder(f'HSP21_STATUS_{name}', (x, -0.061, 0.456), 0.024, 0.012, model, mat, vertices=20, rotation=(math.radians(90), 0, 0))
text_mesh('HSP21_LABEL_TRIAGEM', 'TRIAGEM', (0, -0.064, 0.354), 0.048, model, white)
text_mesh('HSP21_LABEL_TREINO', 'TREINO', (0, -0.064, 0.267), 0.030, model, teal)

bpy.context.view_layer.update()
meshes = [obj for obj in model.objects if obj.type == 'MESH']
points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
minimum = Vector(min(point[index] for point in points) for index in range(3))
maximum = Vector(max(point[index] for point in points) for index in range(3))
dimensions = maximum - minimum
if minimum.z < -0.001 or dimensions.x > 0.70 or dimensions.y > 0.55 or dimensions.z > 0.55:
    raise AssertionError(f'Unexpected terminal bounds: {minimum[:]}, {maximum[:]}')

for obj in scene.objects:
    obj.select_set(False)
root.select_set(True)
for obj in root.children_recursive:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
ASSET.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(ASSET),
    export_format='GLB',
    use_active_scene=True,
    use_selection=True,
    export_animations=False,
    export_extras=True,
    export_yup=True,
)

studio = bpy.data.collections.new('HSP21_TRIAGE_STUDIO')
scene.collection.children.link(studio)
camera_data = bpy.data.cameras.new('HSP21_TRIAGE_CAMERA')
camera = bpy.data.objects.new(camera_data.name, camera_data)
studio.objects.link(camera)
camera.location = (1.25, -1.65, 1.05)
camera_data.lens = 58
camera_data.clip_start = 0.01
point_camera(camera, (0, 0, 0.24))
scene.camera = camera
for name, location, energy, size, color in [
    ('HSP21_KEY', (1.5, -1.2, 2.0), 900, 2.0, (0.82, 0.94, 1.0)),
    ('HSP21_FILL', (-1.4, -0.5, 1.2), 650, 1.8, (0.45, 0.75, 1.0)),
    ('HSP21_RIM', (0.5, 1.4, 1.5), 800, 1.6, (0.10, 0.75, 0.70)),
]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    studio.objects.link(light)
    light.location = location
    point_camera(light, (0, 0, 0.24))
scene.world = bpy.data.worlds.new('HSP21_TRIAGE_WORLD')
scene.world.color = (0.008, 0.015, 0.022)
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(PREVIEW)
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.film_transparent = False
bpy.ops.render.render(write_still=True)

LIBRARY.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(LIBRARY), {scene}, fake_user=True, compress=True)

for obj in old_objects:
    current = (
        tuple(round(value, 9) for row in obj.matrix_world for value in row),
        obj.hide_viewport,
        obj.hide_render,
    )
    if current != old_state[obj.as_pointer()]:
        raise AssertionError(f'Pre-existing object changed: {obj.name}')
for old_scene in old_scenes:
    if bpy.data.scenes.get(old_scene.name) is not old_scene:
        raise AssertionError(f'Pre-existing scene removed: {old_scene.name}')

bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), compress=True)
triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
report = {
    'date': '2026-10-21',
    'passed': True,
    'checkpoint': str(CHECKPOINT),
    'master': str(MASTER),
    'masterBytes': MASTER.stat().st_size,
    'masterSha256': sha256(MASTER),
    'preExistingObjectsVerifiedUnchanged': len(old_objects),
    'preExistingScenesVerifiedPresent': len(old_scenes),
    'scene': SCENE_NAME,
    'asset': str(ASSET),
    'assetBytes': ASSET.stat().st_size,
    'assetSha256': sha256(ASSET),
    'library': str(LIBRARY),
    'libraryBytes': LIBRARY.stat().st_size,
    'librarySha256': sha256(LIBRARY),
    'preview': str(PREVIEW),
    'meshObjects': len(meshes),
    'triangles': triangles,
    'bounds': {
        'min': [float(value) for value in minimum],
        'max': [float(value) for value in maximum],
        'dimensions': [float(value) for value in dimensions],
    },
    'placements': [
        {'id': 'triage-01', 'localPosition': [-5.8, 0.82, -2.25], 'rotation': [0, 0, 0]},
        {'id': 'triage-02', 'localPosition': [5.8, 0.82, -2.25], 'rotation': [0, math.pi, 0]},
    ],
    'workflow': ['identificacao', 'registro_simulado', 'encaminhamento'],
    'trainingOnly': True,
    'diagnosisImplemented': False,
    'clinicalClassificationImplemented': False,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('HOSPITAL_TRIAGE_SAVED ' + json.dumps({
    'assetBytes': report['assetBytes'],
    'assetSha256': report['assetSha256'],
    'triangles': triangles,
    'bounds': report['bounds'],
    'oldObjects': len(old_objects),
    'oldScenes': len(old_scenes),
    'masterBytes': report['masterBytes'],
    'masterSha256': report['masterSha256'],
}, ensure_ascii=False))
