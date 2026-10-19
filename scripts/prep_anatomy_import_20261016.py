"""Prepare four supplied anatomy assemblies in the current Blender session.

Run explicitly in Blender 5.2. This script never opens or saves a master .blend,
changes an existing scene, writes a runtime manifest, or edits supplied originals.
Exported colors and sizes are educational display reconstructions, not clinical
measurements or anatomical segmentation. Final catalog entries require GLB
roundtrip checks and an actual 512px render before status becomes validated.
"""
import bpy
import collections
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
OUT = ROOT / 'frontend/public/assets/additions20261016'
REPORT = ROOT / 'reports/anatomy_catalog_entries_20261016.json'
QA_REPORT = ROOT / 'reports/ANATOMY_IMPORT_QA_20261016.json'
OWNER = 'prep_anatomy_import_20261016_v1'
SCENE = 'PREP_ANATOMY_ASSETS_20261016'
ASSETS = [
    {'id': 'EDU_Liver_Gallbladder_20261016', 'name': 'Fígado e vesícula biliar',
     'folder': 'Esqueleto/Anatomy - Human Liver and Gallbladder', 'parts': 1,
     'triangles': 25801, 'height': .35, 'color': (.42, .085, .055, 1)},
    {'id': 'EDU_Lungs_20261016', 'name': 'Pulmões',
     'folder': 'Esqueleto/Anatomy - Human Lungs', 'parts': 1,
     'triangles': 68610, 'height': .55, 'color': (.72, .24, .29, 1)},
    {'id': 'EDU_Kidney_Urinary_20261016', 'name': 'Rins e sistema urinário',
     'folder': 'Esqueleto/Anatomy - Human kidney and urinary system', 'parts': 1,
     'triangles': 145866, 'height': .60, 'color': (.46, .12, .21, 1)},
    {'id': 'EDU_Spine_Torso_RibCage_20261016', 'name': 'Tronco, coluna e caixa torácica',
     'folder': 'Esqueleto/Anatomy - Human Spine Torso and Rib Cage', 'parts': 4,
     'triangles': 109224, 'height': .70, 'color': (.73, .66, .48, 1)},
]


def disk_path(path):
    value = str(path)
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def sha256(path):
    h = hashlib.sha256()
    with open(disk_path(path), 'rb') as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(str(temp), str(path))


def scene_switch(scene):
    window = bpy.context.window or next(iter(bpy.context.window_manager.windows), None)
    if window is None:
        raise RuntimeError('A Blender window context is required; no existing scene was altered.')
    window.scene = scene
    bpy.context.view_layer.update()


def owned_scene(name):
    scene = bpy.data.scenes.get(name)
    if scene:
        assert scene.get('prep_owner') == OWNER, 'Unknown scene already exists: ' + name
    else:
        scene = bpy.data.scenes.new(name)
        scene['prep_owner'] = OWNER
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
    return scene


def owned_collection(scene, name, parent=None):
    collection = bpy.data.collections.get(name)
    if collection:
        assert collection.get('prep_owner') == OWNER, 'Unknown collection already exists: ' + name
    else:
        collection = bpy.data.collections.new(name)
        collection['prep_owner'] = OWNER
    destination = parent or scene.collection
    if collection.name not in destination.children:
        destination.children.link(collection)
    return collection


def clear_owned_objects(collection):
    for obj in list(collection.all_objects):
        assert obj.get('prep_owner') == OWNER, 'Refusing to delete unowned object: ' + obj.name
    for obj in list(collection.all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def mesh_objects(objects):
    return [o for o in objects if o.type == 'MESH' and not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]


def geometry_stats(objects):
    meshes = mesh_objects(objects)
    assert meshes, 'No anatomical mesh imported'
    assert all(math.isfinite(float(c)) for o in meshes for v in o.data.vertices for c in v.co), 'Non-finite source vertex'
    points = [o.matrix_world @ Vector(corner) for o in meshes for corner in o.bound_box]
    assert points and all(math.isfinite(float(c)) for p in points for c in p), 'Non-finite world bounds'
    lo = Vector([min(p[q] for p in points) for q in range(3)])
    hi = Vector([max(p[q] for p in points) for q in range(3)])
    size = hi - lo
    assert min(size) > 1e-8, 'Degenerate anatomy bounds'
    return {'meshes': len(meshes), 'vertices': sum(len(o.data.vertices) for o in meshes),
            'triangles': sum(max(0, len(p.vertices) - 2) for o in meshes for p in o.data.polygons),
            'boundsMin': list(lo), 'boundsMax': list(hi), 'dimensions': list(size)}


def f32_point(point):
    # OBJ decimal coordinates are stored as float32 by Blender. Canonicalize
    # negative zero as well, so identity matrix multiplication cannot change keys.
    return tuple(0. if x == 0 else x for x in struct.unpack('<3f', struct.pack('<3f', *point)))


def positive_triangle_key(points):
    a, b, c = [f32_point(p) for p in points]
    u = [b[q] - a[q] for q in range(3)]
    v = [c[q] - a[q] for q in range(3)]
    cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    if all(value == 0 for value in cross):
        return None
    return b''.join(sorted(struct.pack('<3f', *p) for p in (a, b, c)))


def topology_signature(counter):
    value = hashlib.sha256()
    for key, count in sorted(counter.items()):
        value.update(key)
        value.update(struct.pack('<I', count))
    return value.hexdigest()


def audit_obj_triangles(path, relative):
    """Diagnose actual source degenerates before accepting importer cleanup."""
    vertices = []
    faces = []
    with open(disk_path(path), 'r', encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('v '):
                point = tuple(float(x) for x in line.split()[1:4])
                assert len(point) == 3 and all(math.isfinite(x) for x in point)
                vertices.append(f32_point(point))
            elif line.startswith('f '):
                indices = [int(token.split('/')[0]) for token in line.split()[1:]]
                face = tuple(i - 1 if i > 0 else len(vertices) + i for i in indices)
                assert len(face) == 3, 'Unexpected non-triangle OBJ; topology audit must be extended explicitly'
                assert all(0 <= i < len(vertices) for i in face), 'Invalid source vertex index'
                faces.append(face)
    repeated = 0
    geometric_zero_distinct = 0
    valid_index_faces = set()
    positive = collections.Counter()
    for face in faces:
        if len(set(face)) < 3:
            repeated += 1
            continue
        # These supplied sources have no duplicate usable index faces. If a
        # different source adds them, do not silently predict importer behavior.
        canonical = tuple(sorted(face))
        assert canonical not in valid_index_faces, 'Duplicate usable face requires separate diagnosis'
        valid_index_faces.add(canonical)
        key = positive_triangle_key([vertices[i] for i in face])
        if key is None:
            geometric_zero_distinct += 1
        else:
            positive[key] += 1
    maximum = len(faces) - repeated
    proof = {'file': relative, 'rawFaceRecords': len(faces), 'sourceFanTriangles': len(faces),
        'facesWithRepeatedVertexIndices': repeated,
        'zeroAreaFacesWithDistinctIndices': geometric_zero_distinct,
        'usableIndexTriangles': maximum, 'positiveAreaTriangles': sum(positive.values()),
        'expectedImportedTrianglesMin': maximum - geometric_zero_distinct,
        'expectedImportedTrianglesMax': maximum,
        'positiveAreaGeometrySha256Float32': topology_signature(positive),
        'diagnosis': 'Repeated-index triangle records have zero area and are rejected by OBJ mesh validation; source fan count is not usable surface count'}
    return proof, positive


def imported_positive_triangles(objects):
    positive = collections.Counter()
    for obj in mesh_objects(objects):
        for polygon in obj.data.polygons:
            assert len(polygon.vertices) == 3, 'Importer unexpectedly changed triangle topology'
            points = [obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices]
            key = positive_triangle_key(points)
            if key is not None:
                positive[key] += 1
    return positive


def glb_document(path):
    with path.open('rb') as stream:
        magic, version, total = struct.unpack('<4sII', stream.read(12))
        assert magic == b'glTF' and version == 2 and total == path.stat().st_size
        size, kind = struct.unpack('<II', stream.read(8))
        assert kind == 0x4E4F534A
        return json.loads(stream.read(size))


def glb_scene_triangles(doc):
    accessors = doc.get('accessors', [])
    counts = []
    for mesh in doc.get('meshes', []):
        total = 0
        for primitive in mesh.get('primitives', []):
            assert primitive.get('mode', 4) == 4, 'Unexpected non-triangle primitive'
            accessor = primitive.get('indices', primitive['attributes']['POSITION'])
            total += accessors[accessor]['count'] // 3
        counts.append(total)
    def visit(i):
        node = doc['nodes'][i]
        return (counts[node['mesh']] if 'mesh' in node else 0) + sum(visit(j) for j in node.get('children', []))
    return sum(visit(i) for i in doc['scenes'][doc.get('scene', 0)]['nodes'])


def educational_material(asset, part_index):
    name = asset['id'] + '_PBR_Reconstructed_' + str(part_index)
    mat = bpy.data.materials.get(name)
    if mat:
        assert mat.get('prep_owner') == OWNER, 'Unknown material: ' + name
    else:
        mat = bpy.data.materials.new(name)
        mat['prep_owner'] = OWNER
    # For the multipart torso, distinguish source parts without naming them as organs.
    # The OBJ provides no material/segmentation labels to justify tissue assignment.
    rgba = list(asset['color'])
    if asset['parts'] > 1:
        factor = (1., .83, 1.12, .67)[part_index % 4]
        rgba = [min(.94, v * factor) for v in rgba[:3]] + [1]
    mat.use_nodes = True
    mat.diffuse_color = rgba
    nodes = mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if bsdf is None:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    if output is None:
        output = nodes.new('ShaderNodeOutputMaterial')
    if not any(link.to_node == output and link.to_socket == output.inputs['Surface'] for link in mat.node_tree.links):
        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Metallic'].default_value = 0
    bsdf.inputs['Roughness'].default_value = .58
    mat['color_provenance'] = 'Reconstructed educational palette; no clinical or semantic segmentation claim'
    mat['source_mtl_missing'] = True
    return mat


def import_sources(asset, scene, collection, sources, topology):
    scene_switch(scene)
    clear_owned_objects(collection)
    root = bpy.data.objects.new(asset['id'] + '_ROOT', None)
    collection.objects.link(root)
    root['prep_owner'] = OWNER
    root['asset_id'] = asset['id']
    root['shared_coordinates_preserved'] = True
    imported = []
    for index, src in enumerate(sources):
        before = set(bpy.data.objects)
        try:
            result = bpy.ops.wm.obj_import(filepath=disk_path(SOURCE / src['file']),
                                           forward_axis='Y', up_axis='Z')
            assert 'FINISHED' in result
        finally:
            # Only newly created objects are ever relinked or modified.
            fresh = list(set(bpy.data.objects) - before)
            for obj in fresh:
                obj['prep_owner'] = OWNER
                obj['source_file'] = src['file']
        assert fresh, 'OBJ import created no objects: ' + src['file']
        for part, obj in enumerate(fresh):
            world = obj.matrix_world.copy()
            obj.name = asset['id'] + '_Part_' + str(index).zfill(2) + '_' + str(part).zfill(2)
            for current in list(obj.users_collection):
                current.objects.unlink(obj)
            collection.objects.link(obj)
            obj.parent = root
            obj.matrix_world = world
            if obj.type == 'MESH':
                obj.data.materials.clear()
                obj.data.materials.append(educational_material(asset, index))
            imported.append(obj)
    bpy.context.view_layer.update()
    stats = geometry_stats(imported)
    proofs, source_positive = topology
    assert sum(p['sourceFanTriangles'] for p in proofs) == asset['triangles'], 'Raw OBJ fan count differs from audited source'
    minimum = sum(p['expectedImportedTrianglesMin'] for p in proofs)
    maximum = sum(p['expectedImportedTrianglesMax'] for p in proofs)
    assert minimum <= stats['triangles'] <= maximum, (asset['id'], stats['triangles'], minimum, maximum)
    imported_positive = imported_positive_triangles(imported)
    assert imported_positive == source_positive, 'Imported useful triangle geometry differs from source; do not infer harmless cleanup'
    stats['sourceFanTriangles'] = asset['triangles']
    stats['sourceRepeatedIndexFaces'] = sum(p['facesWithRepeatedVertexIndices'] for p in proofs)
    stats['positiveAreaGeometryMatchesSource'] = True
    stats['positiveAreaGeometrySha256Float32'] = topology_signature(imported_positive)
    lo = Vector(stats['boundsMin']); hi = Vector(stats['boundsMax'])
    origin = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    scale = asset['height'] / (hi.z - lo.z)
    root.matrix_world = Matrix.Scale(scale, 4) @ Matrix.Translation(-origin)
    root['display_scale_from_source_units'] = scale
    root['display_height_m'] = asset['height']
    root['educational_note'] = 'Display normalization, not clinical size or diagnostic model'
    bpy.context.view_layer.update()
    normalized = geometry_stats(imported)
    assert abs(normalized['dimensions'][2] - asset['height']) < 1e-5
    return root, imported, stats, normalized, scale


def import_glb_owned(path, scene, collection, prefix):
    scene_switch(scene)
    clear_owned_objects(collection)
    before = set(bpy.data.objects)
    try:
        result = bpy.ops.import_scene.gltf(filepath=str(path))
        assert 'FINISHED' in result
    finally:
        fresh = list(set(bpy.data.objects) - before)
        for obj in fresh:
            obj['prep_owner'] = OWNER
    for obj in fresh:
        obj.name = prefix + obj.name
        for current in list(obj.users_collection):
            current.objects.unlink(obj)
        collection.objects.link(obj)
    bpy.context.view_layer.update()
    return fresh


def render_preview(scene, collection, path, stats):
    scene_switch(scene)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('WORLD_' + scene.name)
    world['prep_owner'] = OWNER
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.11, .14, .18, 1)
    background.inputs['Strength'].default_value = .45
    scene.world = world
    lo = Vector(stats['boundsMin']); hi = Vector(stats['boundsMax'])
    center = (lo + hi) / 2
    span = max(hi - lo)
    camera_data = bpy.data.cameras.new('CAM_' + scene.name)
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    camera['prep_owner'] = OWNER
    collection.objects.link(camera)
    camera.location = center + Vector((1.1, -1.8, .85)) * span
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span * 1.4
    camera_data.clip_start = .001
    camera_data.clip_end = max(100, span * 20)
    scene.camera = camera
    for index, (offset, energy, size) in enumerate([((1, -1.7, 2), 85, 1.8), ((-1.6, -.4, .8), 48, 2), ((.2, 1.4, 1.5), 70, 1.5)]):
        data = bpy.data.lights.new('LIGHT_' + scene.name + '_' + str(index), type='AREA')
        light = bpy.data.objects.new(data.name, data)
        light['prep_owner'] = OWNER
        collection.objects.link(light)
        light.location = center + Vector(offset) * span
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
        data.energy = energy * span * span
        data.shape = 'DISK'
        data.size = size * span
    scene.render.filepath = str(path)
    result = bpy.ops.render.render(write_still=True)
    assert 'FINISHED' in result and path.is_file() and path.stat().st_size > 500
    with path.open('rb') as stream:
        data = stream.read(24)
    assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (512, 512)


def previous_object_state(objects):
    # Stored channels avoid scene-switch evaluation cache differences.
    return {o.as_pointer(): (o.name, o.type, o.parent.as_pointer() if o.parent else None,
            o.data.as_pointer() if o.data else None, tuple(o.location), tuple(o.scale),
            o.rotation_mode, tuple(o.rotation_euler), tuple(o.rotation_quaternion),
            tuple(v for row in o.matrix_parent_inverse for v in row),
            tuple(c.as_pointer() for c in o.users_collection)) for o in objects}


def main():
    assert bpy.app.version >= (5, 2, 0), 'Prepared for Blender 5.2+'
    if QA_REPORT.exists():
        assert json.loads(QA_REPORT.read_text(encoding='utf-8')).get('prepOwner') == OWNER, 'Unknown QA report already exists'
    existing_records = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else []
    assert isinstance(existing_records, list) and all(r.get('prepOwner') == OWNER for r in existing_records), 'Unknown catalog report already exists'
    records = {r['id']: r for r in existing_records}
    OUT.mkdir(parents=True, exist_ok=True)
    prepared_sources = {}
    prepared_topology = {}
    for asset in ASSETS:
        sources = []
        for index in range(asset['parts']):
            relative = str(Path(asset['folder']) / ('model_' + str(index) + '.obj'))
            source = SOURCE / relative
            assert Path(disk_path(source)).is_file(), 'Missing source: ' + str(source)
            sources.append({'file': relative, 'sha256': sha256(source), 'bytes': Path(disk_path(source)).stat().st_size})
        prepared_sources[asset['id']] = sources
        proofs = []
        positive = collections.Counter()
        for src in sources:
            proof, geometry = audit_obj_triangles(SOURCE / src['file'], src['file'])
            proofs.append(proof)
            positive.update(geometry)
        prepared_topology[asset['id']] = (proofs, positive)
        final = OUT / (asset['id'] + '.glb')
        preview = OUT / (asset['id'] + '.png')
        previous = records.get(asset['id'])
        if final.exists() or preview.exists():
            assert previous and previous.get('status') == 'validated' and previous.get('reimportValidated'), 'Unknown/incomplete output exists: ' + str(final)
            assert previous['sourceFiles'] == sources, 'Sources changed; preserve previous derivative and choose a new ID'
            assert final.is_file() and sha256(final) == previous['sha256'], 'Existing GLB differs from recorded bytes'
            assert preview.is_file() and sha256(preview) == previous['previewSha256'], 'Existing preview differs from recorded bytes'
    # Reject unrelated existing scene/collection names before any import.
    for name in [SCENE] + ['PREP_ANAT_' + a['id'] for a in ASSETS]:
        value = bpy.data.scenes.get(name) or bpy.data.collections.get(name)
        assert value is None or value.get('prep_owner') == OWNER, 'Unknown existing datablock: ' + name
    old_objects = tuple(o for o in bpy.data.objects if o.get('prep_owner') != OWNER)
    old_state = previous_object_state(old_objects)
    old_windows = [(w, w.scene) for w in bpy.context.window_manager.windows]
    qa_results = []
    scene = owned_scene(SCENE)
    top = owned_collection(scene, SCENE)
    scene['purpose'] = 'Four supplied anatomy assemblies with reconstructed educational materials and display scale'
    try:
        for slot, asset in enumerate(ASSETS):
            ident = asset['id']
            sources = prepared_sources[ident]
            final = OUT / (ident + '.glb')
            preview = OUT / (ident + '.png')
            collection = owned_collection(scene, 'PREP_ANAT_' + ident, top)
            if final.exists():
                # Idempotent reuse only after exact ownership/source/output hashes match.
                if not mesh_objects(collection.all_objects):
                    restored = import_glb_owned(final, scene, collection, '')
                    for obj in restored:
                        if obj.parent is None:
                            obj.location.x += (slot - 1.5) * 1.4
                qa_results.append({'id': ident, 'reusedValidatedOutput': True, 'sha256': records[ident]['sha256']})
                continue
            token = uuid.uuid4().hex[:10]
            staging_glb = OUT / ('.' + ident + '.' + token + '.staging.glb')
            staging_preview = OUT / ('.' + ident + '.' + token + '.staging.png')
            root, objects, original_stats, normalized, scale = import_sources(asset, scene, collection, sources, prepared_topology[ident])
            scene_switch(scene)
            for obj in scene.objects:
                obj.select_set(False)
            for obj in [root] + objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = root
            status = bpy.ops.export_scene.gltf(filepath=str(staging_glb), export_format='GLB',
                use_selection=True, use_active_scene=True, export_yup=True, export_apply=True,
                export_animations=False, export_skins=False, export_cameras=False,
                export_lights=False, export_extras=True, export_materials='EXPORT',
                export_texcoords=True, export_normals=True)
            assert 'FINISHED' in status and staging_glb.is_file()
            doc = glb_document(staging_glb)
            assert not doc.get('skins') and not doc.get('animations'), 'Unexpected generated rig/animation'
            expected = glb_scene_triangles(doc)
            assert 0 < expected <= original_stats['triangles'], 'Unexpected exported triangle count'
            qa = owned_scene('PREP_ANATOMY_QA_' + str(slot + 1) + '_20261016')
            qa_collection = owned_collection(qa, 'QA_ANAT_' + ident)
            imported = import_glb_owned(staging_glb, qa, qa_collection, 'QA16_')
            actual = geometry_stats(imported)
            assert actual['triangles'] == expected, (actual['triangles'], expected)
            tolerance = max(1e-5, max(normalized['dimensions']) * 1e-4)
            assert all(abs(a - b) <= tolerance for a, b in zip(actual['dimensions'], normalized['dimensions'])), 'Roundtrip bounds changed'
            assert not any(o.type == 'ARMATURE' for o in imported)
            helpers = owned_collection(qa, 'QA_ANAT_HELPERS_' + str(slot + 1) + '_20261016')
            clear_owned_objects(helpers)
            render_preview(qa, helpers, staging_preview, actual)
            assert not final.exists() and not preview.exists(), 'Output appeared during preparation; preserve it'
            staging_glb.rename(final)
            staging_preview.rename(preview)
            # All parts receive the same gallery offset only after export and roundtrip.
            root.location.x += (slot - 1.5) * 1.4
            record = {'id': ident, 'name': asset['name'], 'category': 'Anatomia',
                'sourceRelative': sources[0]['file'], 'sourceFiles': sources,
                'sourceSha256': sources[0]['sha256'] if len(sources) == 1 else hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
                'sourceHashMethod': 'file-sha256' if len(sources) == 1 else 'sha256-of-json-sourceFiles-sort-keys',
                'originalTriangles': asset['triangles'], 'sourceFanTriangles': asset['triangles'],
                'importedTriangles': original_stats['triangles'], 'credits': {},
                'licenseStatus': 'unknown', 'status': 'validated', 'reimportValidated': True,
                'url': '/assets/additions20261016/' + final.name, 'bytes': final.stat().st_size,
                'sha256': sha256(final), 'triangles': actual['triangles'], 'meshes': actual['meshes'],
                'dimensions': actual['dimensions'], 'dimensionsConvention': 'Blender X/Y/Z meters; GLB exports Y up',
                'animated': False, 'animations': [], 'originalRig': False, 'skins': 0,
                'preparedTriangles': normalized['triangles'], 'meshPrimitiveTriangles': expected,
                'sourceBounds': original_stats, 'displayScaleFromSourceUnits': scale,
                'sourceTopologyProof': prepared_topology[ident][0],
                'importedPositiveAreaGeometryMatchesSource': True,
                'displayHeightMeters': asset['height'], 'scaleMeaning': 'Educational display scale; not clinical measurements',
                'materialRecovery': 'PBR colors reconstructed per assembly/source part; supplied MTL missing; no diagnostic or tissue segmentation claim',
                'textureRecovery': 'No PNG association inferred; UVs retained when supplied; no reliable MTL or per-face material labels',
                'modifications': 'OBJ importer rejects repeated-index zero-area face records; all positive-area source triangles independently matched by coordinates. Shared coordinates preserved; one assembly root centers/scales display; reconstructed PBR educational palette; no mesh reduction or rig generation',
                'validation': 'Source topology diagnosis plus exact float32 positive-area triangle multiset match before normalization; exported GLB reimported with exact delivered triangle count; finite vertices/world bounds; source/display bounds compared; actual Blender 512px PNG rendered',
                'preview': '/assets/additions20261016/' + preview.name, 'previewSha256': sha256(preview),
                'previewSize': [512, 512], 'previewEvidence': 'Actual reimported model rendered by Blender EEVEE',
                'scene': SCENE, 'collection': collection.name, 'qaScene': qa.name,
                'sourceParts': len(sources), 'prepOwner': OWNER}
            records[ident] = record
            write_json(REPORT, [records[a['id']] for a in ASSETS if a['id'] in records])
            qa_results.append({'id': ident, 'sourceFanTriangles': asset['triangles'],
                               'importedTriangles': original_stats['triangles'],
                               'exportedTriangles': expected, 'reimport': actual, 'preview': str(preview)})
        # Original stored transforms, parenting, mesh pointers and collection links must survive.
        assert previous_object_state(old_objects) == old_state, 'An existing object was modified'
        write_json(QA_REPORT, {'prepOwner': OWNER, 'status': 'validated', 'assets': qa_results,
            'previousObjectsPreserved': len(old_objects), 'previousStoredStateUnchanged': True,
            'masterSaved': False, 'runtimeManifestChanged': False, 'sourceFilesChanged': False,
            'scene': SCENE, 'catalogEntriesReport': str(REPORT), 'blenderVersion': bpy.app.version_string})
        print('PREP_ANATOMY_IMPORT_20261016 ' + json.dumps({'status': 'validated', 'assets': len(ASSETS),
              'scene': SCENE, 'catalog': str(REPORT), 'masterSaved': False}))
    except Exception:
        write_json(QA_REPORT, {'prepOwner': OWNER, 'status': 'failed', 'error': traceback.format_exc(),
            'completedAssets': qa_results, 'masterSaved': False, 'originalFilesModified': False})
        raise
    finally:
        for window, previous_scene in old_windows:
            window.scene = previous_scene


if __name__ == '__main__':
    main()
