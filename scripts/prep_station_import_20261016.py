"""Prepare the supplied station source and a separate static PBR LOD.

Run in Blender 5.2 with runpy.run_path(..., run_name='__main__'). Never opens or
saves a master .blend, deletes scene data, edits the source GLB, or writes a
runtime manifest. Only copied meshes/material trees/images are reduced/resized.
The source station remains full size with its original hierarchy. Static LOD
copies bake their world matrices and batch by material; meter scale is retained.
"""
import bpy
import hashlib
import json
import math
import os
import struct
import traceback
import uuid
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE = Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo')
RELATIVE = r'Estação de Trem Central\centraal_station_amsterdam.glb'
SOURCE_SHA = '6998b94de7dd765982f4fecadf2a0dd00bb307199148b66a49be9a2a3533de10'
OWNER = 'prep_station_import_20261016_v1'
IDENT = 'TRAIN_Centraal_Station_LOD1_20261016'
OUT = ROOT / 'frontend/public/assets/additions20261016'
FINAL = OUT / (IDENT + '.glb')
PREVIEW = OUT / (IDENT + '.png')
REPORT = ROOT / 'reports/station_catalog_entries_20261016.json'
QA_REPORT = ROOT / 'reports/STATION_IMPORT_QA_20261016.json'
TARGET = 225000
HARD_MAX = 250000
TEXTURE_CAP = 1024


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def write_json(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(str(temp), str(path))


def scene_switch(scene):
    window = bpy.context.window or next(iter(bpy.context.window_manager.windows), None)
    assert window, 'Blender window context is required'
    window.scene = scene
    bpy.context.view_layer.update()


def new_scene(base):
    # Existing scenes, including a prior failed attempt, are preserved intact.
    name = base
    index = 1
    while bpy.data.scenes.get(name) or bpy.data.collections.get(name):
        name = base + '_R' + str(index).zfill(2)
        index += 1
    scene = bpy.data.scenes.new(name)
    scene['prep_owner'] = OWNER
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    collection = bpy.data.collections.new(name)
    collection['prep_owner'] = OWNER
    scene.collection.children.link(collection)
    return scene, collection


def relink_fresh(objects, collection):
    for obj in objects:
        obj['prep_owner'] = OWNER
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)


def import_to_scene(path, scene, collection):
    scene_switch(scene)
    before = set(bpy.data.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    assert 'FINISHED' in result
    fresh = list(set(bpy.data.objects) - before)
    assert fresh
    relink_fresh(fresh, collection)
    bpy.context.view_layer.update()
    return fresh


def meshes(objects):
    return [o for o in objects if o.type == 'MESH' and not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]


def stats(objects):
    geometry = meshes(objects)
    assert geometry
    assert all(math.isfinite(float(x)) for o in geometry for v in o.data.vertices for x in v.co), 'Non-finite vertex'
    # Decimate/join can retain loose vertices above the actual surface. glTF
    # exports polygon-referenced vertices, so validate that same geometry rather
    # than object bound_box (which includes loose vertices and can be cached).
    points = [o.matrix_world @ o.data.vertices[index].co for o in geometry
              for index in {i for polygon in o.data.polygons for i in polygon.vertices}]
    assert points, 'No polygon-referenced geometry'
    assert all(math.isfinite(float(x)) for p in points for x in p), 'Non-finite world bound'
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    assert min(hi - lo) > 1e-6
    return {'meshes': len(geometry), 'vertices': sum(len(o.data.vertices) for o in geometry),
            'triangles': sum(max(0, len(p.vertices) - 2) for o in geometry for p in o.data.polygons),
            'boundsMin': list(lo), 'boundsMax': list(hi), 'dimensions': list(hi - lo)}


def doc_from_glb(path):
    with path.open('rb') as stream:
        magic, version, total = struct.unpack('<4sII', stream.read(12))
        assert magic == b'glTF' and version == 2 and total == path.stat().st_size
        length, kind = struct.unpack('<II', stream.read(8))
        assert kind == 0x4E4F534A
        return json.loads(stream.read(length))


def triangle_count(doc):
    counts = []
    for mesh in doc.get('meshes', []):
        total = 0
        for primitive in mesh.get('primitives', []):
            assert primitive.get('mode', 4) == 4
            accessor = primitive.get('indices', primitive['attributes']['POSITION'])
            total += doc['accessors'][accessor]['count'] // 3
        counts.append(total)
    def visit(i):
        node = doc['nodes'][i]
        return (counts[node['mesh']] if 'mesh' in node else 0) + sum(visit(j) for j in node.get('children', []))
    return sum(visit(i) for i in doc['scenes'][doc.get('scene', 0)]['nodes'])


def state(objects):
    return {o.as_pointer(): (o.name, o.parent.as_pointer() if o.parent else None,
            o.data.as_pointer() if o.data else None, tuple(o.location), tuple(o.scale),
            o.rotation_mode, tuple(o.rotation_euler), tuple(o.rotation_quaternion),
            tuple(v for row in o.matrix_parent_inverse for v in row),
            tuple(c.as_pointer() for c in o.users_collection)) for o in objects}


def source_material_snapshot(objects):
    materials = {m for o in meshes(objects) for m in o.data.materials if m}
    images = set()
    trees = set()
    def visit(tree):
        if tree is None or tree in trees:
            return
        trees.add(tree)
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                images.add(node.image)
            if node.type == 'GROUP':
                visit(node.node_tree)
    for material in materials:
        visit(material.node_tree)
    return {'materials': {m.as_pointer(): (m.name, m.node_tree.as_pointer() if m.node_tree else None,
                 tuple(m.diffuse_color)) for m in materials},
            'trees': {t.as_pointer(): (t.name, tuple((n.name, n.type,
                 n.image.as_pointer() if n.type == 'TEX_IMAGE' and n.image else None,
                 n.node_tree.as_pointer() if n.type == 'GROUP' and n.node_tree else None) for n in t.nodes),
                 tuple((l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name) for l in t.links)) for t in trees},
            'images': {i.as_pointer(): (i.name, tuple(i.size), i.colorspace_settings.name) for i in images}}


def used_images(objects):
    images = set()
    visited = set()
    def visit(tree):
        if tree is None or tree in visited:
            return
        visited.add(tree)
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                images.add(node.image)
            elif node.type == 'GROUP':
                visit(node.node_tree)
    for obj in meshes(objects):
        for material in obj.data.materials:
            if material:
                visit(material.node_tree)
    return list(images)


def clone_station(source_objects, scene, collection):
    scene_switch(scene)
    mapping = {}
    material_copies = {}
    image_copies = {}
    group_copies = {}
    image_details = []
    def copy_image(original):
        if original in image_copies:
            return image_copies[original]
        image = original.copy()
        assert image != original
        image.name = 'ST16_LOD_' + original.name
        image['prep_owner'] = OWNER
        image_copies[original] = image
        before_size = tuple(original.size)
        if max(before_size) > TEXTURE_CAP:
            factor = TEXTURE_CAP / max(before_size)
            image.scale(max(1, round(before_size[0] * factor)), max(1, round(before_size[1] * factor)))
        assert image.size[0] and image.size[1] and max(image.size) <= TEXTURE_CAP
        image.pack()
        image_details.append({'sourceName': original.name, 'copiedName': image.name,
                              'sourceDimensions': list(before_size), 'lodDimensions': list(image.size)})
        return image
    def remap_tree(tree):
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                node.image = copy_image(node.image)
            elif node.type == 'GROUP' and node.node_tree:
                old_group = node.node_tree
                if old_group not in group_copies:
                    copied_group = old_group.copy()
                    copied_group.name = 'ST16_LOD_' + old_group.name
                    copied_group['prep_owner'] = OWNER
                    group_copies[old_group] = copied_group
                    remap_tree(copied_group)
                node.node_tree = group_copies[old_group]
    def copy_material(original):
        if original in material_copies:
            return material_copies[original]
        material = original.copy()
        assert material != original and material.node_tree != original.node_tree
        material.name = 'ST16_LOD_' + original.name
        material['prep_owner'] = OWNER
        material['material_provenance'] = 'Copied from supplied station PBR; only owned texture copies resized'
        material_copies[original] = material
        if material.node_tree:
            remap_tree(material.node_tree)
        return material
    for original in source_objects:
        if original.type not in ('MESH', 'EMPTY'):
            continue
        duplicate = original.copy()
        duplicate.name = 'ST16_LOD_' + original.name
        duplicate['prep_owner'] = OWNER
        duplicate['station_source_node'] = original.name
        if original.type == 'MESH':
            duplicate.data = original.data.copy()
            duplicate.data.name = 'ST16_LOD_' + original.data.name
            assert duplicate.data != original.data
            for index, material in enumerate(original.data.materials):
                if material:
                    duplicate.data.materials[index] = copy_material(material)
        collection.objects.link(duplicate)
        mapping[original] = duplicate
    root = bpy.data.objects.new(IDENT + '_ROOT', None)
    root['prep_owner'] = OWNER
    root['source_unit'] = 'meter, glTF convention; scale factor 1 retained'
    collection.objects.link(root)
    for original, duplicate in mapping.items():
        world = original.matrix_world.copy()
        duplicate.parent = mapping.get(original.parent, root)
        duplicate.matrix_world = world
        assert duplicate.parent != original.parent
    bpy.context.view_layer.update()
    assert len(meshes(mapping.values())) == len(meshes(source_objects))
    return root, list(mapping.values()), image_details


def reduce_lod(objects, budget):
    geometry = meshes(objects)
    counts = {o: sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) for o in geometry}
    fixed = sum(count for count in counts.values() if count <= 12)
    reducible = sum(count for count in counts.values() if count > 12)
    ratio = min(1., max(.001, (budget - fixed) / max(1, reducible)))
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj, count in counts.items():
        if count <= 12 or ratio >= 1:
            continue
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new('ST16_Owned_LOD_Decimate', 'DECIMATE')
        modifier.decimate_type = 'COLLAPSE'
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        result = bpy.ops.object.modifier_apply(modifier=modifier.name)
        assert 'FINISHED' in result
        obj.select_set(False)
    bpy.context.view_layer.update()
    return {'collapseRatio': ratio, 'fixedSmallTriangles': fixed, 'requestedBudget': budget,
            'result': stats(objects)}


def batch_static_copies(objects, root):
    """Only copied static meshes enter this operation; SOURCE never does."""
    geometry = meshes(objects)
    before = stats(geometry)
    assert all(o.get('prep_owner') == OWNER and not o.animation_data and not o.constraints for o in geometry)
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    # Detach owned mesh copies with identical world placement, then apply every
    # world matrix into copied geometry in one operator call before joining.
    for obj in geometry:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        obj.select_set(True)
    bpy.context.view_layer.objects.active = geometry[0]
    result = bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    assert 'FINISHED' in result
    bpy.context.view_layer.update()
    groups = {}
    for obj in geometry:
        used = {obj.data.materials[p.material_index] for p in obj.data.polygons}
        assert len(used) == 1 and None not in used, 'Station primitive must have one unambiguous material'
        material = next(iter(used))
        assert material.get('prep_owner') == OWNER
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.material_index = 0
        groups.setdefault(material, []).append(obj)
        obj.select_set(False)
    assert len(groups) <= 27, 'Unexpected station material group count'
    batches = []
    for index, (material, members) in enumerate(groups.items()):
        names = [o.get('station_source_node', o.name) for o in members]
        for obj in members:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = members[0]
        if len(members) > 1:
            joined = bpy.ops.object.join()
            assert 'FINISHED' in joined
        batch = bpy.context.view_layer.objects.active
        batch.name = 'ST16_LOD_BATCH_' + str(index).zfill(2)
        batch['prep_owner'] = OWNER
        batch['source_node_names_json'] = json.dumps(names, ensure_ascii=False)
        batch['derivative_batch_material'] = material.name
        world = batch.matrix_world.copy()
        batch.parent = root
        batch.matrix_world = world
        batch.select_set(False)
        batches.append(batch)
    bpy.context.view_layer.update()
    after = stats(batches)
    assert after['triangles'] == before['triangles']
    assert all(abs(a - b) < .002 for a, b in zip(before['dimensions'], after['dimensions']))
    return batches, {'inputMeshes': len(geometry), 'outputMaterialBatches': len(batches),
        'worldTransformsAppliedToOwnedCopies': True, 'sourceHierarchyKeptInSourceSceneOnly': True,
        'trianglesBefore': before['triangles'], 'trianglesAfter': after['triangles']}


def render_preview(scene, collection, path, bounds):
    scene_switch(scene)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    world = bpy.data.worlds.new('ST16_QA_World')
    world['prep_owner'] = OWNER
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.11, .14, .18, 1)
    background.inputs['Strength'].default_value = .6
    scene.world = world
    center = (Vector(bounds['boundsMin']) + Vector(bounds['boundsMax'])) / 2
    span = max(bounds['dimensions'])
    data = bpy.data.cameras.new('ST16_QA_Camera')
    camera = bpy.data.objects.new(data.name, data)
    camera['prep_owner'] = OWNER
    collection.objects.link(camera)
    camera.location = center + Vector((1.1, -1.8, .9)) * span
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'; data.ortho_scale = span * 1.4; data.clip_end = span * 20
    scene.camera = camera
    for index, (position, power, size) in enumerate([((1, -2, 2.5), 95, 2), ((-2, -.3, 1.2), 55, 2), ((.3, 1.7, 2), 85, 1.6)]):
        light_data = bpy.data.lights.new('ST16_QA_Light_' + str(index), 'AREA')
        light = bpy.data.objects.new(light_data.name, light_data)
        light['prep_owner'] = OWNER
        collection.objects.link(light)
        light.location = center + Vector(position) * span
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
        light_data.energy = power * span * span
        light_data.shape = 'DISK'; light_data.size = span * size
    scene.render.filepath = str(path)
    result = bpy.ops.render.render(write_still=True)
    assert 'FINISHED' in result and path.stat().st_size > 500
    with path.open('rb') as stream:
        header = stream.read(24)
    assert header[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', header[16:24]) == (512, 512)


def main():
    assert bpy.app.version >= (5, 2, 0)
    source_path = SOURCE / RELATIVE
    assert sha(source_path) == SOURCE_SHA, 'Source changed; audit before deriving a new LOD'
    source_doc = doc_from_glb(source_path)
    source_expected = triangle_count(source_doc)
    assert source_expected == 1130377 and not source_doc.get('skins') and not source_doc.get('animations')
    previous = None
    if REPORT.exists():
        values = json.loads(REPORT.read_text(encoding='utf-8'))
        assert isinstance(values, list) and len(values) == 1 and values[0].get('prepOwner') == OWNER, 'Unknown catalog report exists'
        previous = values[0]
    if QA_REPORT.exists():
        assert json.loads(QA_REPORT.read_text(encoding='utf-8')).get('prepOwner') == OWNER, 'Unknown QA report exists'
    if FINAL.exists() or PREVIEW.exists():
        assert previous and previous.get('status') == 'validated' and previous.get('reimportValidated'), 'Unknown or incomplete output exists'
        assert previous['sourceSha256'] == SOURCE_SHA and FINAL.is_file() and PREVIEW.is_file()
        assert sha(FINAL) == previous['sha256'] and sha(PREVIEW) == previous['previewSha256'], 'Output differs from previously validated bytes'
        # Completed work is idempotently reused without editing or deleting anything.
        print('PREP_STATION_IMPORT_20261016 ' + json.dumps({'status': 'reused-validated', 'id': IDENT, 'masterSaved': False}))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    windows = [(w, w.scene) for w in bpy.context.window_manager.windows]
    original_objects = tuple(bpy.data.objects)
    original_state = state(original_objects)
    run = uuid.uuid4().hex[:10]
    staging = OUT / ('.' + IDENT + '.' + run + '.staging.glb')
    staging_preview = OUT / ('.' + IDENT + '.' + run + '.staging.png')
    try:
        source_scene, source_collection = new_scene('PREP_STATION_SOURCE_20261016')
        original = import_to_scene(source_path, source_scene, source_collection)
        source_stats = stats(original)
        assert source_stats['triangles'] == source_expected
        assert abs(source_stats['dimensions'][0] - 286.555778) < .1
        assert abs(source_stats['dimensions'][1] - 133.004947) < .1
        assert abs(source_stats['dimensions'][2] - 36.948025) < .1
        original_import_state = state(original)
        original_materials = source_material_snapshot(original)
        source_scene['purpose'] = 'Untouched full-resolution supplied station in nominal glTF meter scale'
        source_scene['source_sha256'] = SOURCE_SHA
        source_scene['original_preserved'] = True
        derivative_scene, derivative_collection = new_scene('PREP_STATION_LOD_20261016')
        derivative_scene['purpose'] = 'Separate static PBR LOD, not city placement; scale remains one meter'
        root, derivative, texture_details = clone_station(original, derivative_scene, derivative_collection)
        reduction = reduce_lod(derivative, TARGET)
        if reduction['result']['triangles'] > HARD_MAX:
            reduction['secondPass'] = reduce_lod(derivative, 220000)
        reduced = stats(derivative)
        assert 0 < reduced['triangles'] <= HARD_MAX
        assert all(abs(a - b) <= max(.1, a * .02) for a, b in zip(source_stats['dimensions'], reduced['dimensions'])), 'LOD changed station extent by more than 2%'
        derivative, material_batching = batch_static_copies(derivative, root)
        reduction['materialBatching'] = material_batching
        reduced = stats(derivative)
        lo = Vector(reduced['boundsMin']); hi = Vector(reduced['boundsMax'])
        root.matrix_world = Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
        root['meter_scale_retained'] = True
        root['display_transform'] = 'Translation only: centered in XY, grounded in Z; scale 1'
        bpy.context.view_layer.update()
        normalized = stats(derivative)
        assert abs(normalized['boundsMin'][2]) < 1e-4
        for obj in derivative_scene.objects:
            obj.select_set(False)
        for obj in [root] + derivative:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        result = bpy.ops.export_scene.gltf(filepath=str(staging), export_format='GLB',
            use_selection=True, use_active_scene=True, export_yup=True, export_apply=True,
            export_animations=False, export_skins=False, export_cameras=False,
            export_lights=False, export_extras=True, export_materials='EXPORT',
            export_image_format='AUTO', export_texcoords=True, export_normals=True)
        assert 'FINISHED' in result and staging.is_file()
        document = doc_from_glb(staging)
        expected = triangle_count(document)
        assert 0 < expected <= HARD_MAX and not document.get('skins') and not document.get('animations')
        qa_scene, qa_collection = new_scene('PREP_STATION_QA_20261016')
        roundtrip = import_to_scene(staging, qa_scene, qa_collection)
        verified = stats(roundtrip)
        assert verified['triangles'] == expected
        assert all(abs(a - b) <= max(.002, a * 1e-5) for a, b in zip(normalized['dimensions'], verified['dimensions'])), 'Reimport bounds mismatch'
        qa_images = used_images(roundtrip)
        assert qa_images and all(0 < max(image.size) <= TEXTURE_CAP for image in qa_images), 'Delivered texture exceeds cap or is missing'
        assert len(meshes(roundtrip)) == len(meshes(derivative)), 'LOD hierarchy lost a mesh node'
        render_preview(qa_scene, qa_collection, staging_preview, verified)
        assert state(original) == original_import_state, 'Full-resolution source object changed'
        assert source_material_snapshot(original) == original_materials, 'Source/shared material or image changed'
        assert state(original_objects) == original_state, 'An earlier object changed'
        assert sha(source_path) == SOURCE_SHA, 'Original disk GLB changed'
        assert not FINAL.exists() and not PREVIEW.exists(), 'Output appeared during preparation; preserve it'
        staging.rename(FINAL)
        staging_preview.rename(PREVIEW)
        source_extras = source_doc.get('asset', {}).get('extras', {})
        record = {'id': IDENT, 'name': 'Estação Central de Amsterdam · LOD1', 'category': 'Trens',
            'sourceRelative': RELATIVE, 'sourceSha256': SOURCE_SHA,
            'sourceFiles': [{'file': RELATIVE, 'sha256': SOURCE_SHA, 'bytes': source_path.stat().st_size}],
            'credits': source_extras, 'licenseStatus': 'attribution', 'originalTriangles': source_expected,
            'status': 'validated', 'reimportValidated': True, 'originalRig': False,
            'animated': False, 'animations': [], 'skins': 0,
            'url': '/assets/additions20261016/' + FINAL.name, 'bytes': FINAL.stat().st_size,
            'sha256': sha(FINAL), 'triangles': expected, 'preparedTriangles': reduced['triangles'],
            'meshPrimitiveTriangles': expected, 'meshes': verified['meshes'], 'dimensions': verified['dimensions'],
            'dimensionsConvention': 'Blender XYZ meters; GLB exports Y up',
            'sourceDimensionsGLTF_XYZ': [286.555778, 36.948025, 133.004947],
            'sourceDimensionsBlenderXYZ': source_stats['dimensions'], 'sourceUnits': 'meters, glTF convention',
            'sourceScaleRetained': 1, 'normalization': 'Translation only; centered XY and grounded Z; not fitted to city',
            'geometryModified': True, 'lod': {'level': 1, 'targetTriangles': TARGET, 'maxTriangles': HARD_MAX,
                'actualTriangles': expected, 'method': 'Per-mesh collapse on copied meshes; world transforms baked into static copies before batching by material'},
            'originalPreserved': True, 'originalSourceScene': source_scene.name,
            'derivativeScene': derivative_scene.name, 'qaScene': qa_scene.name,
            'sourceCollection': source_collection.name, 'collection': derivative_collection.name,
            'hierarchyPreserved': False, 'sourceHierarchyPreserved': True,
            'derivativeMaterialBatches': len(derivative), 'materialBatching': material_batching,
            'textureCapPixels': TEXTURE_CAP, 'textures': texture_details,
            'materialRecovery': 'Original supplied PBR copied into owned material/node trees and owned image copies; original/shared datablocks retained',
            'modifications': 'Static LOD reduction per copied mesh; copied geometry world transforms applied then batched by material (up to 27 meshes); owned textures capped at 1024px; meter scale retained; full hierarchy preserved only in SOURCE scene',
            'validation': 'GLB reimport: matching triangles, finite vertices/world bounds, matching dimensions, all delivered image sizes <=1024, real 512px Blender preview; full source and prior objects unchanged',
            'preview': '/assets/additions20261016/' + PREVIEW.name, 'previewSha256': sha(PREVIEW),
            'previewSize': [512, 512], 'previewEvidence': 'Actual delivered GLB reimport rendered in Blender EEVEE',
            'prepOwner': OWNER}
        write_json(REPORT, [record])
        write_json(QA_REPORT, {'prepOwner': OWNER, 'status': 'validated', 'source': source_stats,
            'reduction': reduction, 'derivative': normalized, 'reimport': verified,
            'sourceScene': source_scene.name, 'derivativeScene': derivative_scene.name, 'qaScene': qa_scene.name,
            'previousObjectsPreserved': len(original_objects), 'sourceAndSharedMaterialsUnchanged': True,
            'originalDiskSha256Unchanged': True, 'masterSaved': False, 'runtimeManifestChanged': False,
            'textureCopies': texture_details, 'deliveredTextureDimensions': [list(i.size) for i in qa_images],
            'blenderVersion': bpy.app.version_string})
        print('PREP_STATION_IMPORT_20261016 ' + json.dumps({'status': 'validated', 'id': IDENT,
              'triangles': expected, 'dimensions': verified['dimensions'], 'masterSaved': False}))
    except Exception:
        write_json(QA_REPORT, {'prepOwner': OWNER, 'status': 'failed', 'error': traceback.format_exc(),
            'stagingGLBPreserved': str(staging), 'stagingPreviewPreserved': str(staging_preview),
            'masterSaved': False, 'runtimeManifestChanged': False})
        raise
    finally:
        for window, scene in windows:
            window.scene = scene


if __name__ == '__main__':
    main()
