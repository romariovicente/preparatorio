"""Import supplied animated animals through the live Blender MCP session.

Only newly imported roots are normalized. Source files, armature rest poses,
weights, actions and previous project objects remain untouched.
"""
import bpy, contextlib, hashlib, io, json, math, shutil, struct, sys
from pathlib import Path
from datetime import datetime
from mathutils import Vector

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
sys.path.insert(0, str(ROOT / 'scripts'))
from prep_object_state_20261015 import object_state, state_hash
AUDIT = json.loads((ROOT / 'reports/SUPPLIED_ASSET_AUDIT_20261016.json').read_text(encoding='utf-8'))
SOURCE = Path(AUDIT['source_root'])
OUT = ROOT / 'frontend/public/assets/additions20261016'
OUT.mkdir(parents=True, exist_ok=True)
REPORT = ROOT / 'reports/fauna_catalog_entries_20261016.json'
MASTER = ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve() == MASTER.resolve()
SPECS = [
    ('FOX', 'Raposa', r'Animais Terrestres\FOX - Realistic 3D Model\fox_-_realistic_3d_model_demo_free.glb', .65),
    ('LIONESS', 'Leoa', r'Animais Terrestres\LIONESS - Realistic 3D Model\lioness_-_realistic_3d_model_demo_free.glb', 1.15),
    ('RABBIT', 'Coelho', r'Animais Terrestres\RABBIT - Realistic 3D Model\rabbit_-_realistic_3d_model_demo_free.glb', .45),
    ('WOLF', 'Lobo', r'Animais Terrestres\WOLF - Realistic 3D Model\wolf_-_realistic_3d_model_demo_free.glb', .95),
    ('HORSE', 'Cavalo com sela', r'Montarias dos Personagens\HORSE - Realistic 3D Model\horse_-_realistic_3d_model_demo_free.glb', 2.25),
    ('MEGALODON', 'Megalodonte', r'Animais Marinhos\megalodon\megalodon.glb', None),
]
records = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else []
prior = list(bpy.data.objects)
baseline = object_state(prior)
baseline_hash = state_hash(baseline)
(ROOT / 'art/blender/checkpoints/ASSETS_BEFORE_FAUNA_20261016.json').write_text(
    json.dumps({'state': baseline, 'hash': baseline_hash}, ensure_ascii=False), encoding='utf-8')

def switch(scene):
    for window in bpy.context.window_manager.windows:
        window.scene = scene
    assert bpy.context.scene == scene

def new_scene(name):
    assert name not in bpy.data.scenes, 'Inspect partial scene before rerunning: ' + name
    scene = bpy.data.scenes.new(name)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 501
    switch(scene)
    return scene

def evaluated_points(objects, sample=False):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        used = sorted({index for poly in mesh.polygons for index in poly.vertices})
        if sample:
            used = used[::max(1, len(used) // 150)]
        points.extend(ev.matrix_world @ mesh.vertices[index].co for index in used)
        ev.to_mesh_clear()
    assert points and all(math.isfinite(v) for point in points for v in point)
    return points

def bounds(objects):
    points = evaluated_points(objects)
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    return lo, hi

def glb_document(path):
    data = path.read_bytes()
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    return json.loads(data[20:20 + length])

def triangle_count(objects):
    total = 0
    for obj in objects:
        if obj.type == 'MESH':
            obj.data.calc_loop_triangles()
            total += len(obj.data.loop_triangles)
    return total

def point_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()

def activate_imported_clip(objects, clip):
    # Match the importer's NLA start offset on both sides of the roundtrip.
    for obj in objects:
        ad = obj.animation_data
        if not ad:
            continue
        matching = [track for track in ad.nla_tracks if track.name == clip]
        if matching:
            ad.action = None
            for track in ad.nla_tracks:
                track.mute = track not in matching

def render_preview(scene, objects, target):
    lo, hi = bounds(objects)
    center = (lo + hi) * .5
    span = max(hi - lo)
    studio = bpy.data.collections.new('PREP_STUDIO_' + target.stem)
    scene.collection.children.link(studio)
    cd = bpy.data.cameras.new('CAM_' + target.stem)
    cam = bpy.data.objects.new(cd.name, cd)
    studio.objects.link(cam)
    cam.location = center + Vector((1.45, -1.6, .75)) * span
    point_at(cam, center)
    cd.type = 'ORTHO'
    cd.ortho_scale = span * 1.3
    cd.clip_end = max(1000, span * 10)
    scene.camera = cam
    for name, offset, power, color in [('Key', (1, -1.2, 2), 190, (1, .94, .88)),
            ('Fill', (-1, -.4, .7), 100, (.8, .9, 1)), ('Rim', (0, 1.2, 1.5), 180, (1, 1, 1))]:
        ld = bpy.data.lights.new('LIGHT_' + target.stem + name, 'AREA')
        lamp = bpy.data.objects.new(ld.name, ld)
        studio.objects.link(lamp)
        lamp.location = center + Vector(offset) * span
        point_at(lamp, center)
        ld.energy = power * span * span
        ld.size = span * 1.5
        ld.color = color
    world = bpy.data.worlds.new('WORLD_' + target.stem)
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (.07, .095, .13, 1)
    bg.inputs['Strength'].default_value = .5
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    assert target.exists()

for code, label, relative, height in SPECS:
    key = 'FAUNA_' + code + '_20261016'
    existing = next((r for r in records if r['id'] == key), None)
    if existing:
        path = ROOT / 'frontend/public' / existing['url'].lstrip('/')
        assert existing['status'] == 'validated' and hashlib.sha256(path.read_bytes()).hexdigest() == existing['sha256']
        assert existing['blenderScene'] in bpy.data.scenes
        continue
    source = SOURCE / relative
    meta = next(m for m in AUDIT['models'] if m['relative'] == relative)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == meta['sha256']
    dest = OUT / (key + '.glb')
    preview = OUT / (key + '.jpg')
    assert not dest.exists() and not preview.exists(), 'Existing unvalidated outputs require inspection.'
    scene = new_scene('PREP_FAUNA_' + code + '_20261016')
    scene['purpose'] = 'Supplied animal with original rig and clips; separate from playable city.'
    before_objects, before_images = set(bpy.data.objects), set(bpy.data.images)
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        assert 'FINISHED' in bpy.ops.import_scene.gltf(filepath=str(source))
    all_new = set(bpy.data.objects) - before_objects
    helpers = [o for o in all_new if any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
    imported = sorted(all_new - set(helpers), key=lambda o:o.name)
    meshes = [o for o in imported if o.type == 'MESH']
    armatures = [o for o in imported if o.type == 'ARMATURE']
    assert meshes and armatures
    collection = bpy.data.collections.new('PREP_CITY_FAUNA_' + code)
    scene.collection.children.link(collection)
    for obj in imported:
        collection.objects.link(obj)
        for old in list(obj.users_collection):
            if old != collection:
                old.objects.unlink(obj)
        obj['prep_asset_id'] = key
        obj['source_sha256'] = meta['sha256']
    # A single outer root preserves all skin inverse binds and animated local channels.
    root = bpy.data.objects.new('ROOT_' + key, None)
    collection.objects.link(root)
    for obj in imported:
        if obj.parent is None:
            obj.parent = root
    source_clips = [a['name'] for a in meta['metadata']['animations']]
    reference_clip = next((n for token in ['Idle','Stand','Walk'] for n in source_clips if token in n), source_clips[0])
    activate_imported_clip(imported, reference_clip)
    scene.frame_set(1)
    lo, hi = bounds(meshes)
    original_bounds = [list(lo), list(hi)]
    size = hi - lo
    scale = height / size.z if height else 12.0 / max(size)
    assert 1e-6 < scale < 1e6
    root.scale = (scale,) * 3
    root.location = Vector((-(lo.x + hi.x) * .5, -(lo.y + hi.y) * .5, -lo.z)) * scale
    lo, hi = bounds(meshes)
    normalized_dims = list(hi - lo)
    assert abs(lo.z) < 1e-4 and min(normalized_dims) > 0
    for image in set(bpy.data.images) - before_images:
        if image.type == 'IMAGE' and min(image.size) > 0 and image.users:
            image.pack()
    for obj in scene.objects:
        obj.select_set(False)
    for obj in imported + [root]:
        obj.select_set(True)
    # These sources are already self-contained runtime GLBs. A trial Blender
    # skin re-export changed the pose, so publish the exact verified original
    # bytes and keep normalization as an outer display transform on each import.
    # Failed derivatives remain preserved in checkpoints, never in the catalog.
    shutil.copyfile(source, dest)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == meta['sha256']
    doc = glb_document(dest)
    clips = [a.get('name', '') for a in doc.get('animations', [])]
    assert set(clips) == set(source_clips), (clips, source_clips)
    assert len(doc.get('skins', [])) == len(armatures)
    source_bones = [len(a.data.bones) for a in armatures]
    # Separate scene retains the exact delivered hierarchy for independent inspection.
    qa = new_scene('PREP_FAUNA_QA_' + code + '_20261016')
    before_qa = set(bpy.data.objects)
    with contextlib.redirect_stdout(capture):
        assert 'FINISHED' in bpy.ops.import_scene.gltf(filepath=str(dest))
    reimported = [o for o in set(bpy.data.objects) - before_qa if not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
    qa_meshes = [o for o in reimported if o.type == 'MESH']
    qa_arms = [o for o in reimported if o.type == 'ARMATURE']
    assert len(qa_arms) == len(armatures)
    assert [len(a.data.bones) for a in qa_arms] == source_bones
    qa_root = bpy.data.objects.new('QA_ROOT_' + key, None)
    qa.collection.objects.link(qa_root)
    for obj in reimported:
        if obj.parent is None:
            obj.parent = qa_root
    qa_root.scale = root.scale
    qa_root.location = root.location
    activate_imported_clip(reimported, reference_clip)
    qa.frame_set(1)
    qlo, qhi = bounds(qa_meshes)
    tolerance = max(normalized_dims) * .001 + .0001
    assert max(abs(a-b) for a,b in zip(list(lo)+list(hi), list(qlo)+list(qhi))) < tolerance, (list(lo),list(hi),list(qlo),list(qhi),reference_clip)
    assert triangle_count(meshes) == triangle_count(qa_meshes)
    samples = []
    for frame in [1, 9, 17]:
        qa.frame_set(frame)
        samples.append(evaluated_points(qa_meshes, sample=True))
    motion = max((a-b).length for a,b in zip(samples[0], samples[1]))
    motion = max(motion, max((a-b).length for a,b in zip(samples[0], samples[2])))
    assert motion > .00001, 'No evaluated motion survived export/reimport: ' + key
    qa.frame_set(1)
    record = {'id': key, 'name': label, 'category': 'Animais', 'status': 'validated',
        'sourceRelative': relative, 'sourceSha256': meta['sha256'], 'credits': meta['metadata']['asset'].get('extras', {}),
        'licenseStatus': 'supplied embedded attribution; preserve original license terms',
        'url': '/assets/additions20261016/' + dest.name, 'preview': '/assets/additions20261016/' + preview.name,
        'bytes': dest.stat().st_size, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
        'triangles': triangle_count(qa_meshes), 'originalTriangles': meta['metadata']['triangles_mesh_definitions'],
        'dimensions': normalized_dims, 'height': normalized_dims[2], 'animated': True, 'animations': clips, 'rigged': True,
        'originalRig': True, 'playable': False, 'visualStyle': 'realistic', 'reimportValidated': True,
        'blenderScene': scene.name, 'qaScene': qa.name, 'boneCounts': source_bones, 'referenceClip': reference_clip,
        'excludedImporterHelpers': len(helpers),
        'roundtrip': {'matchingBounds': True, 'matchingTriangles': True, 'matchingBoneCount': True,
            'finiteEvaluatedVertices': True, 'sampleFrames': [1,9,17], 'maxSampleMotionMeters': motion},
        'normalization': {'sourceEvaluatedBounds': original_bounds, 'uniformRootScale': scale,
            'displayHeightMeters': height, 'lengthMeters': 12 if height is None else None,
            'note': 'Approximate presentation scale; no claim of measured specimen size.'},
        'modifications': 'Delivered GLB is byte-identical to supplied source. Blender display uses an outer parent only; source skeleton, inverse binds, weights, materials and clips retained without skin re-export.',
        'deliveryMethod': 'verified-original-glb-copy; Blender source and independent reimport both evaluated at matching display transforms',
        'tags': ['fauna', 'marinho' if code == 'MEGALODON' else 'terrestre', 'esqueleto original', 'animação'],
        'description': 'Modelo fornecido com esqueleto e movimentos próprios, disponível para inspeção animada.',
        'timeLocal': datetime.now().astimezone().isoformat(timespec='seconds')}
    render_preview(qa, qa_meshes, preview)
    (ROOT / ('reports/fauna_' + code.lower() + '_20261016.log')).write_text(capture.getvalue(), encoding='utf-8')
    records.append(record)
    REPORT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    assert state_hash(object_state(prior)) == baseline_hash, 'A preexisting stored object channel changed.'
    print('PREP_FAUNA_VALIDATED ' + json.dumps({k:record[k] for k in ['id','triangles','animations','boneCounts','dimensions']}))

assert len(records) == len(SPECS)
switch(bpy.data.scenes['PREP_FAUNA_QA_FOX_20261016'])
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), check_existing=False)
print('PREP_FAUNA_SAVED ' + json.dumps({'assets':len(records),'scenes':len(bpy.data.scenes),'objects':len(bpy.data.objects),'masterBytes':MASTER.stat().st_size,'previousObjectChannelsMatch':True}))
