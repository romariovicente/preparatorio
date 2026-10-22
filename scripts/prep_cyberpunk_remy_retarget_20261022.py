"""Retarget genuine Remy motion onto the preserved Cyberpunk neutral pose.

Run through the existing Blender MCP after inspect_retarget_blender_20261022.py.
The validated neutral library, master, and current runtime asset stay preserved.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
VERSION = str(globals().get('PREP_RETARGET_VERSION', ''))
assert VERSION in ('','_v2','_v3','_v4','_v5')
WORKING = ROOT / f'art/blender/libraries/PREP_CHARACTER_CYBERPUNK_REMY_RETARGET_20261022{VERSION}.blend'
OUTPUT = ROOT / f'art/character_retarget_20261022/CHR_Cyberpunk_Remy_Retarget_20261022{VERSION}.glb'
REPORT = ROOT / f'reports/CHARACTER_CYBERPUNK_REMY_RETARGET_20261022{VERSION}.json'
TARGET_SCENE = 'PREP_CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022'
SOURCE_SCENE = 'MIXAMO_REMY_20261005'
NEUTRAL_SHA = 'cade5fff6780e8f36b7ac7f962a779f032fcb99e352281ad7ad3edf06c81eb28'


def sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def depth(bone):
    return 0 if bone.parent is None else 1 + depth(bone.parent)


def curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def bounds(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    parts = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            coords = np.empty(len(mesh.vertices)*3,dtype=np.float32)
            mesh.vertices.foreach_get('co',coords)
            matrix = np.array(evaluated.matrix_world)
            parts.append(coords.reshape(-1,3) @ matrix[:3,:3].T + matrix[:3,3])
        finally:
            evaluated.to_mesh_clear()
    points = np.concatenate(parts)
    assert np.isfinite(points).all()
    low, high = Vector(points.min(axis=0)), Vector(points.max(axis=0))
    return low, high


def activate_source(clip, frame):
    bpy.context.window.scene = source_scene
    source_arm.animation_data.action = None
    for track in source_arm.animation_data.nla_tracks:
        track.mute = track.name != clip
    source_scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {bone.name: source_arm.matrix_world @ bone.matrix.copy() for bone in source_arm.pose.bones}


def apply_world_pose(desired):
    inverse = target_arm.matrix_world.inverted()
    pose = {name: inverse @ world for name, world in desired.items()}
    for bone in target_bones:
        kwargs = {}
        if bone.parent:
            kwargs = {'parent_matrix': pose[bone.parent.name],
                      'parent_matrix_local': bone.parent.bone.matrix_local}
        bone.matrix_basis = bone.bone.convert_local_to_pose(
            pose[bone.name], bone.bone.matrix_local, invert=True, **kwargs)
        bone.rotation_mode = 'QUATERNION'
    bpy.context.view_layer.update()


def render_sample(clip, frame, direction):
    target_scene.frame_set(frame)
    bpy.context.view_layer.update()
    low, high = bounds(target_meshes)
    center = (low + high) * 0.5
    camera = target_scene.camera
    camera.location = center + Vector((0, -5, 0) if direction == 'front' else (5, 0, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.98
    path = ROOT / f'reports/cyberpunk_retarget_20261022{VERSION}/{clip}_{frame:03d}_{direction}.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    target_scene.render.filepath = str(path)
    target_scene.render.resolution_x = 480
    target_scene.render.resolution_y = 640
    target_scene.render.resolution_percentage = 100
    bpy.ops.render.render(write_still=True)
    return str(path)


assert Path(bpy.data.filepath).resolve() == WORKING.resolve(), bpy.data.filepath
assert sha256(WORKING) == NEUTRAL_SHA, 'Working file already modified; audit before rerunning.'
target_scene = bpy.data.scenes[TARGET_SCENE]
source_scene = bpy.data.scenes[SOURCE_SCENE]
target_arm = next(obj for obj in target_scene.objects if obj.type == 'ARMATURE')
source_arm = next(obj for obj in source_scene.objects if obj.type == 'ARMATURE')
target_meshes = [obj for obj in target_scene.objects if obj.type == 'MESH' and obj.parent == target_arm]
assert len(target_meshes) == 35
bpy.context.window.scene = target_scene
target_scene.frame_set(1)
bpy.context.view_layer.update()
frozen_morph_objects=[]
for obj in target_meshes:
    keys=obj.data.shape_keys
    if keys and keys.animation_data:
        values={key.name:key.value for key in keys.key_blocks}
        keys.animation_data_clear()
        for key in keys.key_blocks:
            key.value=values[key.name]
        frozen_morph_objects.append(obj.name)
target_bones = sorted(target_arm.pose.bones, key=depth)
target_reference = {bone.name: target_arm.matrix_world @ bone.matrix.copy() for bone in target_bones}
source_reference = activate_source('Idle', 1)
reference_corrections = None
if VERSION in ('_v3','_v4','_v5'):
    helper=ROOT/'scripts/cyberpunk_reference_corrections_20261022.py'
    namespace={}
    exec(compile(helper.read_text(encoding='utf-8'),str(helper),'exec'),namespace)
    old_reference={name:matrix.copy() for name,matrix in target_reference.items()}
    corrected,overrides,reference_corrections=namespace['corrected_reference'](old_reference,source_reference)
    for bone in target_bones:
        if bone.name not in overrides and bone.parent:
            corrected[bone.name]=corrected[bone.parent.name] @ old_reference[bone.parent.name].inverted() @ old_reference[bone.name]
    bpy.context.window.scene=target_scene
    apply_world_pose(corrected)
    root=target_arm
    while root.parent:
        root=root.parent
    low,high=bounds(target_meshes)
    factor=1.7/(high.z-low.z)
    root.scale=tuple(value*factor for value in root.scale)
    bpy.context.view_layer.update()
    low,high=bounds(target_meshes)
    root.location.z-=low.z
    bpy.context.view_layer.update()
    target_reference={bone.name:target_arm.matrix_world @ bone.matrix.copy() for bone in target_bones}
    reference_corrections['uniformHeightScale']=factor
target_reference_local = {bone.name: target_reference[bone.parent.name].inverted() @ target_reference[bone.name]
                          if bone.parent else target_reference[bone.name] for bone in target_bones}

mapping = {
    'CC_Base_Hip_02': 'Hips',
    'CC_Base_Waist_033': 'Spine',
    'CC_Base_Spine01_034': 'Spine1',
    'CC_Base_Spine02_035': 'Spine2',
    'CC_Base_NeckTwist01_036': 'Neck',
    'CC_Base_Head_038': 'Head',
}
for side, code, suffixes in (
    ('Left', 'L', {'Thigh':'04', 'Calf':'05', 'Foot':'06', 'ToeBase':'00', 'Clavicle':'049', 'Upperarm':'050', 'Forearm':'051', 'Hand':'055'}),
    ('Right', 'R', {'Thigh':'018', 'Calf':'019', 'Foot':'021', 'ToeBase':'022', 'Clavicle':'077', 'Upperarm':'078', 'Forearm':'079', 'Hand':'083'}),
):
    for cc, mixamo in (('Thigh','UpLeg'), ('Calf','Leg'), ('Foot','Foot'), ('ToeBase','ToeBase'),
                       ('Clavicle','Shoulder'), ('Upperarm','Arm'), ('Forearm','ForeArm'), ('Hand','Hand')):
        mapping[f'CC_Base_{code}_{cc}_{suffixes[cc]}'] = side + mixamo
mapping = {target: 'mixamorig:' + source for target, source in mapping.items()}
assert all(name in target_reference and source in source_reference for name, source in mapping.items())

# Canonical source axes are X right, Y up, Z forward; target axes are X right,
# Z up and -Y forward. Motion deltas are converted between these world spaces.
source_up = source_reference['mixamorig:Head'].translation - source_reference['mixamorig:Hips'].translation
source_up_axis = max(range(3),key=lambda axis:abs(source_up[axis]))
source_up_cardinal = Vector((0,0,0))
source_up_cardinal[source_up_axis] = 1 if source_up[source_up_axis]>0 else -1
source_right = source_reference['mixamorig:LeftArm'].translation - source_reference['mixamorig:RightArm'].translation
source_right_axis = max((axis for axis in range(3) if axis!=source_up_axis), key=lambda axis:abs(source_right[axis]))
source_right_cardinal = Vector((0,0,0))
source_right_cardinal[source_right_axis] = 1 if source_right[source_right_axis]>0 else -1
source_back_cardinal = source_up_cardinal.cross(source_right_cardinal)
source_basis = Matrix((source_right_cardinal,source_back_cardinal,source_up_cardinal)).transposed()
alignment = source_basis.inverted().to_quaternion()
inverse_alignment = alignment.inverted()
source_hip = source_reference['mixamorig:Hips'].translation.copy()
target_hip = target_reference['CC_Base_Hip_02'].translation.copy()
source_leg = sum((source_reference[a].translation - source_reference[b].translation).length for a,b in
                 [('mixamorig:LeftUpLeg','mixamorig:LeftLeg'),('mixamorig:LeftLeg','mixamorig:LeftFoot')])
target_leg = sum((target_reference[a].translation - target_reference[b].translation).length for a,b in
                 [('CC_Base_L_Thigh_04','CC_Base_L_Calf_05'),('CC_Base_L_Calf_05','CC_Base_L_Foot_06')])
translation_scale = target_leg / source_leg
source_ref_rot = {name: matrix.to_quaternion() for name, matrix in source_reference.items()}
target_ref_rot = {name: matrix.to_quaternion() for name, matrix in target_reference.items()}
target_ref_scale = {name: matrix.to_scale() for name, matrix in target_reference.items()}
source_fps = source_scene.render.fps / source_scene.render.fps_base
target_scene.render.fps = round(source_fps)
target_scene.frame_start = 1
target_scene.render.image_settings.file_format = 'PNG'

report = {'createdAt':datetime.now(timezone.utc).isoformat(), 'status':'in-progress',
          'sourceLibrary':'art/blender/PREPARATORIO_MIXAMO_REMY_20261005.blend',
          'neutralLibrary':'art/blender/libraries/PREP_CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022.blend',
          'method':'world rotation deltas relative to real Remy Idle and complete Cyberpunk neutral pose; target hierarchy offsets retained',
          'mapping':mapping, 'translationScale':translation_scale, 'clips':[], 'renders':[],
          'evaluatedSourceUp':list(source_up),'sourceUpAxis':source_up_axis,'alignmentQuaternion':list(alignment),
          'referenceCorrections':reference_corrections,
          'legacyFacialMorphTracksFrozen':frozen_morph_objects,
          'runtimeChanged':False, 'masterChanged':False}
created = []
for clip in ('Idle', 'Walk'):
    source_track = next(track for track in source_arm.animation_data.nla_tracks if track.name == clip)
    source_strip = source_track.strips[0]
    end_frame = math.ceil(source_strip.frame_end)
    bpy.context.window.scene = target_scene
    target_arm.animation_data_create()
    for track in target_arm.animation_data.nla_tracks:
        track.mute = True
    action = bpy.data.actions.new(f'PREP_Cyberpunk_Remy_{clip}_20261022')
    action.use_fake_user = True
    target_arm.animation_data.action = action
    errors = []
    frame_rows = []
    previous_quats = {}
    horizontal_origin = None
    for frame in range(1, end_frame + 1):
        source_pose = activate_source(clip, frame)
        bpy.context.window.scene = target_scene
        target_scene.frame_set(frame)
        bpy.context.view_layer.update()
        source_delta = alignment @ (source_pose['mixamorig:Hips'].translation - source_hip) * translation_scale
        # Keep walking in place. Navigation owns world horizontal translation.
        source_delta.x = source_delta.y = 0.0
        desired = {}
        for bone in target_bones:
            ref = target_reference[bone.name]
            inherited = desired[bone.parent.name] @ target_reference_local[bone.name] if bone.parent else ref.copy()
            if bone.name in mapping:
                source_name = mapping[bone.name]
                delta = source_pose[source_name].to_quaternion() @ source_ref_rot[source_name].inverted()
                rotation = alignment @ delta @ inverse_alignment @ target_ref_rot[bone.name]
                position = inherited.translation.copy()
                if bone.name == 'CC_Base_Hip_02':
                    position = target_hip + source_delta
                desired[bone.name] = Matrix.LocRotScale(position, rotation, target_ref_scale[bone.name])
            else:
                desired[bone.name] = inherited
        if VERSION in ('_v4','_v5'):
            assert abs(alignment.w)>.99999, 'Segment fit requires the evaluated Z-up Remy source.'
            desired=namespace['fit_leg_motion'](desired,target_reference,source_pose,target_bones)
        apply_world_pose(desired)
        low_before, high_before = bounds(target_meshes)
        floor_correction = -low_before.z
        for matrix in desired.values():
            matrix.translation.z += floor_correction
        apply_world_pose(desired)
        low, high = bounds(target_meshes)
        assert abs(low.z) <= .002, (clip, frame, low.z)
        error = max(((target_arm.matrix_world @ bone.matrix).translation-desired[bone.name].translation).length for bone in target_bones)
        errors.append(error)
        assert error < .002, (clip, frame, error)
        for bone in target_bones:
            quat = bone.rotation_quaternion
            previous = previous_quats.get(bone.name)
            if previous and quat.dot(previous) < 0:
                quat.negate()
            previous_quats[bone.name] = quat.copy()
            for path in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(data_path=path, frame=frame, group=bone.name)
        frame_rows.append({'frame':frame,'floorZ':round(low.z,6),'height':round(high.z-low.z,6),
                           'floorCorrection':round(floor_correction,6)})
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    slot = target_arm.animation_data.action_slot
    target_arm.animation_data.action = None
    track = target_arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 1, action)
    strip.action_slot = slot
    strip.action_frame_start, strip.action_frame_end = 1, end_frame
    strip.frame_start, strip.frame_end = 1, end_frame
    strip.extrapolation = 'NOTHING'
    track.mute = True
    created.append(track)
    report['clips'].append({'name':clip,'frames':end_frame,'duration':(end_frame-1)/source_fps,
                             'sourceAction':source_strip.action.name,'action':action.name,
                             'maxPoseHeadError':max(errors),'groundSamples':frame_rows})
    print(f'BAKED {clip}: {end_frame} frames; max error={max(errors):.8f}')

bpy.context.window.scene = target_scene
target_scene.name = 'PREP_CHARACTER_CYBERPUNK_REMY_RETARGET_20261022'
for track in created:
    for other in created:
        other.mute = other != track
    sample_frames = [1] if track.name == 'Idle' else [1,9,17,25]
    for frame in sample_frames:
        for view in ('front','side'):
            report['renders'].append(render_sample(track.name, frame, view))

for track in created:
    track.mute = False
target_arm.animation_data.action = None
target_scene.frame_end = 251
bpy.ops.object.select_all(action='DESELECT')
model_root = target_arm
while model_root.parent:
    model_root = model_root.parent
model_objects = [model_root, *model_root.children_recursive]
for obj in model_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = target_arm
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
result = bpy.ops.export_scene.gltf(filepath=str(OUTPUT),export_format='GLB',use_selection=True,use_active_scene=True,
                                 export_yup=True,export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',
                                 export_cameras=False,export_lights=False,export_extras=True)
assert 'FINISHED' in result
for track in created:
    track.mute = track.name != 'Idle'
target_scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(WORKING),compress=True)
report['status'] = 'baked-awaiting-independent-reimport-and-visual-review'
report['blend'] = {'path':str(WORKING),'sha256':sha256(WORKING),'bytes':WORKING.stat().st_size}
report['glb'] = {'path':str(OUTPUT),'sha256':sha256(OUTPUT),'bytes':OUTPUT.stat().st_size}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'report':str(REPORT),'glb':report['glb'],
                  'clips':[{'name':row['name'],'frames':row['frames']} for row in report['clips']]}))
