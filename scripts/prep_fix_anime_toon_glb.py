"""Create a Cycles-compatible derivative without the author's inverted outline hulls.

The author texture payload, skin weights, node indices and animation channels stay
byte-for-byte unchanged. Single-sided black hulls work in a glTF rasterizer, while
Cycles renders their backs and hides the colored surfaces. Never edit the source.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'frontend/public/assets/supplied/SUP_lowpoly_anime_character_cyberstyle.glb'
TARGET = ROOT / 'frontend/public/assets/supplied/SUP_lowpoly_anime_character_cyberstyle_Color_v2.glb'
REPORT = ROOT / 'reports/material_qa/anime_color_fix.json'


def read_glb(path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from('<III', data)
    assert magic == 0x46546C67 and version == 2 and total == len(data)
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    document = json.loads(data[20:20 + size])
    # Retain complete non-JSON chunks, including exact binary padding.
    return document, data[20 + size:], data


def triangles(document, active=False):
    indices = {node['mesh'] for node in document['nodes'] if 'mesh' in node} if active else range(len(document['meshes']))
    return sum(document['accessors'][p['indices']]['count'] // 3 for i in indices for p in document['meshes'][i]['primitives'])


def main():
    original, remaining_chunks, raw = read_glb(SOURCE)
    corrected = copy.deepcopy(original)
    black_materials = {
        i for i, material in enumerate(original.get('materials', []))
        if 'toon' in material.get('name', '').lower()
        and 'baseColorTexture' not in material.get('pbrMetallicRoughness', {})
        and material.get('pbrMetallicRoughness', {}).get('baseColorFactor', [1, 1, 1, 1])[:3] == [0, 0, 0]
        and not material.get('doubleSided', False)
    }
    hidden = []
    for index, node in enumerate(corrected['nodes']):
        if 'mesh' not in node:
            continue
        mesh = corrected['meshes'][node['mesh']]
        if mesh['primitives'] and all(p.get('material') in black_materials for p in mesh['primitives']):
            hidden.append({'nodeIndex': index, 'nodeName': node.get('name'), 'meshIndex': node['mesh'], 'meshName': mesh.get('name')})
            # Detaching a mesh leaves the node and all skin/animation indices intact.
            del node['mesh']
            # A mesh-less node has no skin to deform; skin resources remain intact.
            node.pop('skin', None)
    assert len(hidden) == 9, f'Unexpected hull count: {len(hidden)}'
    assert all('mesh' in node for node in corrected['nodes'] if 'skin' in node), 'A skin-bearing node must reference a mesh.'
    assert corrected['animations'] == original['animations']
    assert corrected['skins'] == original['skins']
    assert corrected['images'] == original['images']
    assert corrected['accessors'] == original['accessors']
    assert len(corrected['nodes']) == len(original['nodes'])
    encoded = json.dumps(corrected, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    encoded += b' ' * ((-len(encoded)) % 4)
    output = struct.pack('<III', 0x46546C67, 2, 20 + len(encoded) + len(remaining_chunks)) + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded + remaining_chunks
    if TARGET.exists():
        assert TARGET.read_bytes() == output, 'Existing derivative differs; refusing overwrite.'
    else:
        TARGET.write_bytes(output)
    reloaded, result_chunks, result_raw = read_glb(TARGET)
    assert result_chunks == remaining_chunks
    assert reloaded == corrected
    assert all('mesh' in node for node in reloaded['nodes'] if 'skin' in node)
    report = {
        'id': 'SUP_lowpoly_anime_character_cyberstyle',
        'input': str(SOURCE), 'output': str(TARGET),
        'url': '/assets/supplied/' + TARGET.name,
        'inputSha256': hashlib.sha256(raw).hexdigest(), 'sha256': hashlib.sha256(result_raw).hexdigest(),
        'bytes': len(result_raw), 'hiddenHullNodes': hidden,
        'trianglesBefore': triangles(original, True), 'triangles': triangles(reloaded, True),
        'activeMeshesBefore': sum('mesh' in n for n in original['nodes']),
        'activeMeshes': sum('mesh' in n for n in reloaded['nodes']),
        'skins': len(reloaded['skins']), 'nodeCount': len(reloaded['nodes']),
        'skinJointCount': len(reloaded['skins'][0]['joints']),
        'skinBearingNodes': sum('skin' in node for node in reloaded['nodes']),
        'skinWithoutMeshNodes': sum('skin' in node and 'mesh' not in node for node in reloaded['nodes']),
        'textures': len(reloaded['textures']), 'materials': len(reloaded['materials']),
        'blackHullMaterialNames': [original['materials'][index]['name'] for index in sorted(black_materials)],
        'animations': [{'name': a['name'], 'channels': len(a['channels'])} for a in reloaded['animations']],
        'unchanged': ['Binary payload and padding', 'Texture image descriptors and bytes', 'Skin/inverse bind matrices', 'Node indices and transforms', 'Animation channels/samplers', 'Mesh/accessor geometry data'],
        'modification': 'Detached nine single-sided black inverted toon hull meshes for Cycles compatibility; original author colors/textures and rig retained. Toon outlines are absent in this derivative.',
        'validation': 'GLB header/chunk lengths; JSON round trip; exact non-JSON payload; unchanged skins, animations, image/accessor metadata; every skin-bearing node references a mesh.',
        'blenderReimportValidated': False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
