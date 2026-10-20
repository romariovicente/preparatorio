"""Finish the existing AMGO19 scene via MCP; never reimport or duplicate it.

The export is now active-scene-only. This completion pass consumes its exact
SHA-bound CPU geometry verification and saves the existing scene/master.
"""
from pathlib import Path
import bpy, hashlib, json, math, struct
from mathutils import Vector

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE = Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Veiculos\Transparency Mercedes AMG One\transparency_mercedes_amg_one.glb')
EXPECTED_SHA = '951afc9a529f94ddcf1b8480de8356e0e381f9e832f9588985e5d2f6897b6a0a'
OUTPUT = ROOT / 'frontend/public/assets/additions20261019/VEH_Mercedes_AMG_One_Interactive_20261019.glb'
REPORT = ROOT / 'reports/AMG_ONE_BLENDER_20261019.json'
CPU_REPORT = ROOT / 'reports/AMG_ONE_RUNTIME_VALIDATION_20261019.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def glb_document(path):
    raw = path.read_bytes()
    return json.loads(raw[20:20+struct.unpack_from('<I', raw, 12)[0]])

def document_inventory(doc):
    result = {'triangles': 0, 'positions': 0, 'normalPositions': 0, 'uvPositions': 0, 'meshInstances': 0}
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        result['meshInstances'] += 1
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            if primitive.get('mode', 4) != 4:
                raise RuntimeError('Only original triangle primitives are supported.')
            attributes = primitive['attributes']
            count = doc['accessors'][attributes['POSITION']]['count']
            result['positions'] += count
            result['triangles'] += doc['accessors'][primitive['indices']]['count']//3
            if 'NORMAL' in attributes:
                result['normalPositions'] += doc['accessors'][attributes['NORMAL']]['count']
            if 'TEXCOORD_0' in attributes:
                result['uvPositions'] += doc['accessors'][attributes['TEXCOORD_0']]['count']
    return result

master = Path(bpy.data.filepath)
scene = bpy.data.scenes.get('PREP_AMG_ONE_20261019')
if not master.is_file() or not scene:
    raise RuntimeError('The saved master and existing AMG scene are required.')
if sha(SOURCE) != EXPECTED_SHA:
    raise RuntimeError('Original source hash changed.')
before_names = set(obj.name for obj in bpy.data.objects)
untouched = {obj.name: (obj.data, tuple(obj.matrix_world[i][j] for i in range(4) for j in range(4)))
             for obj in bpy.data.objects if not obj.name.startswith('AMGO19_')}
bpy.context.window.scene = scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
if len(meshes) != 152 or any(not obj.name.startswith('AMGO19_') for obj in meshes):
    raise RuntimeError('AMG scene must contain exactly the 152 original mesh components.')
by_contract = {obj.get('asset_node_name'): obj for obj in scene.objects if obj.get('asset_node_name')}
required = ['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR', 'Door_FL', 'Door_FR', 'Glass_FL', 'Glass_FR']
for name in required:
    obj = by_contract.get(name)
    if not obj or not obj.children:
        raise RuntimeError('Missing nonempty interactive group: ' + name)
    if name.startswith('Wheel_') and obj.get('rotation_axis_gltf') != 'X':
        raise RuntimeError('Incorrect wheel axle: ' + name)
    if name.startswith('Glass_') and obj.parent != by_contract['Door_' + name[-2:]]:
        raise RuntimeError('Side glass is not parented to its actual door.')
bpy.context.view_layer.update()
points = [obj.matrix_world @ Vector(point) for obj in meshes for point in obj.bound_box]
low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
if not all(math.isfinite(value) for point in points for value in point):
    raise RuntimeError('Nonfinite mesh bounds.')
if abs(low.z) > 1e-4 or abs(high.z-1.26) > 1e-4:
    raise RuntimeError('AMG must stand on floor zero at height 1.26 m.')
source_inventory = document_inventory(glb_document(SOURCE))
if sum(len(poly.vertices)-2 for obj in meshes for poly in obj.data.polygons) != source_inventory['triangles']:
    raise RuntimeError('Blender geometry differs from source instance triangle count.')
root = by_contract.get('Vehicle')
if not root:
    raise RuntimeError('AMG root missing.')
doc = glb_document(OUTPUT)
inventory = document_inventory(doc)
cpu = json.loads(CPU_REPORT.read_text(encoding='utf-8'))
if not cpu.get('passed') or cpu.get('sha256') != sha(OUTPUT) or cpu.get('sourceSha256') != EXPECTED_SHA:
    raise RuntimeError('Run the CPU geometry verifier against this exact exported GLB before finishing.')
if len(doc['scenes']) != 1 or inventory['triangles'] != source_inventory['triangles'] or inventory['meshInstances'] != source_inventory['meshInstances']:
    raise RuntimeError('Single-scene triangle/mesh instance inventory differs.')
if inventory['normalPositions'] != inventory['positions'] or inventory['uvPositions'] < source_inventory['uvPositions']:
    raise RuntimeError('Normal or UV attribute coverage was lost.')
geometry = cpu.get('geometry', {})
if geometry.get('matchedTriangles') != source_inventory['triangles'] or geometry.get('maxPositionError', 1) > 1e-4 or geometry.get('maxUvError', 1) > 1e-4 or geometry.get('maxNormalError', 1) > .001:
    raise RuntimeError('Transformed original face geometry, UV or normal comparison failed.')
if OUTPUT.stat().st_size > 25_000_000:
    raise RuntimeError('AMG-only export unexpectedly exceeds its original web asset budget.')
if set(obj.name for obj in bpy.data.objects) != before_names:
    raise RuntimeError('Finishing unexpectedly created or removed Blender objects.')
for name, (data, matrix) in untouched.items():
    obj = bpy.data.objects.get(name)
    if not obj or obj.data != data or tuple(obj.matrix_world[i][j] for i in range(4) for j in range(4)) != matrix:
        raise RuntimeError('Another scene object changed: ' + name)
if sha(SOURCE) != EXPECTED_SHA:
    raise RuntimeError('Source changed after export.')
materials = doc.get('materials', [])
opaque_names = [mat.get('name', '') for mat in materials if mat.get('name', '').startswith('AMGO19_') and mat.get('name', '').endswith('_opaque')]
if len(opaque_names) != 2:
    raise RuntimeError('Expected only the two paint/carbon opacity adaptations.')
checkpoints = sorted((ROOT / 'art/blender/checkpoints').glob('PREP_before_AMG_ONE_*.blend'))
report = {'scene': scene.name, 'master': str(master), 'checkpoint': str(checkpoints[-1]) if checkpoints else None,
          'source': str(SOURCE), 'sourceSha256': EXPECTED_SHA, 'originalPreserved': True,
          'derivative': str(OUTPUT), 'url': '/assets/additions20261019/' + OUTPUT.name,
          'bytes': OUTPUT.stat().st_size, 'sha256': sha(OUTPUT), 'singleSceneExport': True,
          'inventoryPerInstance': inventory, 'sourceInventoryPerInstance': source_inventory,
          'splitVertices': inventory['positions']-source_inventory['positions'],
          'splitVertexPercent': (inventory['positions']/source_inventory['positions']-1)*100,
          'geometryVerification': geometry, 'geometryVerifierReport': str(CPU_REPORT),
          'height': 1.26, 'dimensionsBlender': list(high-low), 'floorZ': low.z,
          'frontDirection': '+Z', 'wheelNames': required[:4], 'doorGeometryAuthored': True,
          'doorPivotApproximate': True, 'windowDropM': .22, 'opaqueMaterials': opaque_names,
          'fixedGlass': 'windshield and rear glass remain in Body',
          'otherSceneObjectsPreserved': len(untouched), 'validatedInBrowser': False}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(master))
print(json.dumps(report, ensure_ascii=False))
