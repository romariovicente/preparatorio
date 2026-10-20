"""Add all20 roster assets at their runtime city coordinates through live MCP.

This is an independent, editable authoring scene. It never edits source GLBs,
existing rigs/scenes, their bones, or animation keyframes. Legacy generated FK
tracks remain stored but muted. Three reviewed native poses are constant NLA
samples at t=0; the five artistic posture revisions remain explicitly pending.
The final compressed master save is left to the coordinating agent.

Optional exec-global PREP_CHARACTERS_RENDER=True renders the CPU16-sample
overview before writing the compressed scene library. Default: configure only.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0, str(ROOT / 'scripts'))
from prep_object_state_20261015 import object_state, state_hash
from prep_incremental_scene_tools_20261020 import (
    MASTER, PUBLIC, bounds_json, checkpoint_before, evaluated_bounds, freeze_pose,
    helper, import_fresh, pack_new_images, point, require_master, save_scene_library,
    sha256, source_name, visible, write_json,
)

SCENE_NAME = 'PREP_CHARACTERS_CITY_20261020'
OWNER = 'preparatorio-city-characters-20261020-v1'
PREFIX = 'CCH20_'
PLAN = ROOT / 'reports/CHARACTER_PLACEMENTS_20261020.json'
REVIEWS = ROOT / 'frontend/src/config/characterMotionReviews.json'
OUTPUT = ROOT / 'art/blender/PREPARATORIO_CHARACTERS_CITY_20261020.blend'
REPORT = ROOT / 'reports/CHARACTERS_CITY_BLENDER_20261020.json'
PREVIEW = ROOT / 'reports/characters_city_overview_20261020.png'
CITY_SCENE = '00_ARAPIRACA_CYBER_20261005'
RENDER = bool(globals().get('PREP_CHARACTERS_RENDER', False))
PENDING_POSES = {'SUP_dark_necromancer___corrupted_staff__', 'SUP_japanese_school_girl_v25',
                 'SUP_woman_seated_v15', 'SUP_woman_standing_v38__eko', 'SUP_woman_standing_v33'}


def collection(scene, name):
    target = bpy.data.collections.new(PREFIX + name)
    scene.collection.children.link(target)
    return target


def empty(target, name, parent=None):
    obj = bpy.data.objects.new(PREFIX + name, None)
    target.objects.link(obj)
    obj.parent = parent
    obj['owner'] = OWNER
    return obj


def make_material(name, color, roughness=.7):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = next(node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat


def make_label(target, name, text, at, heading, mat):
    curve = bpy.data.curves.new(PREFIX + name, 'FONT')
    curve.body = text
    curve.size = .13
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.space_line = 1.1
    curve.extrude = .001
    curve.materials.append(mat)
    obj = bpy.data.objects.new(PREFIX + name, curve)
    target.objects.link(obj)
    obj.location = at
    obj.rotation_euler = (math.pi/2, 0, heading)
    obj['owner'] = OWNER
    return obj


def ground_cache():
    """Read only the real260m city ground, never the inactive4km macro."""
    city = bpy.data.scenes.get(CITY_SCENE)
    if city is None:
        raise RuntimeError('The original playable city scene is missing.')
    bpy.context.window.scene = city
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    candidates = [obj for obj in city.objects if obj.type == 'MESH' and visible(obj)
                  and (obj.get('walkable') or obj.name.startswith('ENV_ARAP_Base')
                       or obj.name.startswith('ENV_ARAP_UrbanPlate')
                       or obj.name.startswith('ROAD_') and not re.search(r'white|Centre|MARK', obj.name, re.I))]
    vertices, triangles, used = [], [], []
    for obj in candidates:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            world_vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
            if not all(math.isfinite(value) for vertex in world_vertices for value in vertex):
                raise RuntimeError('The authored city ground contains nonfinite geometry.')
            base = len(vertices)
            vertices.extend(world_vertices)
            accepted = 0
            for tri in mesh.loop_triangles:
                a, b, c = (world_vertices[index] for index in tri.vertices)
                normal = (b-a).cross(c-a)
                if normal.length and normal.normalized().z >= .55:
                    triangles.append(tuple(base + index for index in tri.vertices))
                    accepted += 1
            if accepted:
                used.append(obj)
        finally:
            evaluated.to_mesh_clear()
    if not triangles:
        raise RuntimeError('No upward-facing playable-city floor was found.')
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True), used


def sample_floor(tree, position):
    x, baseline, z = position
    heights = []
    offsets = [(0, 0)] + [(math.cos(i*math.pi/4)*.32, math.sin(i*math.pi/4)*.32) for i in range(8)]
    for dx, dz in offsets:
        origin = Vector((x+dx, -z-dz, baseline+.41))
        hit, normal, index, distance = tree.ray_cast(origin, Vector((0, 0, -1)), .82)
        if hit is not None and normal.z >= .55 and baseline-.4-1e-6 <= hit.z <= baseline+.4+1e-6:
            heights.append(hit.z)
    if not heights:
        raise RuntimeError('No authored floor beneath NPC: ' + str(position))
    return max(heights)


def mirror_ground(target, sources):
    copies = []
    for source in sources:
        obj = source.copy()
        obj.name = PREFIX + 'GROUND_' + source.name
        target.objects.link(obj)
        matrix = source.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = matrix
        obj.animation_data_clear()
        obj['owner'] = OWNER
        obj['authoring_ground_source'] = source.name
        obj['walkable'] = True
        copies.append(obj)
    return copies


def texture_inventory(meshes, doc):
    images = {node.image for obj in meshes for mat in obj.data.materials if mat and mat.use_nodes
              for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
    if doc.get('images') and (not images or any(min(image.size) <= 0 for image in images)):
        raise RuntimeError('An authored character texture is missing its embedded pixels.')
    if doc.get('images') and not all(len(obj.data.uv_layers) for obj in meshes):
        raise RuntimeError('An authored textured mesh lost its UV layers.')
    return [{'name': image.name, 'size': list(image.size), 'packed': bool(image.packed_file)}
            for image in sorted(images, key=lambda image: image.name)]


def studio(scene, target):
    center = Vector((0, 0, .8))
    data = bpy.data.cameras.new(PREFIX + 'CAMERA_OVERVIEW')
    camera = bpy.data.objects.new(data.name, data)
    target.objects.link(camera)
    camera.location = Vector((45, -70, 57))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.ortho_scale = 74
    data.clip_start, data.clip_end = .1, 350
    scene.camera = camera
    for name, location, energy, size, color in [
            ('KEY', (-10, -18, 45), 85000, 45, (1, .96, .9)),
            ('FILL', (35, 20, 30), 55000, 35, (.8, .9, 1)),
            ('RIM', (-35, 15, 30), 40000, 30, (.86, .96, 1))]:
        data = bpy.data.lights.new(PREFIX + name, 'AREA')
        obj = bpy.data.objects.new(data.name, data)
        target.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (center-obj.location).to_track_quat('-Z', 'Y').to_euler()
        data.energy, data.size, data.color = energy, size, color
        data.shape = 'DISK'
    world = bpy.data.worlds.new(PREFIX + 'WORLD')
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == 'BACKGROUND')
    background.inputs['Color'].default_value = (.13, .18, .22, 1)
    background.inputs['Strength'].default_value = .65
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(PREVIEW)
    scene.view_settings.view_transform = 'AgX'


def main():
    require_master()
    if bpy.data.scenes.get(SCENE_NAME) or OUTPUT.exists() or REPORT.exists():
        raise RuntimeError('This new scene/library/report already exists. Inspect it instead of duplicating an attempt.')
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    placements = plan['placements']
    reviews = {review['id']: review for review in json.loads(REVIEWS.read_text(encoding='utf-8'))}
    if (plan['status'] != 'passed' or not plan['allRepresented'] or len(placements) != 20
            or len({entry['id'] for entry in placements}) != 20 or plan['figureCount'] != 21):
        raise RuntimeError('Expected the audited20-asset/21-figure city placement plan.')
    preflight = []
    for entry in placements:
        path = (PUBLIC / entry['displayUrl'].lstrip('/')).resolve()
        if not path.is_relative_to(PUBLIC) or not path.is_file():
            raise RuntimeError('Expected an existing local display GLB: ' + entry['id'])
        current_hash = sha256(path)
        review = reviews.get(entry['id'])
        if entry.get('standingPose') and (not review or review['sha256'] != current_hash or not review.get('poseReviewed')):
            raise RuntimeError('Pose approval is not tied to the current source hash: ' + entry['id'])
        if entry['id'] in PENDING_POSES and '/assets/supplied/' not in entry['displayUrl']:
            raise RuntimeError('A pending authored pose must use the preserved original, not generated FK.')
        expected_point = list(point(entry['position']))
        if any(abs(a-b)>1e-6 for a, b in zip(expected_point, entry['blenderBasePoint'])):
            raise RuntimeError('Frontend-to-Blender coordinate mapping changed.')
        preflight.append((entry, path, current_hash))
    prior = list(bpy.data.objects)
    previous_state = state_hash(object_state(prior))
    previous_images = set(bpy.data.images)
    previous_scene = bpy.context.scene.name
    reusable = [Path(path) for path in globals().get('PREP_REUSE_CHECKPOINT_REPORTS', [])]
    reusable += [ROOT/'reports/CHARACTERS_CITY_CHECKPOINT_20261020.json',
                 ROOT/'reports/CITY_LIVING_CHECKPOINT_20261020.json',
                 ROOT/'reports/CONTINUATION_CHECKPOINT_20261020.json',
                 ROOT/'reports/CITY_ADDITIONS_CHECKPOINT_20261019.json']
    checkpoint = checkpoint_before('CHARACTERS_CITY', prior, reusable, allow_known_additions=True)
    disk_before = (MASTER.stat().st_size, MASTER.stat().st_mtime_ns)
    tree, floor_sources = ground_cache()
    floors = {entry['id']: sample_floor(tree, entry['position']) for entry in placements}
    scene = bpy.data.scenes.new(SCENE_NAME)
    scene['owner'] = OWNER
    scene['author'] = 'Romario Vicente Amaro'
    scene['purpose'] = 'All20 runtime roster assets at the same playable-city coordinates; no separate macro map.'
    scene['posture_scope'] = 'Native reviewed t=0 poses frozen. Five authored poses still require artistic reposing; no claim of a corrected rig.'
    scene['source_placement_report'] = str(PLAN)
    scene['source_plan_sha256'] = sha256(PLAN)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 1, 120
    bpy.context.window.scene = scene
    report = {'owner': OWNER, 'scene': SCENE_NAME, 'status': 'assembling',
              'createdAt': datetime.now(timezone.utc).isoformat(), 'author': scene['author'],
              'checkpoint': checkpoint, 'master': str(MASTER), 'masterSavedByThisScript': False,
              'previousScene': previous_scene, 'plan': str(PLAN), 'planSha256': sha256(PLAN),
              'sourceGLBsModified': False, 'publicGLBExported': False, 'assetCount': 20,
              'figuresDeclaredBySourcePlan': 21, 'assets': [], 'rendered': False,
              'artisticPostureRevisionsStillPending': sorted(PENDING_POSES),
              'blenderVisualQA': False, 'browserVisualQA': False,
              'realismOrAllCharacterLocomotionComplete': False}
    try:
        ground_target = collection(scene, 'PLAYABLE_CITY_GROUND_MIRROR')
        ground_copies = mirror_ground(ground_target, floor_sources)
        labels = collection(scene, 'LABELS')
        lettering = make_material('LETTERING', (.77, .93, 1))
        for index, (entry, path, expected_hash) in enumerate(preflight):
            target = collection(scene, f'ACTOR_{index+1:02d}')
            objects, doc, source_hash, import_log = import_fresh(scene, target, entry['id'], path, OWNER, expected_hash)
            native_pose = entry.get('standingPose')
            if entry['id'] == 'CHR_Remy_Mixamo_20261005' and native_pose is None:
                native_pose = {'clip': 'Idle', 'time': 0}
            frozen = freeze_pose(objects, native_pose['clip'] if native_pose else None,
                                 native_pose.get('time', 0) if native_pose else 0)
            source_bounds = evaluated_bounds(objects)
            lo, hi, count = source_bounds
            size = hi-lo
            if size.z <= .001 or not all(math.isfinite(value) and value >= 0 for value in size):
                raise RuntimeError('Invalid actual character geometry: ' + entry['id'])
            # Static source figures may be exported in centimetres. A huge
            # evaluated body is never accepted merely because its box scales.
            if size.z > 500 or max(size.x, size.y) > max(size.z*8, 50):
                raise RuntimeError('Reject anomalous evaluated geometry, not a stale1km bounding box: ' + entry['id'])
            factor = entry['height']/size.z
            placement = empty(target, f'ACTOR_{index+1:02d}_PLACEMENT')
            normalized = empty(target, f'ACTOR_{index+1:02d}_NORMALIZATION', placement)
            own = set(objects)
            for obj in objects:
                if obj.parent not in own:
                    obj.parent = normalized
            normalized.scale = (factor,)*3
            normalized.location = Vector((-(lo.x+hi.x)/2, -(lo.y+hi.y)/2, -lo.z))*factor
            position = list(entry['position'])
            floor = floors[entry['id']]
            position[1] = floor+.01
            placement.location = point(position)
            placement.rotation_euler.z = entry['heading']
            placement['actorId'] = entry['actorId']
            placement['display_name'] = entry['name']
            placement['runtime_position_three_xyz'] = entry['position']
            placement['floor_support_source_scene'] = CITY_SCENE
            placement['floor_top_z'] = floor
            placement['pose_review_status'] = 'artist-review-pending' if entry['id'] in PENDING_POSES else 'authored-pose-preserved'
            samples = []
            for frame in (1, 60, 120):
                scene.frame_set(frame)
                actual = evaluated_bounds(objects)
                bottom, top = actual[:2]
                foot_gap = bottom.z-floor
                if abs(foot_gap-.01) > .004 or abs((top.z-bottom.z)-entry['height']) > .006:
                    raise RuntimeError('Frozen source posture/foot placement changed: ' + entry['id'])
                if max(top.x-bottom.x, top.y-bottom.y) > 14:
                    raise RuntimeError('The normalized character has an implausibly large body span.')
                samples.append({'frame': frame, 'boundsBlender': bounds_json(actual), 'footGapMeters': foot_gap})
            scene.frame_set(1)
            meshes = [obj for obj in objects if obj.type == 'MESH' and not helper(obj)]
            arms = [obj for obj in objects if obj.type == 'ARMATURE']
            source_bones = sorted(len(skin['joints']) for skin in doc.get('skins', []))
            imported_bones = sorted(len(arm.data.bones) for arm in arms)
            if source_bones != imported_bones:
                raise RuntimeError('Original skin/bone count changed: ' + entry['id'])
            texture_info = texture_inventory(meshes, doc)
            if sha256(path) != source_hash:
                raise RuntimeError('Source GLB changed during the additive import.')
            label_at = placement.location + Vector((0, 0, entry['height']+.3))
            label_text = entry['name']+'\n'+('Pose original · revisão pendente' if entry['id'] in PENDING_POSES else 'PREPARATÓRIO')
            make_label(labels, f'ACTOR_{index+1:02d}_LABEL', label_text, label_at, entry['heading'], lettering)
            report['assets'].append({'id': entry['id'], 'actorId': entry['actorId'], 'source': str(path),
                'sha256': source_hash, 'sourcePreserved': True, 'figuresDeclared': entry['figures'],
                'positionThree': entry['position'], 'positionBlender': list(placement.location),
                'headingRadians': entry['heading'], 'floorSupportTop': floor, 'floorProbeRadius': .32,
                'sourcePoseBoundsBlender': bounds_json(source_bounds), 'uniformWrapperScale': factor,
                'normalizationOnlyOnOuterEmpty': True, 'meshCount': len(meshes), 'originalSkinJointCounts': source_bones,
                'importedArmatureBoneCounts': imported_bones, 'nativeActionsRetained': [a.get('name') for a in doc.get('animations', [])],
                'frozenPose': frozen, 'textures': texture_info, 'poseSamples': samples,
                'artisticReposeCompleted': False, 'authoredPostureReviewPending': entry['id'] in PENDING_POSES,
                'generatedFkExecuted': False, 'nativeRigModified': False})
            (ROOT/f'reports/character_city_import_{index+1:02d}_20261020.log').write_text(import_log, encoding='utf-8')
            # Persist progress so a timeout leaves an inspectable partial stage.
            write_json(REPORT, report)
        scene.frame_set(1)
        studio(scene, collection(scene, 'OVERVIEW'))
        report['packedNewImages'] = pack_new_images(previous_images)
        if state_hash(object_state(prior)) != previous_state:
            raise RuntimeError('An older scene object changed; do not save the master.')
        require_master()
        if (MASTER.stat().st_size, MASTER.stat().st_mtime_ns) != disk_before:
            raise RuntimeError('The master disk file changed during assembly; inspect the autosave state.')
        if RENDER:
            bpy.ops.render.render(write_still=True)
            if not PREVIEW.is_file():
                raise RuntimeError('The configured overview render was not written.')
            report['rendered'] = True
        report['standalone'] = save_scene_library(scene, OUTPUT)
        report.update({'status': 'assembled-and-saved', 'instantiatedAssets': len(report['assets']),
                       'sceneObjectCount': len(scene.objects), 'previousObjectCount': len(prior),
                       'previousObjectChannelsMatch': True, 'masterDiskUnchanged': True,
                       'mirroredGroundObjectCount': len(ground_copies), 'mirroredGroundSourceScene': CITY_SCENE,
                       'preview': {'path': str(PREVIEW), 'engine': 'CYCLES', 'device': 'CPU', 'samples': 16,
                                   'resolution': [1440, 1080], 'configured': True}})
        if RENDER:
            report['preview'].update({'bytes': PREVIEW.stat().st_size, 'sha256': sha256(PREVIEW)})
        write_json(REPORT, report)
        print('PREP_CHARACTERS_CITY_RESULT '+json.dumps({'scene': SCENE_NAME,
              'assets': len(report['assets']), 'library': str(OUTPUT), 'report': str(REPORT),
              'rendered': RENDER, 'masterSaved': False}, ensure_ascii=False))
    except Exception as error:
        report.update({'status': 'partial-inspect-before-rerun', 'error': str(error)})
        write_json(REPORT, report)
        raise


main()
