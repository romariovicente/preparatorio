"""Integrate four genuine Mixamo library-character FBXs inside Blender 5.2.

Execute with __file__ set to this file, after the city builder has finished.
No download, account operation, source rewrite, transform_apply or registry edit
occurs here. Missing downloads fail before scene changes. Failed attempts remain
inspectable and require a new suffix or explicit review before another attempt.

Optional globals: PREP_MIXAMO_SUFFIX (default 20261005),
PREP_MIXAMO_DOWNLOADS (absolute directory), PREP_MIXAMO_SAVE_BLEND (default True),
PREP_MIXAMO_CHARACTER (default Remy), PREP_MIXAMO_STAGE_NPC (default True),
PREP_MIXAMO_RENDER (default True), PREP_MIXAMO_CHECKPOINT (default True),
PREP_MIXAMO_WRITE_METADATA (default True), PREP_MIXAMO_REDUCE_WEIGHTS (default True).

Idle.fbx must be WithSkin; Walk/Dance/Interact.fbx must come from this SAME
character. Names are delivery names: the report records the actual action names.
No claim is made about successful autorig of the user's supplied Jumpsuit.
The standalone blend and optional checkpoint write scene dependencies only.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import struct
import traceback
from datetime import datetime, timezone

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = str(globals().get('PREP_MIXAMO_SUFFIX', '20261005'))
if not re.fullmatch(r'[A-Za-z0-9_-]+', SUFFIX):
    raise ValueError('Unsafe delivery suffix')
DOWNLOADS = Path(globals().get('PREP_MIXAMO_DOWNLOADS', ROOT / ('art/mixamo_downloads_' + SUFFIX))).resolve()
CHARACTER = str(globals().get('PREP_MIXAMO_CHARACTER', 'Remy'))
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', CHARACTER):
    raise ValueError('Unsafe library character name')
CLIPS = ('Idle', 'Walk', 'Dance', 'Interact')
ASSET_ID = 'CHR_' + CHARACTER + '_Mixamo_' + SUFFIX
SCENE_NAME = 'MIXAMO_' + CHARACTER.upper() + '_' + SUFFIX
DEST = ROOT / 'frontend/public/assets/characters' / (ASSET_ID + '.glb')
REPORT_DIR = ROOT / 'reports/prep_mixamo_validation'
REPORT_PATH = REPORT_DIR / (CHARACTER.lower() + '_' + SUFFIX + '.json')
STAGING = ROOT / 'art' / ('mixamo_derived_' + SUFFIX) / (ASSET_ID + '_pending.glb')
BLEND = ROOT / 'art/blender' / ('PREPARATORIO_MIXAMO_' + CHARACTER.upper() + '_' + SUFFIX + '.blend')
METADATA = ROOT / 'frontend/src/config/mixamoAssets.json'
ARAPIRACA_NAME = '00_ARAPIRACA_CYBER_20261005'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_glb(path):
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or length != len(raw):
        raise ValueError('Invalid or incomplete GLB')
    doc, binary, offset = None, None, 12
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset)
        chunk = raw[offset + 8:offset + 8 + size]
        if kind == 0x4E4F534A:
            doc = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        offset += size + 8
    if doc is None or binary is None or offset != len(raw):
        raise ValueError('GLB requires embedded JSON and binary chunks')
    return doc, binary


def accessor_array(doc, binary, index):
    acc = doc['accessors'][index]
    dtypes = {5120: '<i1', 5121: '<u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
    widths = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    dtype, width = np.dtype(dtypes[acc['componentType']]), widths[acc['type']]
    if acc.get('sparse'):
        raise ValueError('Unexpected sparse accessor in generated Mixamo GLB')
    view = doc['bufferViews'][acc['bufferView']]
    if view.get('buffer', 0) != 0:
        raise ValueError('External buffer in generated GLB')
    offset = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = view.get('byteStride', width * dtype.itemsize)
    result = np.ndarray((acc['count'], width), dtype=dtype, buffer=binary,
                        offset=offset, strides=(stride, dtype.itemsize)).copy()
    if acc.get('normalized') and acc['componentType'] != 5126:
        result = np.maximum(result.astype(float) / np.iinfo(dtype).max, -1)
    return result


def fcurves(action, slot=None):
    """Blender 5 layered actions; legacy fallback only when actually available."""
    for layer in getattr(action, 'layers', ()):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', ()):
                if slot is None or bag.slot_handle == slot.handle:
                    yield from bag.fcurves
    if not getattr(action, 'layers', None):
        yield from getattr(action, 'fcurves', ())


def compatible_slot(action, preferred=None):
    slots = list(getattr(action, 'slots', ()))
    if preferred:
        match = next((s for s in slots if s.identifier == preferred.identifier), None)
        if match:
            return match
    for slot in slots:
        if getattr(slot, 'target_id_type', 'OBJECT') == 'OBJECT' and any(fcurves(action, slot)):
            return slot
    return slots[0] if slots else None


def bind_action(arm, action, slot=None):
    arm.animation_data_create()
    arm.animation_data.action = action
    chosen = compatible_slot(action, slot)
    if chosen is not None and hasattr(arm.animation_data, 'action_slot'):
        arm.animation_data.action_slot = chosen
    return chosen


def imported_action(arm):
    ad = arm.animation_data
    if ad and ad.action:
        return ad.action, getattr(ad, 'action_slot', None)
    if ad:
        strips = [s for t in ad.nla_tracks for s in t.strips if s.action]
        if len(strips) == 1:
            return strips[0].action, getattr(strips[0], 'action_slot', None)
    raise ValueError('Expected one imported FBX skeletal action on ' + arm.name)


def import_fbx(path, scene, report):
    bpy.context.window.scene = scene
    # The same importer and bone orientation options are used for all four FBXs.
    # RNA filtering adapts to the native importer when the older operator is absent.
    candidates = [('import_scene.fbx', bpy.ops.import_scene.fbx), ('wm.fbx_import', bpy.ops.wm.fbx_import)]
    operator, name, rna = None, None, None
    for candidate_name, candidate in candidates:
        try:
            candidate_rna = candidate.get_rna_type()
        except (RuntimeError, AttributeError):
            continue
        operator, name, rna = candidate, candidate_name, candidate_rna
        break
    if operator is None:
        raise RuntimeError('No available Blender FBX importer')
    wanted = dict(filepath=str(path), use_anim=True, use_animation=True,
                  import_animation=True, use_image_search=True, global_scale=1.0,
                  bake_space_transform=False, ignore_leaf_bones=True,
                  automatic_bone_orientation=False, use_prepost_rot=True, anim_offset=1.0)
    accepted = {k: v for k, v in wanted.items() if k in rna.properties}
    before = set(bpy.data.objects)
    result = operator(**accepted)
    if 'FINISHED' not in result:
        raise RuntimeError('FBX import did not finish: ' + name)
    objects = [o for o in scene.objects if o not in before]
    arms = [o for o in objects if o.type == 'ARMATURE']
    if len(arms) != 1:
        raise ValueError(f'{path.name}: expected one armature, found {len(arms)}')
    report['imports'].append({'clip': path.stem, 'path': str(path), 'operator': name,
                             'options': accepted, 'objects': len(objects),
                             'bones': len(arms[0].data.bones),
                             'fps': scene.render.fps / scene.render.fps_base})
    return arms[0], objects


def canonical_bone(name):
    return re.sub(r'^mixamorig\d*[:_]?','', name, flags=re.IGNORECASE)


def bone_map(source_arm, target_arm):
    target = {}
    for b in target_arm.data.bones:
        key = canonical_bone(b.name)
        if key in target:
            raise ValueError('Ambiguous target bone namespace: ' + key)
        target[key] = b
    mapping, max_error = {}, 0.0
    for b in source_arm.data.bones:
        other = target.get(canonical_bone(b.name))
        if other is None:
            raise ValueError('Missing target bone: ' + b.name)
        if (canonical_bone(b.parent.name) if b.parent else None) != (canonical_bone(other.parent.name) if other.parent else None):
            raise ValueError('Incompatible bone hierarchy: ' + b.name)
        error = max(abs(b.matrix_local[i][j] - other.matrix_local[i][j]) for i in range(4) for j in range(4))
        max_error = max(max_error, error)
        mapping[b.name] = other.name
    if len(mapping) != len(target):
        raise ValueError(f'Incompatible bind/rest skeleton: bones {len(mapping)}/{len(target)}, matrix error {max_error}')
    return mapping, max_error


def make_clip(source_arm, target_arm, clip, target_fps, report):
    original, original_slot = imported_action(source_arm)
    mapping, rest_error = bone_map(source_arm, target_arm)
    if rest_error > .005:
        return bake_global_clip(source_arm, target_arm, clip, target_fps, mapping, rest_error, report)
    action = original.copy()
    action.name = 'MIXAMO_' + CHARACTER + '_' + clip + '_' + SUFFIX
    action.use_fake_user = True
    original.use_fake_user = True
    slot = compatible_slot(action, original_slot)
    curves = list(fcurves(action, slot))
    if not curves:
        raise ValueError('Empty skeletal action: ' + clip)
    bone_channels = 0
    for curve in curves:
        if curve.data_path.startswith('pose.bones['):
            match = re.match(r'pose\.bones\[("(?:[^"\\]|\\.)*")\]', curve.data_path)
            if not match:
                raise ValueError('Unsupported bone animation path: ' + curve.data_path)
            bone = json.loads(match.group(1))
            if bone not in mapping:
                raise ValueError('Unknown animated bone: ' + bone)
            curve.data_path = 'pose.bones[' + json.dumps(mapping[bone]) + ']' + curve.data_path[match.end():]
            bone_channels += 1
    if bone_channels == 0:
        raise ValueError('No real bone animation channels: ' + clip)
    start, end = map(float, original.frame_range)
    source_fps = source_arm.users_scene[0].render.fps / source_arm.users_scene[0].render.fps_base
    ratio = target_fps / source_fps
    for curve in curves:
        for key in curve.keyframe_points:
            key.co.x = 1 + (key.co.x - start) * ratio
            key.handle_left.x = 1 + (key.handle_left.x - start) * ratio
            key.handle_right.x = 1 + (key.handle_right.x - start) * ratio
        curve.update()
    frame_end = 1 + (end - start) * ratio
    if frame_end <= 1:
        raise ValueError('Animation duration is zero: ' + clip)
    target_arm.animation_data_create()
    target_arm.animation_data.action = None
    track = target_arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, action)
    if slot is not None and hasattr(strip, 'action_slot'):
        strip.action_slot = slot
    strip.action_frame_start = 1
    strip.action_frame_end = frame_end
    strip.frame_start = 1
    strip.frame_end = frame_end
    strip.extrapolation = 'NOTHING'
    strip.blend_type = 'REPLACE'
    track.mute = True
    report['actions'].append({'clip': clip, 'sourceAction': original.name,
                              'action': action.name, 'slot': getattr(slot, 'identifier', None),
                              'sourceFrameRange': [start, end], 'frameRange': [1, frame_end],
                              'boneChannels': bone_channels, 'matchedBones': len(mapping),
                              'maxBindMatrixDifference': rest_error, 'sourceFps': source_fps,
                              'targetFps': target_fps})
    return action, slot, track


def bake_global_clip(source_arm, target_arm, clip, target_fps, mapping, rest_error, report):
    """FBX WithoutSkin may use a posed rest skeleton; bake onto WithSkin bind.

    Local Euler channels cannot be copied between those rests. Preserve the
    evaluated world matrices instead and derive local basis on the target rig.
    """
    original, _ = imported_action(source_arm)
    original.use_fake_user = True
    source_scene, target_scene = source_arm.users_scene[0], target_arm.users_scene[0]
    source_fps = source_scene.render.fps / source_scene.render.fps_base
    start, end = map(float, original.frame_range)
    frame_end = 1 + (end-start) * target_fps / source_fps
    if frame_end <= 1:
        raise ValueError('Empty source motion')
    action = bpy.data.actions.new('MIXAMO_' + CHARACTER + '_' + clip + '_' + SUFFIX)
    action.use_fake_user = True
    bind_action(target_arm, action)
    for track in target_arm.animation_data.nla_tracks:
        track.mute = True
    target_scene.render.fps = round(target_fps)
    samples = []
    for frame in range(1, math.ceil(frame_end)+1):
        source_frame = min(end, start+(frame-1)*source_fps/target_fps)
        bpy.context.window.scene = source_scene
        source_scene.frame_set(int(source_frame), subframe=source_frame-int(source_frame))
        bpy.context.view_layer.update()
        desired_world = {mapping[bone.name]: source_arm.matrix_world @ bone.matrix.copy() for bone in source_arm.pose.bones}
        bpy.context.window.scene = target_scene
        target_scene.frame_set(frame)
        bpy.context.view_layer.update()
        inverse = target_arm.matrix_world.inverted()
        desired = {name: inverse @ matrix for name, matrix in desired_world.items()}
        for bone in target_arm.pose.bones:
            kwargs = {}
            if bone.parent:
                kwargs = {'parent_matrix': desired[bone.parent.name], 'parent_matrix_local': bone.parent.bone.matrix_local}
            bone.matrix_basis = bone.bone.convert_local_to_pose(desired[bone.name], bone.bone.matrix_local, invert=True, **kwargs)
            bone.rotation_mode = 'QUATERNION'
            for path in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(data_path=path, frame=frame, group=bone.name)
        bpy.context.view_layer.update()
        error = max(max(abs((target_arm.matrix_world @ bone.matrix)[i][j]-desired_world[bone.name][i][j]) for i in range(4) for j in range(4)) for bone in target_arm.pose.bones)
        samples.append(error)
    if max(samples) > .005:
        raise ValueError('World-matrix retarget does not reproduce original skeleton: '+str(max(samples)))
    slot = compatible_slot(action)
    for curve in fcurves(action, slot):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    target_arm.animation_data.action = None
    track = target_arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, action)
    if slot is not None and hasattr(strip, 'action_slot'):
        strip.action_slot = slot
    strip.action_frame_start, strip.action_frame_end = 1, frame_end
    strip.frame_start, strip.frame_end = 1, frame_end
    strip.extrapolation, strip.blend_type, track.mute = 'NOTHING', 'REPLACE', True
    report['actions'].append({'clip': clip, 'sourceAction': original.name, 'action': action.name,
        'sourceFrameRange': [start,end], 'frameRange': [1,frame_end], 'matchedBones': len(mapping),
        'maxBindMatrixDifference': rest_error, 'retargetMethod': 'Evaluated global matrices converted to target bind local basis',
        'bakedFrames': len(samples), 'maxWorldMatrixError': max(samples), 'sourceFps': source_fps, 'targetFps': target_fps})
    return action, slot, track


def skin_report(arm, meshes):
    bone_names = {b.name for b in arm.data.bones if b.use_deform}
    total, uncovered, maximum, maximum_sum_error = 0, 0, 0, 0.0
    for obj in meshes:
        groups = {g.index for g in obj.vertex_groups if g.name in bone_names}
        for v in obj.data.vertices:
            values = [g.weight for g in v.groups if g.group in groups and g.weight > 1e-8]
            if not all(math.isfinite(x) and x > 0 for x in values):
                raise ValueError('Nonfinite or negative skin weight')
            total += 1
            maximum = max(maximum, len(values))
            if not values:
                uncovered += 1
            maximum_sum_error = max(maximum_sum_error, abs(sum(values) - 1))
    if total == 0 or uncovered or maximum_sum_error > .003:
        raise ValueError(f'Invalid skin coverage: {uncovered}/{total} unweighted, sum error {maximum_sum_error}')
    return {'vertices': total, 'unweightedVertices': uncovered, 'weightCoverage': 1,
            'maxInfluences': maximum, 'maxWeightSumError': maximum_sum_error,
            'bones': len(arm.data.bones), 'deformingBones': len(bone_names)}


def skin_fingerprint(meshes):
    digest = hashlib.sha256()
    for obj in meshes:
        digest.update(obj.name.encode('utf-8'))
        for vertex in obj.data.vertices:
            digest.update(struct.pack('<I3f', vertex.index, *vertex.co))
            for group in sorted(vertex.groups, key=lambda row: row.group):
                digest.update(struct.pack('<If', group.group, group.weight))
    return digest.hexdigest()


def independent_working_copy(source_arm, source_objects, scene):
    """Leave the full eight-influence imported meshes/rig in their source scene."""
    copies = {obj: obj.copy() for obj in source_objects}
    for original, copy in copies.items():
        if original.data:
            copy.data = original.data.copy()
        scene.collection.objects.link(copy)
        if original.parent in copies:
            copy.parent = copies[original.parent]
        for modifier in copy.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object in copies:
                modifier.object = copies[modifier.object]
    return copies[source_arm], [copies[obj] for obj in source_objects]


def reduce_to_four(arm, meshes):
    """Derive runtime weights on independent copies, without silent truncation."""
    bone_names = {bone.name for bone in arm.data.bones if bone.use_deform}
    discarded, changed, total = [], 0, 0
    for obj in meshes:
        deform_groups = {group.index for group in obj.vertex_groups if group.name in bone_names}
        for vertex in obj.data.vertices:
            influences = sorted(((group.group, group.weight) for group in vertex.groups
                                 if group.group in deform_groups and group.weight > 1e-8),
                                key=lambda row: (-row[1], row[0]))
            retained = influences[:4]
            weight_sum = sum(weight for _, weight in retained)
            if weight_sum <= 0:
                raise ValueError('Cannot reduce an unweighted vertex')
            total += 1
            loss = sum(weight for _, weight in influences[4:])
            discarded.append(loss)
            if len(influences) > 4:
                changed += 1
            for index, _ in influences[4:]:
                obj.vertex_groups[index].remove([vertex.index])
            for index, weight in retained:
                obj.vertex_groups[index].add([vertex.index], weight / weight_sum, 'REPLACE')
    return {'method': 'Independent working mesh/rig copies; retain strongest four weights and renormalize',
            'vertices': total, 'verticesWithDiscardedWeights': changed,
            'maxDiscardedWeightSum': max(discarded),
            'meanDiscardedWeightSum': sum(discarded) / max(1, total),
            'originalImportedMeshesRetained': True,
            'maxAllowedSampleErrorMeters': .035, 'maxAllowedSampleP99ErrorMeters': .012}


def reduction_motion_report(source_scene, source_arm, source_meshes, scene, arm, meshes, clips, scale, translation):
    """Measure actual 8→4 skin deformation differences, not just weight sums."""
    rows = []
    saved = []
    for obj, obj_scene in ((source_arm, source_scene), (arm, scene)):
        data = obj.animation_data
        saved.append((obj, obj_scene, data.action, getattr(data, 'action_slot', None),
                      [(track, track.mute) for track in data.nla_tracks], obj_scene.frame_current))
        for track in data.nla_tracks:
            track.mute = True
    try:
        for clip in CLIPS:
            action, slot = clips[clip]
            bind_action(arm, action, slot)
            bind_action(source_arm, action, slot)
            start, end = map(float, action.frame_range)
            for fraction in (0, .17, .31, .5, .73, .91, 1):
                frame = start + (end - start) * fraction
                original = evaluated_points(source_scene, source_meshes, frame) * scale + np.array(translation)
                reduced = evaluated_points(scene, meshes, frame)
                if original.shape != reduced.shape:
                    raise ValueError('Reduced mesh topology diverges from original import')
                errors = np.linalg.norm(reduced - original, axis=1)
                row = {'clip': clip, 'frame': frame, 'maxErrorMeters': float(errors.max()),
                       'p99ErrorMeters': float(np.quantile(errors, .99)),
                       'meanErrorMeters': float(errors.mean())}
                rows.append(row)
                if row['maxErrorMeters'] > .035 or row['p99ErrorMeters'] > .012:
                    raise ValueError('Four-weight runtime derivative exceeds measured motion tolerance: ' + json.dumps(row))
    finally:
        for obj, obj_scene, action, slot, tracks, frame in saved:
            data = obj.animation_data
            data.action = action
            if action and slot:
                data.action_slot = slot
            for track, mute in tracks:
                track.mute = mute
            obj_scene.frame_set(frame)
    return {'samples': rows, 'maxErrorMeters': max(row['maxErrorMeters'] for row in rows),
            'maxP99ErrorMeters': max(row['p99ErrorMeters'] for row in rows),
            'sampleCount': len(rows), 'passedMeasuredMotionTolerance': True}


def preserve_fbx_materials(meshes, report):
    """Preserve the library FBX's imported materials and embedded image pixels.

    Never transplant the unrelated Jumpsuit materials onto the Remy library
    human. Missing texture pixels fail validation before public publication.
    """
    materials = {m for o in meshes for m in o.data.materials if m is not None}
    if not materials:
        raise ValueError('Library WithSkin FBX has no materials')
    image_rows, images = [], set()
    for mat in materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                images.add(node.image)
    if not images:
        raise ValueError('Library WithSkin FBX has no usable texture images')
    for image in images:
        if image.size[0] <= 0 or image.size[1] <= 0:
            raise ValueError('FBX texture image has no pixels: ' + image.name)
        if not image.packed_file:
            image.pack()
        if not image.packed_file:
            raise ValueError('FBX texture could not be packed: ' + image.name)
        image_rows.append({'name': image.name, 'size': list(image.size),
                           'colorspace': image.colorspace_settings.name,
                           'packedBytes': image.packed_file.size,
                           'packedSha256': hashlib.sha256(image.packed_file.data).hexdigest()})
    report['materials'] = {'method': 'Preserved Mixamo library FBX materials, UVs and image pixels; packed for standalone use',
                           'materials': len(materials), 'packedImages': len(images),
                           'materialNames': sorted(m.name for m in materials),
                           'images': sorted(image_rows, key=lambda row: row['name']),
                           'meshesWithUvs': sum(bool(o.data.uv_layers) for o in meshes)}


def evaluated_points(scene, meshes, frame):
    bpy.context.window.scene = scene
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    parts = []
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        parts.append(np.array([tuple(evaluated.matrix_world @ v.co) for v in evaluated.data.vertices]))
    points = np.concatenate(parts)
    if not np.isfinite(points).all():
        raise ValueError('Nonfinite posed vertices')
    return points


def motion_report(scene, arm, meshes, clips):
    data = arm.animation_data
    saved_action = data.action
    saved_slot = getattr(data, 'action_slot', None)
    saved_mutes = [(t, t.mute) for t in data.nla_tracks]
    saved_frame = scene.frame_current
    rows = []
    try:
        for t, _ in saved_mutes:
            t.mute = True
        for clip in CLIPS:
            action, slot = clips[clip]
            bind_action(arm, action, slot)
            start, end = map(float, action.frame_range)
            frames = [start + (end - start) * fraction for fraction in (0, .17, .31, .5, .73, .91, 1)]
            first = evaluated_points(scene, meshes, frames[0])
            displacements = []
            sample_bounds = []
            for frame in frames[1:]:
                points = evaluated_points(scene, meshes, frame)
                if points.shape != first.shape:
                    raise ValueError('Animated topology changed: ' + clip)
                displacements.append(float(np.linalg.norm(points - first, axis=1).max()))
                sample_bounds.append({'frame': frame, 'min': points.min(axis=0).tolist(),
                                      'max': points.max(axis=0).tolist()})
            maximum = max(displacements)
            if maximum <= .00001:
                raise ValueError('No measured skin deformation: ' + clip)
            rows.append({'clip': clip, 'frames': frames, 'finiteVertices': int(len(first)),
                         'maxSampleDisplacementMeters': maximum,
                         'perSampleDisplacementMeters': displacements,
                         'sampleBoundsMeters': sample_bounds})
    finally:
        data.action = saved_action
        if saved_action and saved_slot:
            data.action_slot = saved_slot
        for t, mute in saved_mutes:
            t.mute = mute
        scene.frame_set(saved_frame)
    return rows


def glb_report(path):
    doc, binary = read_glb(path)
    clip_names = [a.get('name') for a in doc.get('animations', [])]
    if sorted(clip_names) != sorted(CLIPS):
        raise ValueError('Expected exactly four exported NLA clips: ' + str(clip_names))
    if not doc.get('skins') or any('mesh' not in n for n in doc['nodes'] if 'skin' in n):
        raise ValueError('Invalid skin-to-mesh nodes')
    if not doc.get('images') or not all('bufferView' in image for image in doc['images']):
        raise ValueError('Textures must be embedded in the standalone GLB')
    total, maximum = 0, 0
    for node in doc['nodes']:
        if 'skin' not in node:
            continue
        skin = doc['skins'][node['skin']]
        for prim in doc['meshes'][node['mesh']]['primitives']:
            attrs = prim['attributes']
            pos = accessor_array(doc, binary, attrs['POSITION'])
            if not np.isfinite(pos).all():
                raise ValueError('Nonfinite GLB positions')
            weights, joints = [], []
            for channel in (0, 1):
                wk, jk = 'WEIGHTS_' + str(channel), 'JOINTS_' + str(channel)
                if wk in attrs:
                    weights.append(accessor_array(doc, binary, attrs[wk]))
                    joints.append(accessor_array(doc, binary, attrs[jk]))
            if not weights:
                raise ValueError('GLB primitive is missing skin weights')
            w, j = np.concatenate(weights, axis=1), np.concatenate(joints, axis=1)
            if not np.isfinite(w).all() or np.min(w) < 0 or np.max(np.abs(w.sum(axis=1) - 1)) > .003:
                raise ValueError('Invalid exported weight normalization')
            if np.any(j[w > 1e-8] >= len(skin['joints'])):
                raise ValueError('Invalid joint index')
            maximum = max(maximum, int((w > 1e-8).sum(axis=1).max()))
            total += len(pos)
    for animation in doc['animations']:
        for sampler in animation['samplers']:
            if not np.isfinite(accessor_array(doc, binary, sampler['output'])).all():
                raise ValueError('Nonfinite animation samples')
    return {'clips': clip_names, 'skins': len(doc['skins']),
            'jointCounts': [len(s['joints']) for s in doc['skins']],
            'skinnedPrimitiveVertices': total, 'maxInfluences': maximum,
            'materials': len(doc.get('materials', [])), 'images': len(doc.get('images', [])),
            'allImagesEmbedded': all('bufferView' in im for im in doc.get('images', [])),
            'skinNodesWithoutMesh': 0, 'finiteAnimationOutputs': True}


def reimport_clips(arm):
    result = {}
    ad = arm.animation_data
    if ad:
        for track in ad.nla_tracks:
            for strip in track.strips:
                for clip in CLIPS:
                    if track.name == clip or track.name.rsplit('|', 1)[-1] == clip or strip.action.name.rsplit('|', 1)[-1] == clip:
                        result[clip] = (strip.action, getattr(strip, 'action_slot', None))
    if set(result) != set(CLIPS):
        raise ValueError('Reimport is missing usable animation tracks: ' + str(list(result)))
    return result


def stage_city_npc(objects, arm, root, report):
    city = bpy.data.scenes.get(ARAPIRACA_NAME)
    if city is None:
        report['cityNpc'] = {'staged': False, 'reason': 'Arapiraca scene does not exist'}
        return
    bpy.context.window.scene = city
    col = bpy.data.collections.new('ARAP_MIXAMO_' + CHARACTER.upper() + '_' + SUFFIX)
    city.collection.children.link(col)
    copies = {o: o.copy() for o in objects + [root]}
    for old, copied in copies.items():
        if old.type == 'ARMATURE':
            copied.data = old.data.copy()
        col.objects.link(copied)
        if old.parent in copies:
            copied.parent = copies[old.parent]
        for modifier in copied.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object in copies:
                modifier.object = copies[modifier.object]
    new_root = copies[root]
    new_root.name = 'NPC_ARAP_' + CHARACTER + '_Mixamo_' + SUFFIX
    new_root.location += Vector((-6, -14, 0))
    new_root['source_id'] = ASSET_ID
    new_root['actual_mixamo'] = True
    city_arm = copies[arm]
    city_arm.animation_data.action = None
    for track in city_arm.animation_data.nla_tracks:
        track.mute = track.name != 'Idle'
    report['cityNpc'] = {'staged': True, 'scene': city.name, 'collection': col.name,
                         'root': new_root.name, 'armature': city_arm.name,
                         'oldCityInstancesHidden': [], 'originalCatalogScenesPreserved': True}


def run():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {'version': 2, 'status': 'preflight', 'id': ASSET_ID, 'sourceId': ASSET_ID,
              'libraryCharacter': CHARACTER, 'sourceKind': 'Mixamo library humanoid',
              'sourceUrl': 'https://www.mixamo.com/', 'customJumpsuitAutorigClaim': False,
              'actualMixamoDownloads': False, 'blenderVersion': bpy.app.version_string,
              'timestampUtc': datetime.now(timezone.utc).isoformat(), 'imports': [],
              'actions': [], 'warnings': [], 'sourcesPreserved': False}
    previous_scene = bpy.context.window.scene
    try:
        files = {clip: DOWNLOADS / (clip + '.fbx') for clip in CLIPS}
        for clip, path in files.items():
            if not path.is_file() or path.stat().st_size < 1024:
                raise FileNotFoundError('Missing actual Mixamo download: ' + str(path))
            with path.open('rb') as source:
                signature = source.read(100)
            if not (signature.startswith(b'Kaydara FBX Binary  ') or b'FBX' in signature[:80]):
                raise ValueError('Download is not an FBX file: ' + str(path))
        if bpy.data.scenes.get(SCENE_NAME) or DEST.exists() or STAGING.exists() or BLEND.exists() or REPORT_PATH.exists():
            raise FileExistsError('Existing Mixamo delivery/attempt: inspect it and choose a new suffix')
        # Read existing metadata before changes. Only append after actual validation.
        existing_metadata = json.loads(METADATA.read_text(encoding='utf-8')) if METADATA.exists() else []
        if not isinstance(existing_metadata, list) or any(row.get('id') == ASSET_ID for row in existing_metadata):
            raise ValueError('Mixamo metadata needs review; expected list without this delivery ID')
        report['downloads'] = [{'clip': clip, 'path': str(path), 'bytes': path.stat().st_size,
                                'sha256': sha256(path)} for clip, path in files.items()]
        if globals().get('PREP_MIXAMO_CHECKPOINT', True):
            checkpoint = ROOT / 'art/blender/checkpoints' / ('BEFORE_MIXAMO_' + CHARACTER.upper() + '_' + SUFFIX + '.blend')
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            if checkpoint.exists():
                raise FileExistsError('Checkpoint already exists: ' + str(checkpoint))
            bpy.data.libraries.write(str(checkpoint), {previous_scene},
                                     path_remap='ABSOLUTE', fake_user=True, compress=True)
            report['checkpointBefore'] = str(checkpoint)
            report['checkpointScope'] = 'Previously active scene and its dependencies; original full master remains untouched'
        scene = bpy.data.scenes.new(SCENE_NAME)
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        scene.render.fps = 30
        scene['source_id'] = report['sourceId']
        scene['animation_source'] = 'User-authorized Mixamo library character and genuine skeletal animation downloads'
        scene['library_character'] = CHARACTER
        report['stage'] = 'import base'
        source_scene = bpy.data.scenes.new('MIXAMO_SOURCE_' + CHARACTER.upper() + '_IDLE_ORIGINAL_' + SUFFIX)
        source_scene.unit_settings.system, source_scene.unit_settings.scale_length = 'METRIC', 1
        source_scene.render.fps = 30
        original_arm, original_objects = import_fbx(files['Idle'], source_scene, report)
        original_meshes = [obj for obj in original_objects if obj.type == 'MESH' and
                           any(mod.type == 'ARMATURE' and mod.object == original_arm for mod in obj.modifiers)]
        original_skin_fingerprint = skin_fingerprint(original_meshes)
        report['originalImportedSkin'] = skin_report(original_arm, original_meshes)
        report['originalImportedSkinScene'] = source_scene.name
        source_scene['purpose'] = 'Unchanged genuine WithSkin FBX import including all source influences; retained for audit'
        arm, objects = independent_working_copy(original_arm, original_objects, scene)
        bpy.context.window.scene = scene
        scene.render.fps, scene.render.fps_base = source_scene.render.fps, source_scene.render.fps_base
        meshes = [o for o in objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
        if not meshes:
            raise ValueError('Idle WithSkin contains no skinned meshes')
        report['actualMixamoDownloads'] = True
        report['skinBeforeExport'] = skin_report(arm, meshes)
        if report['skinBeforeExport']['maxInfluences'] > 4:
            if not globals().get('PREP_MIXAMO_REDUCE_WEIGHTS', True):
                raise ValueError('Eight-influence source requires measured four-weight derivative for this runtime')
            report['weightReduction'] = reduce_to_four(arm, meshes)
            report['skinBeforeExport'] = skin_report(arm, meshes)
        fps = scene.render.fps / scene.render.fps_base
        base_action, base_slot = imported_action(arm)
        # Archive the genuine imported action; build separate copied export clips.
        original_idle = base_action.copy()
        original_idle.use_fake_user = True
        original_idle.name = 'MIXAMO_Imported_Idle_Original_' + SUFFIX
        arm.animation_data.action = original_idle
        if base_slot:
            arm.animation_data.action_slot = compatible_slot(original_idle, base_slot)
        for track in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(track)
        # The Idle copy must be made while the original action remains active.
        idle_action, idle_slot, idle_track = make_clip(arm, arm, 'Idle', fps, report)
        clips = {'Idle': (idle_action, idle_slot)}
        preserved_source_scenes = [source_scene]
        for clip in CLIPS[1:]:
            report['stage'] = 'import ' + clip
            imported_scene = bpy.data.scenes.new('MIXAMO_SOURCE_' + CHARACTER.upper() + '_' + clip.upper() + '_' + SUFFIX)
            imported_scene.unit_settings.system = 'METRIC'
            imported_scene.unit_settings.scale_length = 1
            imported_scene.render.fps = round(fps)
            source_arm, _ = import_fbx(files[clip], imported_scene, report)
            action, slot, _ = make_clip(source_arm, arm, clip, fps, report)
            clips[clip] = (action, slot)
            imported_scene['purpose'] = 'Preserved genuine imported Mixamo clip; not an extra runtime character'
            preserved_source_scenes.append(imported_scene)
        bpy.context.window.scene = scene
        report['stage'] = 'preserve FBX materials and embedded textures'
        preserve_fbx_materials(meshes, report)
        report['stage'] = 'normalize new parent'
        arm.animation_data.action = None
        for track in arm.animation_data.nla_tracks:
            track.mute = True
        arm.data.pose_position = 'REST'
        points = evaluated_points(scene, meshes, 1)
        lo, hi = points.min(axis=0), points.max(axis=0)
        height = float(hi[2] - lo[2])
        if not .01 < height < 1000:
            raise ValueError('Implausible imported character bounds')
        root = bpy.data.objects.new('CHR_' + CHARACTER + '_Mixamo_Root_' + SUFFIX, None)
        scene.collection.objects.link(root)
        root['source_id'] = ASSET_ID
        root['mixamo_library_character'] = CHARACTER
        root['genuine_mixamo_animations'] = True
        for obj in objects:
            if obj.parent not in objects:
                world = obj.matrix_world.copy()
                obj.parent = root
                obj.matrix_world = world
        scale = 1.8 / height
        root.scale = (scale,) * 3
        root.location = Vector((-float((lo[0] + hi[0]) / 2), -float((lo[1] + hi[1]) / 2), -float(lo[2]))) * scale
        bpy.context.view_layer.update()
        normalized = evaluated_points(scene, meshes, 1)
        if abs(float(np.ptp(normalized[:, 2])) - 1.8) > .001 or abs(float(normalized[:, 2].min())) > .001:
            raise ValueError('Parent normalization did not preserve expected metre bounds')
        arm.data.pose_position = 'POSE'
        report['normalization'] = {'method': 'New parent only; mesh and armature transforms not applied',
                                   'importedRestHeight': height, 'parentUniformScale': scale,
                                   'normalizedRestHeightMeters': float(np.ptp(normalized[:, 2])),
                                   'normalizedRestMinZ': float(normalized[:, 2].min())}
        report['sourceMotionProof'] = motion_report(scene, arm, meshes, clips)
        if report.get('weightReduction'):
            report['weightReduction']['motionComparison'] = reduction_motion_report(
                source_scene, original_arm, original_meshes, scene, arm, meshes, clips, scale, root.location)
        if skin_fingerprint(original_meshes) != original_skin_fingerprint:
            raise ValueError('Original imported eight-influence skin changed')
        report['originalImportedSkinPreserved'] = True
        report['stage'] = 'export'
        for track in arm.animation_data.nla_tracks:
            track.mute = False
        arm.animation_data.action = None
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects + [root]:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = arm
        STAGING.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(STAGING), export_format='GLB', use_selection=True,
            use_active_scene=True, export_yup=True, export_animations=True, export_skins=True,
            export_animation_mode='NLA_TRACKS', export_lights=False, export_cameras=False,
            export_extras=True, export_image_format='AUTO')
        report['glb'] = glb_report(STAGING)
        report['stage'] = 'reimport and pose validation'
        validation = bpy.data.scenes.new('VALIDATE_MIXAMO_' + CHARACTER.upper() + '_' + SUFFIX)
        validation.unit_settings.system = 'METRIC'
        validation.unit_settings.scale_length = 1
        validation.render.fps = round(fps)
        bpy.context.window.scene = validation
        bpy.ops.import_scene.gltf(filepath=str(STAGING))
        validation_arms = [o for o in validation.objects if o.type == 'ARMATURE']
        if len(validation_arms) != 1:
            raise ValueError('GLB reimport armature count mismatch')
        validation_arm = validation_arms[0]
        validation_meshes = [o for o in validation.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == validation_arm for m in o.modifiers)]
        report['reimportSkin'] = skin_report(validation_arm, validation_meshes)
        validated_clips = reimport_clips(validation_arm)
        report['reimportMotionProof'] = motion_report(validation, validation_arm, validation_meshes, validated_clips)
        report['reimportValidated'] = True
        validation_arm.animation_data.action = None
        for track in validation_arm.animation_data.nla_tracks:
            track.mute = track.name.rsplit('|', 1)[-1] != 'Idle'
        validation.frame_set(30)
        if globals().get('PREP_MIXAMO_RENDER', True):
            validation.world = bpy.data.worlds.new('MIXAMO_PREVIEW_WORLD_' + SUFFIX)
            validation.world.color = (.23, .23, .23)
            for location, energy in [((0, -3, 4), 450), ((2, 2, 3), 300)]:
                bpy.ops.object.light_add(type='AREA', location=location)
                bpy.context.object.data.energy = energy
                bpy.context.object.data.size = 4
            bpy.ops.object.camera_add(location=(2.2, -4.5, 1.8))
            camera = bpy.context.object
            camera.rotation_euler = (Vector((0, 0, .9)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = 2.3
            validation.camera = camera
            validation.render.engine = 'CYCLES'
            validation.cycles.samples = 8
            validation.render.resolution_x = 480
            validation.render.resolution_y = 600
            validation.render.resolution_percentage = 100
            validation.render.filepath = str(REPORT_DIR / (CHARACTER.lower() + '_' + SUFFIX + '_idle.png'))
            bpy.ops.render.render(write_still=True)
            report['preview'] = validation.render.filepath
        if globals().get('PREP_MIXAMO_STAGE_NPC', True):
            report['stage'] = 'stage city NPC copy'
            stage_city_npc(objects, arm, root, report)
        bpy.context.window.scene = scene
        for track in arm.animation_data.nla_tracks:
            track.mute = track.name != 'Idle'
        scene.frame_set(1)
        for row in report['downloads']:
            if sha256(row['path']) != row['sha256']:
                raise ValueError('Actual Mixamo source FBX changed during integration: ' + row['clip'])
        # Publish only after the GLB has passed structural, skin and motion checks
        # and a real Blender reimport. No failed GLB enters the runtime registry.
        DEST.parent.mkdir(parents=True, exist_ok=True)
        with STAGING.open('rb') as source, DEST.open('xb') as target:
            shutil.copyfileobj(source, target)
        if sha256(STAGING) != sha256(DEST):
            raise ValueError('Validated GLB copy differs from staging export')
        report.update(url='/assets/characters/' + DEST.name, path=str(DEST),
                      bytes=DEST.stat().st_size, sha256=sha256(DEST), scene=scene.name,
                      sourcesPreserved=True, bones=len(arm.data.bones), clips=list(CLIPS),
                      weightCoverage=report['skinBeforeExport']['weightCoverage'],
                      maxInfluences=report['skinBeforeExport']['maxInfluences'],
                      animations=list(CLIPS), idleClip='Idle', walkClip='Walk',
                      category='Personagens', name=CHARACTER + ' · Mixamo',
                      animated=True, rigged=True, playable=True,
                      visualStyle='realistic',
                      quality='Mixamo library human with genuine skeletal clips; realism art review remains required')
        if globals().get('PREP_MIXAMO_SAVE_BLEND', True):
            report['stage'] = 'save independent character scene'
            BLEND.parent.mkdir(parents=True, exist_ok=True)
            blend_data = {scene, *preserved_source_scenes}
            bpy.data.libraries.write(str(BLEND), blend_data,
                                     path_remap='ABSOLUTE', fake_user=True, compress=True)
            report['blend'] = str(BLEND)
            report['blendBytes'] = BLEND.stat().st_size
            report['blendScope'] = 'Independent runtime character, unchanged eight-influence source scene, and three genuine imported motion scenes; full master saved separately'
            with bpy.data.libraries.load(str(BLEND), link=False) as (data_from, data_to):
                if SCENE_NAME not in data_from.scenes:
                    raise ValueError('Independent blend does not contain the character scene')
                report['blendSceneNamesVerified'] = list(data_from.scenes)
        report['status'] = 'validated'
        report['stage'] = 'complete'
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if globals().get('PREP_MIXAMO_WRITE_METADATA', True):
            entry_keys = ('id', 'sourceId', 'libraryCharacter', 'sourceKind', 'sourceUrl',
                          'name', 'category', 'url', 'bytes', 'sha256', 'bones', 'clips',
                          'animations', 'idleClip', 'walkClip', 'rigged', 'animated',
                          'playable', 'quality', 'visualStyle', 'reimportValidated', 'weightCoverage', 'maxInfluences')
            entry = {key: report[key] for key in entry_keys}
            entry['validationReport'] = str(REPORT_PATH.relative_to(ROOT)).replace('\\', '/')
            entry['actualMixamoDownloads'] = True
            current_metadata = json.loads(METADATA.read_text(encoding='utf-8')) if METADATA.exists() else []
            if current_metadata != existing_metadata:
                raise RuntimeError('Mixamo metadata changed concurrently; validated files retained for manual registry merge')
            METADATA.parent.mkdir(parents=True, exist_ok=True)
            metadata_pending = METADATA.with_suffix('.json.pending')
            with metadata_pending.open('x', encoding='utf-8') as target:
                json.dump(current_metadata + [entry], target, ensure_ascii=False, indent=2)
                target.write('\n')
            metadata_pending.replace(METADATA)
            report['metadataPath'] = str(METADATA)
            REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': report['status'], 'report': str(REPORT_PATH), 'url': report['url'],
                          'bones': report['bones'], 'clips': report['clips'],
                          'images': report['glb']['images'], 'reimportValidated': True}, ensure_ascii=False))
        return report
    except Exception as exc:
        report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
        failed = REPORT_DIR / (CHARACTER.lower() + '_' + SUFFIX + '_failed_' + datetime.now().strftime('%H%M%S') + '.json')
        failed.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Mixamo integration failed; originals retained; report: ' + str(failed))
        raise
    finally:
        if previous_scene and previous_scene.name in bpy.data.scenes:
            bpy.context.window.scene = previous_scene


if __name__ == '__main__':
    run()
