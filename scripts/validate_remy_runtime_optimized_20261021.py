"""Independently reimport original and optimized Remy GLBs and compare structure."""
import bpy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / 'frontend/public/assets/characters'
REPORT = ROOT / 'reports/AVATAR_RUNTIME_VALIDATION_20261021.json'

PAIRS = [
    (
        'body',
        CHARACTERS / 'CHR_Remy_Mixamo_20261005.glb',
        CHARACTERS / 'runtime/CHR_Remy_Mixamo_Web_20261021.glb',
    ),
    (
        'senac_uniform',
        CHARACTERS / 'CHR_Remy_Senac_Uniform_20261013.glb',
        CHARACTERS / 'runtime/CHR_Remy_Senac_Uniform_Web_20261021.glb',
    ),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_channel_count(action):
    """Support both legacy and Blender 4.4+ layered actions."""
    if hasattr(action, 'fcurves'):
        return len(action.fcurves)
    total = 0
    for layer in getattr(action, 'layers', []):
        for strip in getattr(layer, 'strips', []):
            for channelbag in getattr(strip, 'channelbags', []):
                total += len(channelbag.fcurves)
    return total


def inspect(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = list(bpy.context.scene.objects)
    meshes = sorted((obj for obj in objects if obj.type == 'MESH'), key=lambda obj: obj.name)
    armatures = [obj for obj in objects if obj.type == 'ARMATURE']
    if len(armatures) != 1:
        raise AssertionError(f'{path}: expected one armature, found {len(armatures)}')
    armature = armatures[0]
    tracks = []
    if armature.animation_data:
        for track in armature.animation_data.nla_tracks:
            strips = []
            for strip in track.strips:
                action = strip.action
                strips.append({
                    'name': strip.name,
                    'action': action.name if action else None,
                    'frameStart': strip.frame_start,
                    'frameEnd': strip.frame_end,
                    'channels': action_channel_count(action) if action else 0,
                })
            tracks.append({'name': track.name, 'strips': strips})
    images = []
    for image in sorted(bpy.data.images, key=lambda entry: entry.name):
        if image.name in {'Render Result', 'Viewer Node'} or not image.has_data:
            continue
        images.append({'name': image.name, 'size': list(image.size), 'channels': image.channels})
    return {
        'path': str(path),
        'bytes': path.stat().st_size,
        'sha256': sha(path),
        'objects': len(objects),
        'meshCount': len(meshes),
        'meshNames': [obj.name for obj in meshes],
        'meshVertexCounts': {obj.name: len(obj.data.vertices) for obj in meshes},
        'triangles': sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in meshes),
        'armature': armature.name,
        'boneCount': len(armature.data.bones),
        'boneNames': [bone.name for bone in armature.data.bones],
        'tracks': tracks,
        'images': images,
    }


comparisons = []
all_passed = True
for label, source_path, target_path in PAIRS:
    source = inspect(source_path)
    target = inspect(target_path)
    checks = {
        'objectCount': source['objects'] == target['objects'],
        'meshCount': source['meshCount'] == target['meshCount'],
        'meshNames': source['meshNames'] == target['meshNames'],
        'meshVertexCounts': source['meshVertexCounts'] == target['meshVertexCounts'],
        'triangles': source['triangles'] == target['triangles'],
        'boneCount55': source['boneCount'] == target['boneCount'] == 55,
        'boneNames': source['boneNames'] == target['boneNames'],
        'trackNames': [t['name'] for t in source['tracks']] == [t['name'] for t in target['tracks']],
        'trackDurations': [
            [(s['frameStart'], s['frameEnd'], s['channels']) for s in t['strips']]
            for t in source['tracks']
        ] == [
            [(s['frameStart'], s['frameEnd'], s['channels']) for s in t['strips']]
            for t in target['tracks']
        ],
        'sourceDistinctFromTarget': source['sha256'] != target['sha256'],
        'targetSmaller': target['bytes'] < source['bytes'],
    }
    passed = all(checks.values())
    all_passed = all_passed and passed
    comparisons.append({
        'label': label,
        'passed': passed,
        'checks': checks,
        'source': source,
        'target': target,
        'byteReductionPercent': round((1 - target['bytes'] / source['bytes']) * 100, 2),
    })

report = {
    'date': '2026-10-21',
    'passed': all_passed,
    'method': 'Fresh Blender 5.2.2 reimport of every original and optimized GLB.',
    'comparisons': comparisons,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('AVATAR_RUNTIME_VALIDATION ' + json.dumps({
    'passed': all_passed,
    'comparisons': [
        {
            'label': comparison['label'],
            'passed': comparison['passed'],
            'reduction': comparison['byteReductionPercent'],
            'checks': comparison['checks'],
        }
        for comparison in comparisons
    ],
}, ensure_ascii=False))
if not all_passed:
    raise SystemExit(1)
