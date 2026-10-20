"""Shared safeguards for additive, live-MCP Blender authoring on 20 October.

Importing this module never executes Blender operators. Callers retain all old
objects/scenes, import fresh GLBs, save a compressed scene library, and leave
the final master save to the coordinating agent.
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
import bpy
from mathutils import Vector
from prep_object_state_20261015 import object_state, state_hash

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER = ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend'
PUBLIC = (ROOT / 'frontend/public').resolve()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def require_master():
    if Path(bpy.data.filepath).resolve() != MASTER.resolve() or not MASTER.is_file():
        raise RuntimeError('Open the existing Oct16 master in the live MCP session; preserve another open file.')


def checkpoint_before(label, prior, reused_reports=(), allow_known_additions=False):
    """Reuse only a byte-verified checkpoint with the exact complete snapshot.

    The comparison traverses the current object list once, never looks up all
    16k old names repeatedly. A changed scene/object set requires a new copy.
    """
    require_master()
    state = object_state(prior)
    current_hash = state_hash(state)
    scene_names = sorted(scene.name for scene in bpy.data.scenes)
    for path in reused_reports:
        path = Path(path)
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
            saved = Path(report['checkpoint'])
            snapshot = Path(report['stateSnapshot'])
            old_state = json.loads(snapshot.read_text(encoding='utf-8'))
            checkpoint_bytes = report.get('bytes', report.get('checkpointBytes'))
            exact = (report.get('objects') == len(prior) and report.get('scenes') == len(scene_names)
                     and report.get('stateHash') == current_hash and old_state == state
                     and (not report.get('sceneNames') or report['sceneNames'] == scene_names))
            # Root authorized reuse after its saved AMG studio: only known
            # additive scenes/objects may be newer than the baseline. Every
            # baseline object must still exist and match all saved channels.
            extra_names = set(state)-set(old_state)
            allowed_owners = {'preparatorio-city-living-20261020-v2', 'preparatorio-city-characters-20261020-v1'}
            new_objects = [obj for obj in prior if obj.name in extra_names]
            subset = (allow_known_additions and len(old_state) == report.get('objects')
                      and len(state) >= len(old_state)
                      and all(state.get(name) == channels for name, channels in old_state.items())
                      and all(obj.name.startswith('AMGST20_') or obj.get('owner') in allowed_owners for obj in new_objects)
                      and 0 <= len(scene_names)-report.get('scenes', len(scene_names)) <= 3)
            if (saved.is_file() and saved.stat().st_size == checkpoint_bytes
                    and state_hash(old_state) == report.get('stateHash') and (exact or subset)):
                return {'report': str(path), 'checkpoint': str(saved), 'reused': True,
                        'exactObjectSnapshotMatch': exact, 'checkpointObjectSubsetMatches': bool(subset),
                        'checkpointObjectCount': len(old_state), 'additiveObjectCountAfterCheckpoint': len(extra_names),
                        'additiveObjectNames': sorted(extra_names), 'stateHash': current_hash,
                        'compressedCopyRequested': report.get('compressedCopyRequested', report.get('checkpointLibraryReadValidated', False))}
        except (OSError, KeyError, ValueError, TypeError):
            continue
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    target = ROOT / f'art/blender/checkpoints/BEFORE_{label}_{stamp}.blend'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError('Never replace an existing checkpoint.')
    dirty_before = bpy.data.is_dirty
    result = bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, compress=True, check_existing=True)
    require_master()
    if 'FINISHED' not in result or not target.is_file():
        raise RuntimeError('The compressed checkpoint was not saved.')
    if state_hash(object_state(prior)) != current_hash:
        raise RuntimeError('Original object channels changed during the checkpoint.')
    snapshot = target.with_suffix('.objects.json')
    snapshot.write_text(json.dumps(state, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    report_path = ROOT / f'reports/{label}_CHECKPOINT_20261020.json'
    # A repeated attempt never overwrites another checkpoint report.
    if report_path.exists():
        report_path = report_path.with_name(report_path.stem + '_' + stamp + '.json')
    report = {'source': str(MASTER), 'checkpoint': str(target), 'bytes': target.stat().st_size,
              'stateSnapshot': str(snapshot), 'stateHash': current_hash, 'objects': len(prior),
              'scenes': len(scene_names), 'sceneNames': scene_names, 'activeScene': bpy.context.scene.name,
              'compressedCopyRequested': True, 'dirtyBeforeCheckpoint': dirty_before,
              'timeUTC': datetime.now(timezone.utc).isoformat()}
    write_json(report_path, report)
    return {'report': str(report_path), 'checkpoint': str(target), 'reused': False,
            'exactObjectSnapshotMatch': True, 'stateHash': current_hash, 'compressedCopyRequested': True}


def glb_document(path):
    with Path(path).open('rb') as handle:
        header = handle.read(20)
        if len(header) != 20 or header[:4] != b'glTF' or struct.unpack_from('<I', header, 4)[0] != 2:
            raise RuntimeError('Expected audited GLB2: ' + str(path))
        length, kind = struct.unpack_from('<II', header, 12)
        if kind != 0x4E4F534A:
            raise RuntimeError('First GLB chunk must be JSON.')
        doc = json.loads(handle.read(length))
    if any(record.get('uri') and not record['uri'].startswith('data:') for record in doc.get('buffers', [])):
        raise RuntimeError('External geometry buffers are not accepted.')
    if any(record.get('uri') and not record['uri'].startswith('data:') for record in doc.get('images', [])):
        raise RuntimeError('External image files are not accepted.')
    return doc


def canonical(name):
    return re.sub(r'(?:\.\d+)+$', '', str(name))


def source_name(obj):
    return obj.get('asset_node_name', obj.get('prep_source_node_name', obj.name))


def helper(obj):
    normalized = re.sub(r'[^a-z0-9]', '', canonical(source_name(obj)).lower())
    skinned = obj.type == 'MESH' and any(mod.type == 'ARMATURE' for mod in obj.modifiers)
    return (any(c.name.startswith('glTF_not_exported') for c in obj.users_collection)
            or (not skinned and bool(re.fullmatch(r'(?:icosphere|esferaicosaedrica)(?:\d+)?(?:mesh)?', normalized))))


def visible(obj):
    while obj:
        if obj.hide_render:
            return False
        obj = obj.parent
    return True


def evaluated_bounds(objects):
    """Referenced, evaluated vertices: never trust stale skinned mesh bounds."""
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    count = 0
    for obj in objects:
        if obj.type != 'MESH' or not visible(obj) or helper(obj):
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            used = {index for polygon in mesh.polygons for index in polygon.vertices}
            for index in used:
                point = evaluated.matrix_world @ mesh.vertices[index].co
                if not all(math.isfinite(value) for value in point):
                    raise RuntimeError('Nonfinite evaluated vertex: ' + obj.name)
                for axis in range(3):
                    low[axis] = min(low[axis], point[axis])
                    high[axis] = max(high[axis], point[axis])
                count += 1
        finally:
            evaluated.to_mesh_clear()
    if not count:
        raise RuntimeError('No visible, referenced evaluated vertices.')
    return low, high, count


def bounds_json(bounds):
    lo, hi = bounds[:2]
    return {'min': list(lo), 'max': list(hi), 'size': list(hi - lo),
            'evaluatedReferencedVertices': bounds[2] if len(bounds) > 2 else None, 'nonfinite': 0}


def point(frontend):
    return Vector((frontend[0], -frontend[2], frontend[1]))


def import_fresh(scene, target, asset_id, path, owner, expected_sha=None):
    path = Path(path).resolve()
    if not path.is_relative_to(PUBLIC) or path.suffix.lower() != '.glb' or not path.is_file():
        raise RuntimeError('Source must be an existing GLB inside frontend/public.')
    source_hash = sha256(path)
    if expected_sha and source_hash != expected_sha:
        raise RuntimeError('Audited source hash changed: ' + asset_id)
    doc = glb_document(path)
    before = set(scene.objects)
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        result = bpy.ops.import_scene.gltf(filepath=str(path))
    fresh = [obj for obj in scene.objects if obj not in before]
    if 'FINISHED' not in result or not fresh:
        raise RuntimeError('GLB import failed: ' + asset_id)
    node_names = [node.get('name') for node in doc.get('nodes', []) if node.get('name')]
    for obj in fresh:
        # Do not rename imported objects: native animation channel paths remain
        # intact. Preserve the authored label separately from Blender suffixes.
        original = source_name(obj)
        if original not in node_names:
            matches = [name for name in node_names if obj.name == name or obj.name.startswith(name + '.')]
            original = max(matches, key=len) if matches else original
        obj['asset_node_name'] = original
        obj['prep_source_node_name'] = original
        obj['prep_asset_id'] = asset_id
        obj['source_sha256'] = source_hash
        obj['owner'] = owner
        if helper(obj):
            obj.hide_render = True
            obj.hide_set(True)
        target.objects.link(obj) if target not in obj.users_collection else None
        for old in list(obj.users_collection):
            if old != target:
                old.objects.unlink(obj)
    return fresh, doc, source_hash, capture.getvalue()


def freeze_pose(objects, clip_name=None, seconds=0):
    """Mute prototype FK and keep selected native NLA at a constant sample.

    Actions and strips are retained. No keyframe or pose bone is edited. The
    animated-time property has a constant value and no generated fcurve.
    """
    selected, inventory = [], []
    for obj in objects:
        ad = obj.animation_data
        if not ad:
            continue
        active = ad.action
        tracks = list(ad.nla_tracks)
        if clip_name and active and canonical(active.name) == canonical(clip_name) and not tracks:
            ad.action = None
            track = ad.nla_tracks.new()
            track.name = clip_name
            track.strips.new(clip_name, 1, active)
            tracks = list(ad.nla_tracks)
        else:
            ad.action = None
        for track in tracks:
            track.is_solo = False
            matches = [strip for strip in track.strips if clip_name and
                       (canonical(track.name) == canonical(clip_name)
                        or strip.action and canonical(strip.action.name) == canonical(clip_name))]
            track.mute = not bool(matches)
            for strip in track.strips:
                if strip not in matches:
                    continue
                original_range = [strip.frame_start, strip.frame_end]
                strip.use_animated_time = True
                start = strip.action.frame_range[0]
                strip.strip_time = start + seconds * bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
                strip.extrapolation = 'HOLD'
                strip.frame_start = bpy.context.scene.frame_start
                strip.frame_end = max(strip.frame_start+1, bpy.context.scene.frame_end)
                selected.append({'object': obj.name, 'track': track.name, 'strip': strip.name,
                                 'action': strip.action.name, 'constantActionFrame': strip.strip_time,
                                 'originalStripRange': original_range,
                                 'constantSampleRange': [strip.frame_start, strip.frame_end]})
            inventory.append({'object': obj.name, 'track': track.name, 'muted': track.mute,
                              'strips': [{'name': strip.name, 'action': strip.action.name if strip.action else None}
                                         for strip in track.strips]})
    if clip_name and not selected:
        raise RuntimeError('Reviewed native pose clip was not found: ' + clip_name)
    bpy.context.scene.frame_set(1)
    return {'clip': clip_name, 'timeSeconds': seconds, 'selected': selected,
            'nativeNlaFrozenAtSample': bool(clip_name), 'prototypeFkMuted': clip_name is None,
            'tracksRetained': inventory, 'poseBonesOrKeyframesEdited': False}


def pack_new_images(previous_images):
    packed = []
    for image in set(bpy.data.images) - previous_images:
        if image.type == 'IMAGE' and image.users:
            if min(image.size) <= 0:
                raise RuntimeError('Imported image has no pixel buffer: ' + image.name)
            if not image.packed_file:
                image.pack()
            packed.append(image.name)
    return packed


def save_scene_library(scene, output):
    output = Path(output)
    if output.exists():
        raise RuntimeError('Never replace an existing incremental scene library.')
    bpy.data.libraries.write(str(output), {scene}, path_remap='RELATIVE', fake_user=False, compress=True)
    with bpy.data.libraries.load(str(output), link=False) as (source, target):
        names = list(source.scenes)
    if names != [scene.name]:
        raise RuntimeError('Scene library contains unexpected scene dependencies: ' + str(names))
    return {'path': str(output), 'bytes': output.stat().st_size, 'sha256': sha256(output),
            'scenes': names, 'compressedCopyRequested': True, 'onlyNewSceneDependencyClosure': True}
