"""Create reversible WebGL runtime variants of Remy and the SENAC uniform.

Geometry, armature, weights, actions and source files stay unchanged. Only the
embedded image copies are resized before exporting new GLB files.
"""
import bpy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / 'frontend/public/assets/characters'
OUT = CHARACTERS / 'runtime'
BLEND_OUT = ROOT / 'art/blender/runtime'
REPORT = ROOT / 'reports/AVATAR_RUNTIME_OPTIMIZATION_20261021.json'
OUT.mkdir(parents=True, exist_ok=True)
BLEND_OUT.mkdir(parents=True, exist_ok=True)

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
targets = [
    {
        'id': 'CHR_Remy_Mixamo_Web_20261021',
        'source': CHARACTERS / 'CHR_Remy_Mixamo_20261005.glb',
        'target': OUT / 'CHR_Remy_Mixamo_Web_20261021.glb',
        'blend': BLEND_OUT / 'CHR_Remy_Mixamo_Web_20261021.blend',
    },
    {
        'id': 'CHR_Remy_Senac_Uniform_Web_20261021',
        'source': CHARACTERS / 'CHR_Remy_Senac_Uniform_20261013.glb',
        'target': OUT / 'CHR_Remy_Senac_Uniform_Web_20261021.glb',
        'blend': BLEND_OUT / 'CHR_Remy_Senac_Uniform_Web_20261021.blend',
    },
]

def image_limit(name):
    value = name.lower()
    if 'body' in value and ('diffuse' in value or 'normal' in value or 'opacity' in value):
        return 1024
    if 'diffuse' in value or 'opacity' in value:
        return 1024
    return 512

records = []
source_hashes = {item['id']: sha(item['source']) for item in targets}
for item in targets:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(item['source']))
    scene = bpy.context.scene
    objects = list(scene.objects)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    armatures = [obj for obj in objects if obj.type == 'ARMATURE']
    assert len(armatures) == 1 and len(armatures[0].data.bones) == 55
    images = []
    for image in bpy.data.images:
        if image.name in {'Render Result', 'Viewer Node'} or image.size[0] <= 0 or image.size[1] <= 0:
            continue
        before = list(image.size)
        limit = image_limit(image.name)
        longest = max(before)
        if longest > limit:
            scale = limit / longest
            width = max(1, round(before[0] * scale))
            height = max(1, round(before[1] * scale))
            image.scale(width, height)
        images.append({
            'name': image.name,
            'before': before,
            'after': list(image.size),
            'channels': image.channels,
            'fileFormat': image.file_format,
            'colorspace': image.colorspace_settings.name,
            'limit': limit,
        })
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armatures[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(item['blend']), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(item['target']),
        export_format='GLB',
        use_selection=True,
        export_yup=True,
        export_animations=True,
        export_skins=True,
        export_animation_mode='NLA_TRACKS',
        export_lights=False,
        export_cameras=False,
        export_extras=True,
        export_image_format='AUTO',
    )
    assert sha(item['source']) == source_hashes[item['id']]
    triangles = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in meshes)
    tracks = [track.name for track in armatures[0].animation_data.nla_tracks] if armatures[0].animation_data else []
    records.append({
        'id': item['id'],
        'source': str(item['source']),
        'sourceBytes': item['source'].stat().st_size,
        'sourceSha256': source_hashes[item['id']],
        'target': str(item['target']),
        'targetBytes': item['target'].stat().st_size,
        'targetSha256': sha(item['target']),
        'blend': str(item['blend']),
        'meshes': len(meshes),
        'triangles': triangles,
        'bones': len(armatures[0].data.bones),
        'tracks': tracks,
        'images': images,
    })

report = {
    'date': '2026-10-21',
    'method': 'New runtime copies exported by Blender after resizing embedded images only.',
    'sourceFilesPreserved': True,
    'geometryDecimated': False,
    'armatureApplied': False,
    'records': records,
    'limits': [
        'Visual comparison and independent reimport validation are still required before the game selects these files.',
        'The optimization does not complete pending artistic posture or cloth fitting work.',
    ],
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('AVATAR_RUNTIME_OPTIMIZED ' + json.dumps({
    'files': [{'id': r['id'], 'sourceBytes': r['sourceBytes'], 'targetBytes': r['targetBytes'], 'sha256': r['targetSha256']} for r in records]
}, ensure_ascii=False))
