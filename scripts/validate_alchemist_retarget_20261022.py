"""Independent Alchemist GLB reimport, skin, posture and motion validation.

Execute through Blender MCP from the dedicated retarget library, never from the
master. Optional globals PREP_ALCHEMIST_GLB and PREP_ALCHEMIST_RENDER override the
input GLB path and rendering switch. Clip provenance is intentionally agnostic.
This script preserves the input GLB and working library on disk and saves a
separate reimport-review blend; it does not change runtime manifests or master.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
GLB = Path(globals().get(
    'PREP_ALCHEMIST_GLB',
    ROOT / 'art/character_retarget_20261022/CHR_Alchemist_Anime_Retarget_20261022.glb',
)).resolve()
WORKING = ROOT / 'art/blender/libraries/PREP_CHARACTER_ALCHEMIST_RETARGET_20261022.blend'
BLEND = ROOT / 'art/blender/libraries/PREP_CHARACTER_ALCHEMIST_REIMPORT_20261022.blend'
REPORT = ROOT / 'reports/CHARACTER_ALCHEMIST_REIMPORT_20261022.json'
RENDERS = ROOT / 'reports/alchemist_reimport_20261022'
RENDER_ENABLED = bool(globals().get('PREP_ALCHEMIST_RENDER', True))
TARGET_HEIGHT = 1.70
FLOOR_TOLERANCE = .02
SEGMENT_RATIO_TOLERANCE = .02
EXPECTED_BONES = {
    'root', 'hips', 'spine', 'chest', 'neck', 'head',
    *(
        f'{side}_{part}'
        for side in ('L', 'R')
        for part in ('clavicle', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot')
    ),
}
SEGMENTS = [
    ('hips', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head'),
    *(
        (f'{side}_{start}', f'{side}_{end}')
        for side in ('L', 'R')
        for start, end in (
            ('upper_arm', 'forearm'), ('forearm', 'hand'),
            ('thigh', 'shin'), ('shin', 'foot'),
        )
    ),
    ('hips', 'L_thigh'), ('hips', 'R_thigh'),
]
report = {
    'createdAt': datetime.now(timezone.utc).isoformat(),
    'status': 'in-progress',
    'motionSource': 'not-assumed; validation uses exported Idle and Walk only',
    'checks': {}, 'clipSamples': [], 'renders': [],
    'tolerances': {
        'heightMeters': .02, 'floorMeters': FLOOR_TOLERANCE,
        'segmentLengthRelative': SEGMENT_RATIO_TOLERANCE,
        'weightSum': .003, 'maximumInfluences': 4,
    },
    'visualReview': 'pending', 'runtimeChanged': False, 'masterChanged': False,
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_report():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')


def main():
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    assert current == WORKING.resolve(), (
        'Run QA only from the dedicated retarget working library.', bpy.data.filepath,
    )
    assert not bpy.data.is_dirty, 'Save/audit the working library before independent QA.'
    assert GLB.is_file(), GLB
    assert GLB != BLEND.resolve() and BLEND.resolve() != WORKING.resolve()
    working_sha = sha256(WORKING)
    raw = GLB.read_bytes()
    assert struct.unpack_from('<III', raw, 0) == (0x46546C67, 2, len(raw))
    json_length, json_type = struct.unpack_from('<II', raw, 12)
    assert json_type == 0x4E4F534A
    doc = json.loads(raw[20:20 + json_length])
    source_sha = hashlib.sha256(raw).hexdigest()
    report['source'] = {'path': str(GLB), 'sha256': source_sha, 'bytes': len(raw)}
    report['workingLibrary'] = {'path': str(WORKING), 'sha256': working_sha}
    clip_names = [clip.get('name') for clip in doc.get('animations', [])]
    report['checks'].update(
        clipsIdleWalk=sorted(clip_names) == ['Idle', 'Walk'],
        singleSkin=len(doc.get('skins', [])) == 1,
    )
    assert report['checks']['clipsIdleWalk'], clip_names
    assert report['checks']['singleSkin'], len(doc.get('skins', []))

    scene = bpy.data.scenes.new('VALIDATE_ALCHEMIST_RETARGET_20261022')
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.fps = 30
    scene.render.fps_base = 1
    bpy.context.window.scene = scene
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    bpy.context.view_layer.update()
    arms = [obj for obj in scene.objects if obj.type == 'ARMATURE']
    meshes = [obj for obj in scene.objects if obj.type == 'MESH']
    report['checks'].update(singleArmature=len(arms) == 1, singleCharacterMesh=len(meshes) == 1)
    assert len(arms) == 1 and len(meshes) == 1, (len(arms), len(meshes))
    arm = arms[0]
    report['boneNames'] = sorted(bone.name for bone in arm.data.bones)
    report['meshNames'] = [obj.name for obj in meshes]
    report['checks']['exact20BoneRig'] = set(report['boneNames']) == EXPECTED_BONES
    assert report['checks']['exact20BoneRig'], report['boneNames']
    report['checks']['meshUsesImportedRig'] = all(
        any(mod.type == 'ARMATURE' and mod.object == arm for mod in obj.modifiers)
        for obj in meshes
    )
    assert arm.animation_data, 'Imported rig has no animation data.'
    clip_tracks = {}
    for track in arm.animation_data.nla_tracks:
        name = track.name.rsplit('|', 1)[-1]
        if name in ('Idle', 'Walk'):
            assert name not in clip_tracks, f'Duplicate track: {name}'
            assert len(track.strips) == 1, (name, len(track.strips))
            clip_tracks[name] = track
    assert set(clip_tracks) == {'Idle', 'Walk'}, list(clip_tracks)

    max_influences = 0
    max_sum_error = 0
    unweighted = 0
    foot_indices = {'L': [], 'R': []}
    vertex_offset = 0
    for obj in meshes:
        bone_groups = {group.index for group in obj.vertex_groups if group.name in arm.data.bones}
        foot_bones = {
            side: {
                bone.name for bone in arm.data.bones
                if bone.name == f'{side}_foot'
                or any(parent.name == f'{side}_foot' for parent in bone.parent_recursive)
            }
            for side in foot_indices
        }
        foot_groups = {
            side: {group.index for group in obj.vertex_groups if group.name in names}
            for side, names in foot_bones.items()
        }
        for vertex in obj.data.vertices:
            raw_weights = [group.weight for group in vertex.groups if group.group in bone_groups]
            assert all(math.isfinite(value) and value >= 0 for value in raw_weights)
            weights = [value for value in raw_weights if value > 1e-8]
            max_influences = max(max_influences, len(weights))
            max_sum_error = max(max_sum_error, abs(sum(weights) - 1))
            unweighted += not weights
            for side, groups in foot_groups.items():
                if sum(group.weight for group in vertex.groups if group.group in groups) > .5:
                    foot_indices[side].append(vertex_offset + vertex.index)
        vertex_offset += len(obj.data.vertices)
    report.update(
        vertices=vertex_offset, maxInfluences=max_influences,
        maxWeightSumError=max_sum_error, unweightedVertices=unweighted,
        independentFootVertices={side: len(indices) for side, indices in foot_indices.items()},
    )
    report['checks'].update(
        maximumFourInfluences=max_influences <= 4,
        normalizedWeights=max_sum_error < .003,
        fullWeightCoverage=unweighted == 0,
        independentFootRegions=all(foot_indices.values()),
    )
    assert report['checks']['independentFootRegions'], report['independentFootVertices']

    def points():
        graph = bpy.context.evaluated_depsgraph_get()
        arrays = []
        for obj in meshes:
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            try:
                coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
                mesh.vertices.foreach_get('co', coords)
                matrix = np.array(evaluated.matrix_world)
                arrays.append(coords.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])
            finally:
                evaluated.to_mesh_clear()
        result = np.concatenate(arrays)
        assert len(result) == vertex_offset, 'A modifier changed vertex indexing during QA.'
        assert np.isfinite(result).all(), 'Nonfinite deformed vertices.'
        return result

    def select_sample(clip, fraction):
        arm.animation_data.action = None
        for track in arm.animation_data.nla_tracks:
            track.mute = track != clip_tracks[clip]
        strip = clip_tracks[clip].strips[0]
        frame = strip.frame_start + (strip.frame_end - strip.frame_start) * fraction
        scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
        bpy.context.view_layer.update()
        return frame

    select_sample('Idle', 0)
    baseline_joints = {bone.name: arm.matrix_world @ bone.head for bone in arm.pose.bones}
    baseline_lengths = {
        f'{start}->{end}': (baseline_joints[end] - baseline_joints[start]).length
        for start, end in SEGMENTS
    }
    assert all(length > .005 for length in baseline_lengths.values()), baseline_lengths
    report['referenceSegmentLengthsMeters'] = baseline_lengths
    max_segment_error = 0
    max_floor_error = 0
    max_support_error = 0
    walk_displacement = 0
    first_walk = None
    for clip in ('Idle', 'Walk'):
        samples = []
        # Includes the four requested Walk phases and halfway interpolation samples.
        for fraction in (0, .125, .25, .375, .5, .625, .75, .875, 1):
            frame = select_sample(clip, fraction)
            posed = points()
            low, high = posed.min(axis=0), posed.max(axis=0)
            floor_error = abs(float(low[2]))
            max_floor_error = max(max_floor_error, floor_error)
            foot_minima = {side: float(posed[indices, 2].min()) for side, indices in foot_indices.items()}
            max_support_error = max(max_support_error, abs(min(foot_minima.values())))
            joints = {bone.name: arm.matrix_world @ bone.head for bone in arm.pose.bones}
            assert all(math.isfinite(component) for value in joints.values() for component in value)
            lengths = {f'{a}->{b}': (joints[b] - joints[a]).length for a, b in SEGMENTS}
            relative_errors = {key: abs(length / baseline_lengths[key] - 1) for key, length in lengths.items()}
            max_segment_error = max(max_segment_error, max(relative_errors.values()))
            sample = {
                'fraction': fraction, 'frame': frame, 'min': low.tolist(), 'max': high.tolist(),
                'height': float(high[2] - low[2]), 'floorError': floor_error,
                'footMinima': foot_minima, 'segmentLengthsMeters': lengths,
                'maxRelativeSegmentError': max(relative_errors.values()),
                'joints': {name: list(position) for name, position in joints.items()},
            }
            if clip == 'Walk':
                if first_walk is None:
                    first_walk = posed.copy()
                displacement = float(np.linalg.norm(posed - first_walk, axis=1).max())
                walk_displacement = max(walk_displacement, displacement)
                sample['maxVertexDisplacementFromFirst'] = displacement
            samples.append(sample)
        report['clipSamples'].append({'clip': clip, 'samples': samples})
    idle_height = report['clipSamples'][0]['samples'][0]['height']
    report.update(
        maxFloorError=max_floor_error, maxSupportingFootError=max_support_error,
        maxRelativeSegmentError=max_segment_error, walkDeformation=walk_displacement,
        idleHeightMeters=idle_height,
    )
    report['checks'].update(
        freshBlenderReimport=True, finiteVerticesAndJoints=True,
        idleHeightWithin2cm=abs(idle_height - TARGET_HEIGHT) <= .02,
        idleBothFeetWithin2cm=all(abs(value)<=FLOOR_TOLERANCE
            for sample in report['clipSamples'][0]['samples'] for value in sample['footMinima'].values()),
        floorContactWithin2cm=max_floor_error <= FLOOR_TOLERANCE,
        supportingFootWithin2cm=max_support_error <= FLOOR_TOLERANCE,
        segmentLengthsWithin2percent=max_segment_error <= SEGMENT_RATIO_TOLERANCE,
        actualWalkDeformation=walk_displacement > .08,
    )

    if RENDER_ENABLED:
        scene.world = bpy.data.worlds.new('PREP_Alchemist_Reimport_Review_World')
        scene.world.color = (.025, .035, .05)
        for location, energy, size in (
            ((2.4, -3.4, 3), 850, 3), ((-2.4, -1, 2), 500, 2.5), ((0, 2.5, 2.8), 650, 2),
        ):
            bpy.ops.object.light_add(type='AREA', location=location)
            light = bpy.context.object
            light.data.energy = energy
            light.data.size = size
            light.rotation_euler = (Vector((0, 0, .85)) - light.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.ops.object.camera_add()
        camera = bpy.context.object
        scene.camera = camera
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.resolution_x = 480
        scene.render.resolution_y = 640
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        RENDERS.mkdir(parents=True, exist_ok=True)
        for clip, fraction in [('Idle', 0), *[('Walk', value) for value in (0, .25, .5, .75)]]:
            select_sample(clip, fraction)
            posed = points()
            center = Vector(((posed.min(axis=0) + posed.max(axis=0)) * .5).tolist())
            for name, offset in (('front', (0, -5, 0)), ('side', (5, 0, 0))):
                camera.location = center + Vector(offset)
                camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
                camera.data.type = 'ORTHO'
                camera.data.ortho_scale = 1.98
                image = RENDERS / f'{clip}_{round(fraction * 100):03d}_{name}.png'
                scene.render.filepath = str(image)
                bpy.ops.render.render(write_still=True)
                assert image.is_file() and image.stat().st_size > 1000
                report['renders'].append(str(image))
    report['checks']['requestedRendersWritten'] = not RENDER_ENABLED or len(report['renders']) == 10
    report['renderingEnabled'] = RENDER_ENABLED
    select_sample('Idle', 0)
    report['scene'] = scene.name
    # A different path preserves the retarget library and any master on disk.
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    report['blend'] = {'path': str(BLEND), 'sha256': sha256(BLEND), 'bytes': BLEND.stat().st_size}
    report['checks'].update(
        sourceGLBPreserved=sha256(GLB) == source_sha,
        workingLibraryPreserved=sha256(WORKING) == working_sha,
    )
    report['status'] = 'reimport-passed-awaiting-visual-review' if all(report['checks'].values()) else 'reimport-failed'
    write_report()
    print(json.dumps({key: report[key] for key in (
        'status', 'checks', 'idleHeightMeters', 'maxFloorError',
        'maxSupportingFootError', 'maxRelativeSegmentError', 'source',
    )}))
    assert all(report['checks'].values()), report['checks']


try:
    main()
except Exception:
    if report['status'] == 'in-progress':
        report['status'] = 'qa-error'
    report['error'] = traceback.format_exc()
    write_report()
    raise
