"""Run in the current Blender session via MCP, never in a background process.

Creates one independent AMGO19 scene and a derivative from the hash-checked
original. Mesh data, UVs, split normals, materials and original faces remain
intact. Only paint/carbon opacity changes. Door pivots are a declared visual
adaptation because the supplied door component origins are all (0, 0, 0).
"""
from pathlib import Path
import bpy, hashlib, json, math, re, struct
from datetime import datetime
from mathutils import Matrix, Vector

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE = Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Veiculos\Transparency Mercedes AMG One\transparency_mercedes_amg_one.glb')
SOURCE_SHA = '951afc9a529f94ddcf1b8480de8356e0e381f9e832f9588985e5d2f6897b6a0a'
OUTPUT = ROOT / 'frontend/public/assets/additions20261019/VEH_Mercedes_AMG_One_Interactive_20261019.glb'
REPORT = ROOT / 'reports/AMG_ONE_BLENDER_20261019.json'
SCENE_NAME = 'PREP_AMG_ONE_20261019'
TARGET_HEIGHT = 1.26

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bounds(objects):
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ Vector(p) for obj in objects for p in obj.bound_box]
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))

def lineage(obj):
    names = []
    while obj:
        names.append(obj.name)
        obj = obj.parent
    return ' '.join(names)

def triangles(objects):
    return sum(len(poly.vertices)-2 for obj in objects for poly in obj.data.polygons)

def empty(collection, name, parent=None, position=(0, 0, 0)):
    obj = bpy.data.objects.new('AMGO19_' + name, None)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = position
    obj['asset_node_name'] = name
    return obj

master = Path(bpy.data.filepath)
if not master.is_file() or master.suffix.lower() != '.blend':
    raise RuntimeError('Save the current master before running the AMG derivative.')
if bpy.data.scenes.get(SCENE_NAME):
    raise RuntimeError('AMG scene already exists; inspect it instead of duplicating it.')
if sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError('AMG source hash differs from the audited original.')
previous_scene = bpy.context.window.scene
master_objects = {obj.name: (obj.data, tuple(obj.matrix_world[i][j] for i in range(4) for j in range(4)))
                  for obj in bpy.data.objects}
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
checkpoint = ROOT / 'art/blender/checkpoints' / ('PREP_before_AMG_ONE_' + stamp + '.blend')
checkpoint.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)

scene = bpy.data.scenes.new(SCENE_NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene['author'] = 'Romario Vicente Amaro'
scene['source_sha256'] = SOURCE_SHA
scene['purpose'] = 'Independent authored-part vehicle derivative, not the playable world scene'
collection = bpy.data.collections.new('AMGO19_Interactive')
scene.collection.children.link(collection)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
imported = [obj for obj in bpy.data.objects if obj not in before]
meshes = [obj for obj in imported if obj.type == 'MESH']
if len(meshes) != 152:
    raise RuntimeError('Expected all 152 original mesh components.')
source_triangles = triangles(meshes)
source_uv = sum(len(obj.data.uv_layers) for obj in meshes)
source_normals = sum(len(obj.data.loops) for obj in meshes)
source_names = {obj: lineage(obj) for obj in meshes}
source_world = {obj: obj.matrix_world.copy() for obj in meshes}
low, high = bounds(meshes)
scale = TARGET_HEIGHT / (high.z-low.z)
normalization = Matrix.Diagonal((scale, scale, scale, 1)) @ Matrix.Translation(Vector((-(low.x+high.x)/2, -(low.y+high.y)/2, -low.z)))
root = empty(collection, 'Vehicle')
root['front_direction_gltf'] = '+Z'
root['source_front_evidence'] = 'Original headlightframe center at glTF Z+1.68; rear lamp at negative Z'
root['source_triangles'] = source_triangles
root['door_pivot_approximate'] = True
root['original_uv_normals_faces_preserved'] = True

tires = [obj for obj in meshes if re.search(r'amgprojone_tire(?:_|\s)', source_names[obj])]
if len(tires) != 4:
    raise RuntimeError('Expected four independently authored real tire components.')
groups = {'Body': root}
centers = {}
for tire in tires:
    lo, hi = bounds([tire])
    center = (lo+hi)/2
    # glTF +Z is Blender -Y. Model left is glTF/Blender +X.
    side = ('F' if center.y < 0 else 'R') + ('L' if center.x > 0 else 'R')
    if side in centers:
        raise RuntimeError('Ambiguous duplicate tire quadrant ' + side)
    centers[side] = center
    wheel = empty(collection, 'Wheel_' + side, root, normalization @ center)
    wheel['rotation_axis_gltf'] = 'X'
    wheel['radius_m'] = max(hi.y-lo.y, hi.z-lo.z)*scale/2
    groups['Wheel_' + side] = wheel
if set(centers) != {'FL', 'FR', 'RL', 'RR'}:
    raise RuntimeError('All four wheel quadrants are required.')

door_meshes = {}
for side, letter in [('FL', 'L'), ('FR', 'R')]:
    members = [obj for obj in meshes if re.search(r'amgprojone_door_' + letter + r'_', source_names[obj])]
    if len(members) != 16:
        raise RuntimeError('Expected glass plus 15 authored door components on ' + side)
    door_meshes[side] = members
    lo, hi = bounds(members)
    sign = 1 if letter == 'L' else -1
    # Geometry supplies the door split, but no hinge. Place a conservative
    # upper/front visual hinge within its actual bounds and state this clearly.
    hinge = Vector((sign*min(abs(lo.x), abs(hi.x)), lo.y+.08, hi.z-.10))
    door = empty(collection, 'Door_' + side, root, normalization @ hinge)
    door['opening_axis_gltf'] = 'Z'
    door['opening_angle_gltf'] = sign*1.10
    door['door_split_method'] = 'Original authored full door components; adapted butterfly hinge'
    door['door_pivot_approximate'] = True
    glass = empty(collection, 'Glass_' + side, door)
    glass['window_drop_m'] = .22
    groups['Door_' + side] = door
    groups['Glass_' + side] = glass

counts = {key: 0 for key in groups}
opacity_materials = {}
for index, obj in enumerate(meshes):
    names = source_names[obj]
    label = 'Body'
    if re.search(r'amgprojone_(?:tire|rim)(?:_|\s)', names):
        lo, hi = bounds([obj])
        center = (lo+hi)/2
        side = min(centers, key=lambda key: (center-centers[key]).length)
        # Never assign a central body part to a wheel merely by material name.
        if (center-centers[side]).length > .5:
            raise RuntimeError('Wheel component is outside the tire neighborhood: ' + obj.name)
        label = 'Wheel_' + side
    else:
        for side, members in door_meshes.items():
            if obj in members:
                is_glass = any(slot.material and 'clearglass' in slot.material.name.lower() for slot in obj.material_slots)
                label = ('Glass_' if is_glass else 'Door_') + side
                break
    # Reparent with complete world transform preservation. No mesh vertices,
    # UV loops or split normal data are recreated or simplified.
    obj.parent = groups[label]
    obj.matrix_world = normalization @ source_world[obj]
    obj['source_component_lineage'] = names
    obj['source_object_name'] = obj.name
    obj.name = 'AMGO19_' + label + '_Geometry_' + str(index)
    for slot in obj.material_slots:
        mat = slot.material
        if not mat:
            continue
        base_name = re.sub(r'\.\d+$', '', mat.name).lower()
        if base_name not in {'amgprojone_paint', 'amgprojone_carbon'}:
            continue
        if mat.name not in opacity_materials:
            opaque = mat.copy()
            opaque.name = 'AMGO19_' + base_name + '_opaque'
            rgba = tuple(opaque.diffuse_color)
            opaque.diffuse_color = (*rgba[:3], 1)
            if opaque.use_nodes:
                for node in opaque.node_tree.nodes:
                    if node.type != 'BSDF_PRINCIPLED':
                        continue
                    alpha = node.inputs.get('Alpha')
                    for link in list(alpha.links):
                        opaque.node_tree.links.remove(link)
                    alpha.default_value = 1
                    node.inputs['Roughness'].default_value = .23 if base_name.endswith('paint') else .35
            opacity_materials[mat.name] = opaque
        slot.material = opacity_materials[mat.name]
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    counts[label] += len(obj.data.polygons)

# Remove only newly imported hierarchy empties in this independent scene.
for obj in imported:
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
for required in ['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR', 'Door_FL', 'Door_FR', 'Glass_FL', 'Glass_FR']:
    if counts[required] <= 0:
        raise RuntimeError('Empty interactive component: ' + required)
if triangles(meshes) != source_triangles or sum(len(obj.data.uv_layers) for obj in meshes) != source_uv or sum(len(obj.data.loops) for obj in meshes) != source_normals:
    raise RuntimeError('Face, UV or loop inventory changed unexpectedly.')
for name, (data, matrix) in master_objects.items():
    obj = bpy.data.objects.get(name)
    if not obj or obj.data != data or tuple(obj.matrix_world[i][j] for i in range(4) for j in range(4)) != matrix:
        raise RuntimeError('An existing master object changed: ' + name)
bpy.context.view_layer.update()
final_low, final_high = bounds(meshes)
if abs(final_low.z) > 1e-4 or abs(final_high.z-TARGET_HEIGHT) > 1e-4:
    raise RuntimeError('Normalized car must stand on the ground at target height.')
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in collection.all_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format='GLB', use_selection=True, use_active_scene=True,
                          export_extras=True, export_yup=True, export_animations=False,
                          export_apply=False, export_materials='EXPORT')
raw = OUTPUT.read_bytes()
doc = json.loads(raw[20:20+struct.unpack_from('<I', raw, 12)[0]])
exported_triangles = sum(sum(doc['accessors'][p['indices']]['count']//3 for p in doc['meshes'][node['mesh']]['primitives'])
                         for node in doc['nodes'] if 'mesh' in node)
if len(doc['scenes']) != 1 or exported_triangles != source_triangles or sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError('Export triangle count or original source hash changed.')
report = {'scene': scene.name, 'master': str(master), 'checkpoint': str(checkpoint),
          'source': str(SOURCE), 'sourceSha256': SOURCE_SHA, 'originalPreserved': True,
          'derivative': str(OUTPUT), 'url': '/assets/additions20261019/' + OUTPUT.name,
          'sha256': sha(OUTPUT), 'bytes': len(raw), 'sourceMeshes': len(meshes),
          'triangles': exported_triangles, 'height': TARGET_HEIGHT, 'frontDirection': '+Z',
          'dimensionsBlender': list(final_high-final_low), 'wheelNames': ['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR'],
          'countsFaces': counts, 'uvLayersPreserved': source_uv, 'meshLoopsPreserved': source_normals,
          'opaqueMaterials': [mat.name for mat in opacity_materials.values()],
          'doorPivotApproximate': True, 'doorGeometryAuthored': True,
          'fixedGlass': 'windshield and rear glass remain in Body',
          'existingMasterObjectsPreserved': len(master_objects), 'validatedInBrowser': False}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
# Save the current master; do not open or switch to another .blend file.
bpy.ops.wm.save_as_mainfile(filepath=str(master))
print(json.dumps(report, ensure_ascii=False))
