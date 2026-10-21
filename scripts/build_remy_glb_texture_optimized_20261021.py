"""Resize only embedded PNG payloads while preserving every other GLB buffer view.

This avoids Blender exporter normalization of animation time samples and vertex
splits. The source files are read-only and the runtime variants are rebuilt.
"""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / 'frontend/public/assets/characters'
OUT = CHARACTERS / 'runtime'
REPORT = ROOT / 'reports/AVATAR_RUNTIME_OPTIMIZATION_20261021.json'
OUT.mkdir(parents=True, exist_ok=True)

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

TARGETS = [
    {
        'id': 'CHR_Remy_Mixamo_Web_20261021',
        'source': CHARACTERS / 'CHR_Remy_Mixamo_20261005.glb',
        'target': OUT / 'CHR_Remy_Mixamo_Web_20261021.glb',
    },
    {
        'id': 'CHR_Remy_Senac_Uniform_Web_20261021',
        'source': CHARACTERS / 'CHR_Remy_Senac_Uniform_20261013.glb',
        'target': OUT / 'CHR_Remy_Senac_Uniform_Web_20261021.glb',
    },
]


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def image_limit(name):
    value = name.lower()
    if value in {'nursing-crest', 'senac-logo'}:
        return 512
    if 'body' in value and ('diffuse' in value or 'normal' in value or 'opacity' in value):
        return 1024
    if 'diffuse' in value or 'opacity' in value:
        return 1024
    return 512


def read_glb(path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', raw, 0)
    if magic != b'glTF' or version != 2 or total != len(raw):
        raise ValueError(f'Invalid GLB header: {path}')
    offset = 12
    chunks = {}
    while offset < total:
        length, kind = struct.unpack_from('<II', raw, offset)
        offset += 8
        chunks[kind] = raw[offset:offset + length]
        offset += length
    document = json.loads(chunks[JSON_CHUNK].decode('utf-8').rstrip('\x00 '))
    return document, chunks[BIN_CHUNK]


def resize_png(payload, limit):
    with Image.open(BytesIO(payload)) as source:
        source.load()
        before = source.size
        longest = max(before)
        if longest <= limit:
            return payload, before, before
        scale = limit / longest
        after = (max(1, round(before[0] * scale)), max(1, round(before[1] * scale)))
        resized = source.resize(after, Image.Resampling.LANCZOS)
        output = BytesIO()
        resized.save(output, format='PNG', optimize=True, compress_level=9)
        return output.getvalue(), before, after


def write_glb(path, document, binary):
    json_bytes = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    json_bytes += b' ' * ((-len(json_bytes)) % 4)
    binary += b'\x00' * ((-len(binary)) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    payload = bytearray(struct.pack('<4sII', b'glTF', 2, total))
    payload.extend(struct.pack('<II', len(json_bytes), JSON_CHUNK))
    payload.extend(json_bytes)
    payload.extend(struct.pack('<II', len(binary), BIN_CHUNK))
    payload.extend(binary)
    path.write_bytes(payload)


records = []
for item in TARGETS:
    source_hash = sha_file(item['source'])
    document, binary = read_glb(item['source'])
    image_views = {}
    image_records = []
    for image in document.get('images', []):
        if image.get('mimeType') != 'image/png' or 'bufferView' not in image:
            continue
        view_index = image['bufferView']
        view = document['bufferViews'][view_index]
        start = view.get('byteOffset', 0)
        end = start + view['byteLength']
        converted, before, after = resize_png(binary[start:end], image_limit(image.get('name', '')))
        image_views[view_index] = converted
        image_records.append({
            'name': image.get('name', f'image_{view_index}'),
            'bufferView': view_index,
            'before': list(before),
            'after': list(after),
            'beforeBytes': end - start,
            'afterBytes': len(converted),
            'limit': image_limit(image.get('name', '')),
        })

    rebuilt = bytearray()
    immutable_views = []
    for index, view in enumerate(document.get('bufferViews', [])):
        start = view.get('byteOffset', 0)
        end = start + view['byteLength']
        old_payload = binary[start:end]
        new_payload = image_views.get(index, old_payload)
        rebuilt.extend(b'\x00' * ((-len(rebuilt)) % 4))
        view['byteOffset'] = len(rebuilt)
        view['byteLength'] = len(new_payload)
        rebuilt.extend(new_payload)
        if index not in image_views:
            immutable_views.append({
                'index': index,
                'bytes': len(old_payload),
                'sha256': sha_bytes(old_payload),
            })
    document['buffers'][0]['byteLength'] = len(rebuilt)
    write_glb(item['target'], document, bytes(rebuilt))

    # Reopen and prove that every non-image binary view remains byte-identical.
    target_document, target_binary = read_glb(item['target'])
    for expected in immutable_views:
        view = target_document['bufferViews'][expected['index']]
        start = view.get('byteOffset', 0)
        payload = target_binary[start:start + view['byteLength']]
        if len(payload) != expected['bytes'] or sha_bytes(payload) != expected['sha256']:
            raise AssertionError(f"Non-image bufferView changed: {item['id']} #{expected['index']}")
    if sha_file(item['source']) != source_hash:
        raise AssertionError(f"Source changed: {item['source']}")

    records.append({
        'id': item['id'],
        'method': 'Embedded PNG bufferViews replaced; all non-image bufferViews verified byte-identical.',
        'source': str(item['source']),
        'sourceBytes': item['source'].stat().st_size,
        'sourceSha256': source_hash,
        'target': str(item['target']),
        'targetBytes': item['target'].stat().st_size,
        'targetSha256': sha_file(item['target']),
        'byteReductionPercent': round((1 - item['target'].stat().st_size / item['source'].stat().st_size) * 100, 2),
        'nonImageBufferViewsVerified': len(immutable_views),
        'images': image_records,
        'animations': [
            {'name': animation.get('name'), 'channels': len(animation.get('channels', [])), 'samplers': len(animation.get('samplers', []))}
            for animation in document.get('animations', [])
        ],
    })

REPORT.write_text(json.dumps({
    'date': '2026-10-21',
    'passed': True,
    'sourceFilesPreserved': True,
    'geometryDecimated': False,
    'armatureApplied': False,
    'method': 'Direct GLB texture payload optimization, followed by immutable buffer-view verification.',
    'records': records,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('AVATAR_GLB_TEXTURE_OPTIMIZED ' + json.dumps([
    {
        'id': record['id'],
        'sourceBytes': record['sourceBytes'],
        'targetBytes': record['targetBytes'],
        'reduction': record['byteReductionPercent'],
        'sha256': record['targetSha256'],
    }
    for record in records
], ensure_ascii=False))
