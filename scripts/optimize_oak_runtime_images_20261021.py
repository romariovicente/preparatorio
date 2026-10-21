"""Reduce only embedded oak textures; preserve every non-image GLB buffer view."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'frontend/public/assets/environment/runtime/ENV_Oak_Small_001_LOD0_20261021.glb'
REPORT = ROOT / 'reports/OAK_RUNTIME_20261021.json'
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_glb(path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', raw, 0)
    if (magic, version, total) != (b'glTF', 2, len(raw)):
        raise ValueError('Invalid GLB')
    chunks = {}
    offset = 12
    while offset < total:
        length, kind = struct.unpack_from('<II', raw, offset)
        offset += 8
        chunks[kind] = raw[offset:offset + length]
        offset += length
    document = json.loads(chunks[JSON_CHUNK].decode('utf-8').rstrip('\x00 '))
    return document, chunks[BIN_CHUNK]


document, binary = read_glb(TARGET)
replacements = {}
images = []
for image in document.get('images', []):
    view_index = image['bufferView']
    view = document['bufferViews'][view_index]
    start = view.get('byteOffset', 0)
    original = binary[start:start + view['byteLength']]
    with Image.open(BytesIO(original)) as opened:
        opened.load()
        before = opened.size
        scale = min(1, 1024 / max(before))
        after = (max(1, round(before[0] * scale)), max(1, round(before[1] * scale)))
        resized = opened if after == before else opened.resize(after, Image.Resampling.LANCZOS)
        out = BytesIO()
        if image.get('mimeType') == 'image/jpeg':
            resized.convert('RGB').save(out, format='JPEG', quality=86, optimize=True, progressive=True)
        else:
            resized.save(out, format='PNG', optimize=True, compress_level=9)
        replacement = out.getvalue()
    replacements[view_index] = replacement
    images.append({'name': image.get('name'), 'before': list(before), 'after': list(after),
                   'beforeBytes': len(original), 'afterBytes': len(replacement)})

rebuilt = bytearray()
immutable = []
for index, view in enumerate(document['bufferViews']):
    start = view.get('byteOffset', 0)
    original = binary[start:start + view['byteLength']]
    payload = replacements.get(index, original)
    rebuilt.extend(b'\x00' * ((-len(rebuilt)) % 4))
    view['byteOffset'] = len(rebuilt)
    view['byteLength'] = len(payload)
    rebuilt.extend(payload)
    if index not in replacements:
        immutable.append((index, len(original), digest(original)))
document['buffers'][0]['byteLength'] = len(rebuilt)

json_bytes = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
json_bytes += b' ' * ((-len(json_bytes)) % 4)
binary_bytes = bytes(rebuilt) + b'\x00' * ((-len(rebuilt)) % 4)
total = 12 + 8 + len(json_bytes) + 8 + len(binary_bytes)
output = bytearray(struct.pack('<4sII', b'glTF', 2, total))
output.extend(struct.pack('<II', len(json_bytes), JSON_CHUNK)); output.extend(json_bytes)
output.extend(struct.pack('<II', len(binary_bytes), BIN_CHUNK)); output.extend(binary_bytes)
TARGET.write_bytes(output)

check_document, check_binary = read_glb(TARGET)
for index, length, sha in immutable:
    view = check_document['bufferViews'][index]
    start = view.get('byteOffset', 0)
    payload = check_binary[start:start + view['byteLength']]
    if len(payload) != length or digest(payload) != sha:
        raise AssertionError(f'Non-image buffer view changed: {index}')

report = json.loads(REPORT.read_text(encoding='utf-8'))
report.update({
    'bytes': TARGET.stat().st_size,
    'sha256': digest(TARGET.read_bytes()),
    'textureOptimization': {
        'maxDimension': 1024,
        'images': images,
        'nonImageBufferViewsVerified': len(immutable),
    },
    'method': 'One authored LOD0 hierarchy extracted in Blender; embedded images capped at 1024 px; all non-image GLB buffer views verified byte-identical; source preserved.',
})
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('OAK_TEXTURES_OPTIMIZED ' + json.dumps({'bytes': report['bytes'], 'sha256': report['sha256'], 'images': images}, ensure_ascii=False))
