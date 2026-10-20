"""Assemble the campus and six resident habitats in the live Blender MCP session.

Run once, after the AMG/Warp operations finish. Never launch another Blender.
Revised on 20 October. This script reuses a checkpoint only when its complete
object snapshot matches the live state; otherwise it makes a compressed copy
before any scene edits. It does not replace the Oct16 master and writes only
the new scene's dependency closure to PREPARATORIO_CITY_LIVING_20261020.blend.
No GLB is exported or modified. The historical script filename is retained.

Set PREP_CITY_LIVING_RENDER=True in the exec globals to render the configured
Cycles CPU/24-sample overview in the same call. Default: configure and save the
scene, leaving the render to a separate MCP call for a shorter operation.
"""
from pathlib import Path
from datetime import datetime, timezone
import contextlib
import hashlib
import io
import json
import math
import re
import struct
import sys
import bpy
from mathutils import Vector

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
WORK = ROOT.parent.parent / 'work' / 'habitat-audit'
PLAN_PATH = WORK / 'blender-assembly-plan.json'
CPU_PATH = WORK / 'living-model-validation.json'
CHECKPOINT_REPORT = ROOT / 'reports/CITY_ADDITIONS_CHECKPOINT_20261019.json'
MASTER = ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend'
OUTPUT = ROOT / 'art/blender/PREPARATORIO_CITY_LIVING_20261020.blend'
REPORT_PATH = ROOT / 'reports/CITY_LIVING_BLENDER_20261020.json'
PREVIEW = ROOT / 'reports/city_living_overview_20261020.png'
SCENE_NAME = 'PREP_CITY_LIVING_20261020'
OWNER = 'preparatorio-city-living-20261020-v2'
PREFIX = 'CLW20_'
RENDER = bool(globals().get('PREP_CITY_LIVING_RENDER', False))
sys.path.insert(0, str(ROOT / 'scripts'))
from prep_object_state_20261015 import object_state, state_hash
from prep_incremental_scene_tools_20261020 import checkpoint_before, import_fresh, visible, freeze_pose


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def document(path):
    raw = path.read_bytes()
    if raw[:4] != b'glTF' or struct.unpack_from('<I', raw, 4)[0] != 2:
        raise RuntimeError('Only audited GLB2 sources are accepted: ' + str(path))
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A:
        raise RuntimeError('First GLB chunk must be JSON.')
    return json.loads(raw[20:20 + length])


def point(frontend):
    return Vector((frontend[0], -frontend[2], frontend[1]))


def canonical(name):
    # Blender may suffix an already suffixed source node when the same asset
    # exists in an older scene. Only newly imported objects use this matcher.
    return re.sub(r'(?:\.\d+)+$', '', str(name))


def source_name(obj):
    return obj.get('asset_node_name', obj.get('prep_source_node_name', obj.name))


def helper(obj):
    normalized = re.sub(r'[^a-z0-9]', '', canonical(source_name(obj)).lower())
    return (any(c.name.startswith('glTF_not_exported') for c in obj.users_collection)
            or normalized in {'icosphere', 'esferaicosaedrica'})


def collection(scene, name):
    result = bpy.data.collections.new(PREFIX + name)
    scene.collection.children.link(result)
    return result


def empty(target, name, parent=None):
    result = bpy.data.objects.new(PREFIX + name, None)
    target.objects.link(result)
    result.parent = parent
    result['owner'] = OWNER
    return result


def evaluated_bounds(objects):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    low = Vector((math.inf,) * 3)
    high = Vector((-math.inf,) * 3)
    count = 0
    for obj in objects:
        if obj.type != 'MESH' or not visible(obj) or helper(obj):
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            used = {index for polygon in mesh.polygons for index in polygon.vertices}
            for index in used:
                p = evaluated.matrix_world @ mesh.vertices[index].co
                if not all(math.isfinite(v) for v in p):
                    raise RuntimeError('Nonfinite evaluated vertex: ' + obj.name)
                for axis in range(3):
                    low[axis] = min(low[axis], p[axis])
                    high[axis] = max(high[axis], p[axis])
                count += 1
        finally:
            evaluated.to_mesh_clear()
    if not count:
        raise RuntimeError('No evaluated visible geometry for the asset.')
    return low, high


def bounds_json(bounds):
    lo, hi = bounds
    return {'min': list(lo), 'max': list(hi), 'size': list(hi - lo)}


def import_asset(scene, target, spec, expected_sha):
    path = (ROOT / spec['sourceFile']).resolve()
    fresh, doc, source_hash, import_log = import_fresh(scene, target, spec['assetId'], path, OWNER, expected_sha)
    return fresh, doc, path, import_log


def activate_clip(objects, name):
    matched = []
    inventory = []
    for obj in objects:
        ad = obj.animation_data
        if not ad:
            continue
        tracks = list(ad.nla_tracks)
        chosen = [track for track in tracks if canonical(track.name) == canonical(name)]
        if chosen:
            ad.action = None
            for track in tracks:
                track.mute = track not in chosen
                if track in chosen:
                    track.is_solo = False
            matched.extend(obj.name + '/' + track.name for track in chosen)
        elif ad.action and canonical(ad.action.name) == canonical(name):
            matched.append(obj.name + '/action:' + ad.action.name)
        inventory.append({'object': obj.name, 'activeAction': ad.action.name if ad.action else None,
                          'tracks': [{'name': track.name, 'muted': track.mute,
                                      'strips': [{'name': strip.name, 'action': strip.action.name if strip.action else None,
                                                  'start': strip.frame_start, 'end': strip.frame_end}
                                                 for strip in track.strips]}
                                     for track in tracks]})
    if not matched:
        raise RuntimeError('Original clip not found after import: ' + name)
    return {'selected': name, 'matched': matched, 'inventory': inventory,
            'sourceActionsAndNlaRetained': True, 'rootMotionBakedOrEdited': False}


def place_source(target, objects, name):
    placement = empty(target, name + '_PLACEMENT')
    normalized = empty(target, name + '_NORMALIZATION', placement)
    own = set(objects)
    for obj in objects:
        if obj.parent not in own:
            obj.parent = normalized
    return placement, normalized


def armature_point(objects, name=None, head=False):
    for armature in objects:
        if armature.type != 'ARMATURE':
            continue
        for bone in armature.pose.bones:
            if (head and re.match(r'^head(?:[_\d]|$)', bone.name, re.I)) or (not head and bone.name == name):
                return armature.matrix_world @ bone.matrix.translation
    return None


def path_pose(spec):
    rx, rz = spec['pathRadii']
    phase = spec['phase']
    return {'x': math.cos(phase) * rx, 'z': math.sin(phase) * rz,
            'y': (spec.get('swimBaseY', 0) + math.sin(phase * 2) * .035) if spec['kind'] == 'aquarium' else 0,
            'heading': math.atan2(-math.sin(phase) * rx, math.cos(phase) * rz) if rx or rz else phase}


def material(name, color, alpha=1, metallic=0, roughness=.65):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    shader = next(node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Alpha'].default_value = alpha
    if alpha < 1 and hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'DITHERED'
    return mat


BOX_MESHES = {}


def box(target, name, center, dimensions, mat, walkable=False):
    if mat not in BOX_MESHES:
        mesh = bpy.data.meshes.new(PREFIX + 'UNIT_' + mat.name)
        mesh.from_pydata([(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
                          (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)], [],
                         [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        mesh.materials.append(mat)
        mesh.update()
        BOX_MESHES[mat] = mesh
    obj = bpy.data.objects.new(PREFIX + name, BOX_MESHES[mat])
    target.objects.link(obj)
    obj.location = center
    obj.scale = dimensions
    obj['owner'] = OWNER
    obj['walkable'] = walkable
    return obj


def label(target, name, text, location, mat, size=.13):
    curve = bpy.data.curves.new(PREFIX + name, 'FONT')
    curve.body = text
    curve.size = size
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.space_line = 1.05
    curve.extrude = .001
    curve.materials.append(mat)
    obj = bpy.data.objects.new(PREFIX + name, curve)
    target.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.pi / 2, 0, 0)
    obj['owner'] = OWNER
    return obj


def studio(scene, target):
    center = Vector((-48, 150, 1.8))
    camera_data = bpy.data.cameras.new(PREFIX + 'CAMERA_OVERVIEW')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    target.objects.link(camera)
    camera.location = Vector((36, 54, 95))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 117
    camera_data.clip_start = .1
    camera_data.clip_end = 500
    scene.camera = camera
    for name, position, energy, area_size, color in [
            ('KEY', (-40, 112, 75), 155000, 65, (1, .95, .88)),
            ('FILL', (5, 175, 45), 80000, 50, (.78, .9, 1)),
            ('RIM', (-105, 195, 40), 70000, 45, (.85, .96, 1))]:
        data = bpy.data.lights.new(PREFIX + name, 'AREA')
        light = bpy.data.objects.new(data.name, data)
        target.objects.link(light)
        light.location = position
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
        data.energy = energy
        data.shape = 'DISK'
        data.size = area_size
        data.color = color
    world = bpy.data.worlds.new(PREFIX + 'WORLD')
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.11, .16, .21, 1)
    background.inputs['Strength'].default_value = .55
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(PREVIEW)
    scene.view_settings.view_transform = 'AgX'


def main():
    if Path(bpy.data.filepath).resolve() != MASTER.resolve() or not MASTER.is_file():
        raise RuntimeError('Keep the existing Oct16 master open in the live MCP session.')
    if (bpy.data.scenes.get(SCENE_NAME) or bpy.data.scenes.get('PREP_CITY_LIVING_20261019')
            or OUTPUT.exists() or REPORT_PATH.exists()):
        raise RuntimeError('Owned scene/output/report already exists. Inspect it; never duplicate a partial assembly.')
    plan = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
    cpu = json.loads(CPU_PATH.read_text(encoding='utf-8'))
    runtime_path = ROOT / 'frontend/src/config/cityLivingWorld.json'
    runtime = json.loads(runtime_path.read_text(encoding='utf-8'))
    if plan['campus']['position'] != runtime['campus']['position'] or runtime['campus']['scale'] != 1:
        raise RuntimeError('Assembly plan and current playable campus placement disagree.')
    runtime_habitats = {item['id']: item for item in runtime['habitats']}
    for habitat in plan['habitats']:
        current = runtime_habitats[habitat['id']]
        for key in ('assetId', 'position', 'size', 'height', 'clip', 'pathRadii', 'phase', 'fenceHeight'):
            if habitat[key] != current[key]:
                raise RuntimeError('Assembly plan differs from runtime: ' + habitat['id'] + '/' + key)
        if habitat['pad']['topY'] != .23 or habitat['position'][1] != .23:
            raise RuntimeError('Preserve the 0.23 m habitat walking floor.')
    access = runtime['district']['access']
    if access['width'] != 5 or access['from'] != [-49, .23, -111] or access['to'] != [-49, .23, -134]:
        raise RuntimeError('The same-city northern pedestrian connection changed; audit again.')
    if len(plan['habitats']) != 6 or len(cpu['animals']) != 6:
        raise RuntimeError('Expected exactly six independently CPU-validated habitats.')
    expected = {item['assetId']: item for item in cpu['animals']}
    for habitat in plan['habitats']:
        item = expected[habitat['assetId']]
        if not item['insideBoundary'] or not item['belowWater'] or not item['limitLength']:
            raise RuntimeError('Runtime animal validation did not pass: ' + habitat['assetId'])
    prior = list(bpy.data.objects)
    reusable_reports = [Path(path) for path in globals().get('PREP_REUSE_CHECKPOINT_REPORTS', [])]
    reusable_reports += [ROOT/'reports/CITY_LIVING_CHECKPOINT_20261020.json',
                         ROOT/'reports/CONTINUATION_CHECKPOINT_20261020.json', CHECKPOINT_REPORT]
    checkpoint = checkpoint_before('CITY_LIVING', prior, reusable_reports, allow_known_additions=True)
    previous_state = state_hash(object_state(prior))
    previous_images = set(bpy.data.images)
    master_stat = (MASTER.stat().st_size, MASTER.stat().st_mtime_ns)
    previous_scene = bpy.context.window.scene.name
    scene = bpy.data.scenes.new(SCENE_NAME)
    scene['owner'] = OWNER
    scene['author'] = plan['author']
    scene['purpose'] = 'Same-city northern campus and six original-rig managed habitats; no macro4km activation.'
    scene['frontend_config'] = 'frontend/src/config/cityLivingWorld.json'
    scene['motion_note'] = 'Principal pose at source clip t=0/frame1. Original clips retained. Browser performs horizontal drift compensation and route animation.'
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 1500
    bpy.context.window.scene = scene
    report = {'owner': OWNER, 'scene': SCENE_NAME, 'createdAt': datetime.now(timezone.utc).isoformat(),
              'author': plan['author'], 'plan': str(PLAN_PATH), 'planSha256': digest(PLAN_PATH),
              'checkpoint': checkpoint, 'runtimeConfigSha256': digest(runtime_path),
              'newLargeMasterCheckpointCreated': not checkpoint['reused'], 'masterSavedByThisScript': False,
              'master': str(MASTER), 'previousScene': previous_scene, 'status': 'assembling',
              'assets': [], 'publicGLBExported': False, 'principalFrame': 1,
              'browserVisualQA': False, 'rendered': False}
    try:
        structures = collection(scene, 'DISTRICT_STRUCTURES')
        campus_collection = collection(scene, 'CAMPUS_ORIGINAL')
        camera_collection = collection(scene, 'OVERVIEW')
        grass = material('GRASS', (.31, .39, .3), roughness=1)
        path_mat = material('WALKWAY', (.59, .66, .66), roughness=.9)
        rail_mat = material('BOUNDARY_METAL', (.075, .14, .17), metallic=.65, roughness=.35)
        land_glass = material('LAND_BOUNDARY_GLASS', (.43, .65, .65), alpha=.095, metallic=.1, roughness=.18)
        tank_glass = material('AQUARIUM_GLASS', (.36, .69, .76), alpha=.16, metallic=.1, roughness=.18)
        water = material('WATER_SURFACE', (.12, .49, .64), alpha=.25, roughness=.2)
        label_mat = material('LETTERING', (.88, .97, 1), roughness=.5)
        for part, mat in [(plan['ground'], grass), (plan['pedestrianAccess'], path_mat)]:
            box(structures, part['id'], part['blenderCenter'], part['blenderSize'], mat, walkable=True)
        campus_spec = plan['campus']
        campus, campus_doc, campus_path, campus_log = import_asset(scene, campus_collection, campus_spec, cpu['campus']['sha256'])
        hidden = {canonical(name) for name in campus_spec['hideNodes']}
        hidden_objects = []
        for obj in campus:
            if canonical(source_name(obj)) in hidden:
                obj.hide_render = True
                obj.hide_set(True)
                hidden_objects.append(obj.name)
            if canonical(source_name(obj)) == 'Patio':
                obj['walkable'] = True
        if len(hidden_objects) != 6:
            raise RuntimeError('Hide exactly the six redundant campus terrain/building nodes, found ' + str(hidden_objects))
        campus_placement, _ = place_source(campus_collection, campus, 'CAMPUS')
        campus_placement.location = campus_spec['blenderPosition']
        scene.frame_set(1)
        campus_bounds = evaluated_bounds(campus)
        lo, hi = campus_bounds
        if not (lo.x >= -61.51 and hi.x <= -36.49 and lo.y >= 133.99 and hi.y <= 162.01):
            raise RuntimeError('Retained campus no longer fits its 25x28m courtyard.')
        report['campus'] = {'assetId': campus_spec['assetId'], 'source': str(campus_path), 'sha256': digest(campus_path),
                            'scale': 1, 'boundsBlender': bounds_json(campus_bounds), 'hiddenRedundantNodes': hidden_objects,
                            'sourceNodeCount': len(campus_doc['nodes']), 'furnitureAndAnatomyRetained': True}
        label(structures, 'CAMPUS_SIGN', 'CAMPUS PREPARATÓRIO\nAnatomia · estudos · observação da fauna', point((-49, 2.4, -132)), label_mat, size=.4)
        for habitat in plan['habitats']:
            h = habitat
            target = collection(scene, h['id'].upper())
            objects, doc, source, import_log = import_asset(scene, target, h, expected[h['assetId']]['sha256'])
            clip = activate_clip(objects, h['clip'])
            placement, normalized = place_source(target, objects, h['assetId'])
            scene.frame_set(1)
            before_bounds = evaluated_bounds(objects)
            low, high = before_bounds
            size = high - low
            factor = h['targetLengthMeters'] / max(size.x, size.y) if h.get('targetLengthMeters') else h['height'] / size.z
            if not 1e-6 < factor < 1e6:
                raise RuntimeError('Invalid uniform display scale: ' + h['assetId'])
            if not math.isclose(factor, expected[h['assetId']]['scaleFactor'], rel_tol=.035):
                raise RuntimeError('Evaluated pose disagrees with the CPU skin evaluation; never normalize a stale1km bound: ' + h['assetId'])
            anchor = armature_point(objects, h.get('anchorBone')) if h.get('anchorBone') else None
            head = armature_point(objects, head=True)
            forward_yaw = math.atan2((head-anchor).x, -(head-anchor).y) if head is not None and anchor is not None else 0
            normalized.scale = (factor,) * 3
            normalized.location = Vector((-(low.x+high.x)/2, -(low.y+high.y)/2, -low.z)) * factor
            pose = path_pose(h)
            placement.location = point(h['position']) + point((pose['x'], pose['y'], pose['z']))
            placement.rotation_euler.z = pose['heading'] - forward_yaw
            meshes = [obj for obj in objects if obj.type == 'MESH' and not helper(obj)]
            arms = [obj for obj in objects if obj.type == 'ARMATURE']
            source_bones = sorted(len(skin['joints']) for skin in doc.get('skins', []))
            imported_bones = sorted(len(arm.data.bones) for arm in arms)
            if source_bones != imported_bones:
                raise RuntimeError('Original skin joint/bone count differs: ' + h['assetId'])
            source_triangles = sum(doc['accessors'][primitive['indices']]['count']//3
                                   for node in doc['nodes'] if 'mesh' in node
                                   for primitive in doc['meshes'][node['mesh']]['primitives'])
            imported_triangles = sum(len(p.vertices)-2 for obj in meshes for p in obj.data.polygons)
            if source_triangles != imported_triangles:
                raise RuntimeError('Original triangle count differs: ' + h['assetId'])
            samples = []
            for frame in (1, 9, 17):
                scene.frame_set(frame)
                actual = evaluated_bounds(meshes)
                low_frame, high_frame = actual
                cx, cy, floor = h['blenderPosition']
                w, d = h['size']
                if (low_frame.x <= cx-w/2+.15 or high_frame.x >= cx+w/2-.15
                        or low_frame.y <= cy-d/2+.15 or high_frame.y >= cy+d/2-.15):
                    raise RuntimeError('Evaluated body crossed the habitat boundary: ' + h['id'])
                if low_frame.z < floor-.08:
                    raise RuntimeError('Animal is below its habitat floor: ' + h['id'])
                if h['kind'] == 'aquarium':
                    if high_frame.z >= floor+h['waterSurfaceY'] or low_frame.z <= floor+.4:
                        raise RuntimeError('Shark left its water volume.')
                    if max(high_frame.x-low_frame.x, high_frame.y-low_frame.y) > h['maxLengthMeters']:
                        raise RuntimeError('Shark exceeds the8m maximum.')
                samples.append({'frame': frame, 'boundsBlender': bounds_json(actual), 'insideHabitat': True})
            scene.frame_set(1)
            # The library mirrors the runtime's initial route position. Keep
            # all original actions, but prevent a walk with root drift from
            # wandering out of its authoring enclosure on timeline playback.
            frozen = freeze_pose(objects, h['clip'], 0)
            if evaluated_bounds(meshes)[0].z < h['position'][1]-.08:
                raise RuntimeError('The constant native t=0 pose is below its floor.')
            box(structures, h['pad']['id'], h['pad']['blenderCenter'], h['pad']['blenderSize'], path_mat if h['kind']=='aquarium' else grass, walkable=True)
            H = h['fenceHeight']
            for wall in h['walls']:
                box(structures, wall['id'], wall['blenderCenter'], wall['blenderSize'], tank_glass if h['kind']=='aquarium' else land_glass)
                at = list(wall['blenderCenter']); at[2] = h['position'][1]+H
                dims = list(wall['blenderSize']); dims[2] = .12
                box(structures, wall['id']+'_TOP_RAIL', at, dims, rail_mat)
                if h['kind'] != 'aquarium':
                    at[2] = h['position'][1]+H*.45; dims[2] = .08
                    box(structures, wall['id']+'_MID_RAIL', at, dims, rail_mat)
            cx, cy, floor = h['blenderPosition']; w, d = h['size']
            for xsign in (-1, 1):
                for ysign in (-1, 1):
                    box(structures, h['id']+f'_POST_{xsign}_{ysign}', (cx+xsign*w/2,cy+ysign*d/2,floor+H/2), (.2,.2,H), rail_mat)
            if h.get('waterSurface'):
                part = h['waterSurface']
                box(structures, part['id'], part['blenderCenter'], part['blenderSize'], water)
            sign_y = cy-d/2-.25
            box(structures, h['id']+'_SIGN_POST', (cx,sign_y,floor+.75), (.1,.1,1.5), rail_mat)
            box(structures, h['id']+'_SIGN_PANEL', (cx,sign_y,floor+1.55), (3,.12,.65), rail_mat)
            label(structures, h['id']+'_LABEL', h['label'].replace(' · ', '\n')+'\nObservação pelo lado externo',
                  (cx,sign_y-.075,floor+1.55), label_mat)
            textures = {node.image for obj in meshes for mat in obj.data.materials if mat and mat.use_nodes
                        for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
            if not textures or any(min(image.size) <= 0 for image in textures):
                raise RuntimeError('Original image textures missing: ' + h['assetId'])
            if not all(len(obj.data.uv_layers) for obj in meshes):
                raise RuntimeError('Original UV layers missing: ' + h['assetId'])
            report['assets'].append({'assetId': h['assetId'], 'habitat': h['id'], 'source': str(source),
                'sha256': digest(source), 'sourcePreserved': True, 'originalBones': imported_bones,
                'originalTriangles': imported_triangles, 'meshes': len(meshes), 'images': len(textures),
                'originalUVsRetained': True, 'sourcePoseBoundsBlender': bounds_json(before_bounds),
                'uniformRootScale': factor, 'placementBlender': list(placement.location), 'headingRadians': placement.rotation_euler.z,
                'clip': clip, 'poseSamples': samples, 'libraryFrozenPose': frozen, 'normalizationOnlyOnOuterEmpty': True,
                'rootDriftCompensatedInBlender': False, 'runtimeCompensationCpuValidated': True,
                'browserVisualQA': False})
            (ROOT/'reports'/f'city_living_import_{h["id"]}_20261020.log').write_text(import_log,encoding='utf-8')
        scene.frame_set(1)
        studio(scene, camera_collection)
        for image in set(bpy.data.images)-previous_images:
            if image.type == 'IMAGE' and image.users and min(image.size) > 0 and not image.packed_file:
                image.pack()
        if state_hash(object_state(prior)) != previous_state:
            raise RuntimeError('An object from an older scene changed; do not save the master.')
        if (MASTER.stat().st_size, MASTER.stat().st_mtime_ns) != master_stat or Path(bpy.data.filepath).resolve() != MASTER.resolve():
            raise RuntimeError('Oct16 master path or disk file changed unexpectedly.')
        bpy.data.libraries.write(str(OUTPUT), {scene}, path_remap='RELATIVE', fake_user=False, compress=True)
        with bpy.data.libraries.load(str(OUTPUT), link=False) as (data_from, data_to):
            saved_scenes = list(data_from.scenes)
        if saved_scenes != [SCENE_NAME]:
            raise RuntimeError('Standalone library unexpectedly includes another scene: ' + str(saved_scenes))
        report.update({'status': 'assembled-and-saved', 'previousObjectChannelsMatch': True,
                       'previousObjectCount': len(prior), 'sceneObjectCount': len(scene.objects),
                       'standalone': {'path': str(OUTPUT), 'bytes': OUTPUT.stat().st_size, 'sha256': digest(OUTPUT),
                                      'scenes': saved_scenes, 'onlyNewSceneDependencyClosure': True},
                       'preview': {'path': str(PREVIEW), 'engine': 'CYCLES', 'device': 'CPU', 'samples': 24,
                                   'resolution': [1280, 960], 'configured': True},
                       'blenderVisualQA': False, 'masterDiskUnchanged': True})
        if RENDER:
            bpy.ops.render.render(write_still=True)
            if not PREVIEW.is_file():
                raise RuntimeError('Overview render did not write its PNG.')
            report['rendered'] = True
            report['preview'].update({'bytes': PREVIEW.stat().st_size, 'sha256': digest(PREVIEW)})
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PREP_CITY_LIVING_RESULT '+json.dumps({
            'scene': SCENE_NAME, 'assets': len(report['assets']), 'standalone': str(OUTPUT),
            'bytes': OUTPUT.stat().st_size, 'rendered': report['rendered'], 'masterSaved': False,
            'report': str(REPORT_PATH)}, ensure_ascii=False))
    except Exception as error:
        report.update({'status': 'partial-inspect-before-rerun', 'error': str(error), 'masterSavedByThisScript': False})
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        raise


main()
