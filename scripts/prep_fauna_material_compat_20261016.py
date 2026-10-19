"""Adapt five audited zero-specular legacy glTF materials for Three.js.

No Blender export, geometry processing, image transcoding or skin operation is
performed. Only the JSON material metadata and extension declarations change.
Every non-JSON GLB chunk is copied byte-for-byte. The five original public GLBs
and their catalog are retained in a separate checkpoint before any replacement.
Current delivery stays pending-material-qa until a new Blender import validates
the metadata-adapted file. Unknown input/output bytes cause a hard failure.
"""
import copy
import hashlib
import json
import math
import os
import struct
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE_ROOT = Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo')
CATALOG = ROOT / 'reports/fauna_catalog_entries_20261016.json'
BACKUP = ROOT / 'art/blender/checkpoints/FAUNA_LEGACY_SOURCE_20261016'
CATALOG_BACKUP = BACKUP / 'fauna_catalog_entries_before_material_compat_20261016.json'
REPORT = ROOT / 'reports/FAUNA_MATERIAL_COMPAT_20261016.json'
OWNER = 'prep_fauna_material_compat_20261016_v1'
LEGACY = 'KHR_materials_pbrSpecularGlossiness'
SPECULAR = 'KHR_materials_specular'
EXTRA = 'PREPARATORIO_material_compat_20261016'
KNOWN = {
    'FAUNA_FOX_20261016': '6e0615dc8fec710aaa627fe03345c194c52bd0bb7ed23b2d784a54c0335fd7dc',
    'FAUNA_LIONESS_20261016': '16b309a73aa72b8a8510f4cd2a4803208d6d19ffdcba1160d8bc9fff7b76c350',
    'FAUNA_RABBIT_20261016': '6329c42867723e259615d92c307d10fd3133ece4e35864f02d7750cfe3b38e3d',
    'FAUNA_WOLF_20261016': '4bbe8043b30c9f1abb55eaf09313ef430c8f22a9c7d1b9e375d496e511222178',
    'FAUNA_HORSE_20261016': '743fd70ec937dde1aa550afde17eeb506ca538933e291eca41d2fa8d5ffb20ea',
}
MEGALODON_ID = 'FAUNA_MEGALODON_20261016'
MEGALODON_SHA = '3c708fae2dc95527c59d4ede869095c44d08d59c99f745c15450d95f6178a216'
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return digest(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii'))


def parse_glb(data):
    assert len(data) >= 20
    magic, version, total = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and total == len(data)
    chunks = []
    offset = 12
    while offset < len(data):
        assert offset + 8 <= len(data)
        length, kind = struct.unpack_from('<II', data, offset)
        offset += 8
        assert length % 4 == 0 and offset + length <= len(data)
        chunks.append((kind, data[offset:offset + length]))
        offset += length
    assert offset == len(data) and chunks and chunks[0][0] == JSON_CHUNK
    assert sum(kind == JSON_CHUNK for kind, _ in chunks) == 1
    assert sum(kind == BIN_CHUNK for kind, _ in chunks) == 1
    doc = json.loads(chunks[0][1])
    assert doc.get('asset', {}).get('version') == '2.0'
    return doc, chunks


def package_glb(doc, chunks):
    payload = json.dumps(doc, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    payload += b' ' * (-len(payload) % 4)
    new_chunks = [(JSON_CHUNK, payload)] + chunks[1:]
    body = b''.join(struct.pack('<II', len(chunk), kind) + chunk for kind, chunk in new_chunks)
    return struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body


def adapt(original_data, identity, original_sha):
    assert digest(original_data) == original_sha
    original, chunks = parse_glb(original_data)
    doc = copy.deepcopy(original)
    assert LEGACY in doc.get('extensionsRequired', []) and LEGACY in doc.get('extensionsUsed', [])
    assert all('uri' not in image for image in doc.get('images', [])), 'Unexpected external image'
    assert all('uri' not in buffer for buffer in doc.get('buffers', [])), 'Unexpected external buffer'
    materials = []
    for index, material in enumerate(doc.get('materials', [])):
        assert 'pbrMetallicRoughness' not in material, 'Ambiguous pre-existing core material'
        extensions = material.get('extensions', {})
        assert LEGACY in extensions and SPECULAR not in extensions
        workflow = extensions[LEGACY]
        assert set(workflow) <= {'diffuseFactor', 'diffuseTexture', 'specularFactor', 'glossinessFactor'}, 'Unsupported legacy texture/parameter: no approximation allowed'
        assert workflow.get('specularFactor') == [0, 0, 0], 'Only exactly zero-specular legacy inputs are supported'
        assert 'specularGlossinessTexture' not in workflow
        color = workflow.get('diffuseFactor', [1, 1, 1, 1])
        gloss = workflow.get('glossinessFactor', 1)
        assert len(color) == 4 and all(isinstance(x, (float, int)) and math.isfinite(x) and 0 <= x <= 1 for x in color)
        assert isinstance(gloss, (float, int)) and math.isfinite(gloss) and 0 <= gloss <= 1
        core = {'baseColorFactor': copy.deepcopy(color), 'metallicFactor': 0.0, 'roughnessFactor': 1.0 - gloss}
        if 'diffuseTexture' in workflow:
            core['baseColorTexture'] = copy.deepcopy(workflow['diffuseTexture'])
            assert 0 <= core['baseColorTexture']['index'] < len(doc['textures'])
        material['pbrMetallicRoughness'] = core
        material.setdefault('extras', {})
        assert isinstance(material['extras'], dict) and EXTRA not in material['extras']
        material['extras'][EXTRA] = {'owner': OWNER, 'legacyExtension': LEGACY,
            'originalWorkflow': copy.deepcopy(workflow), 'originalGLBSha256': original_sha,
            'method': 'Exactly zero source specular; diffuse factor/texture preserved as core baseColor, metallic=0, roughness=1-glossiness, KHR_materials_specular.specularFactor=0; alpha and other material fields unchanged'}
        del extensions[LEGACY]
        extensions[SPECULAR] = {'specularFactor': 0.0}
        materials.append({'index': index, 'name': material.get('name'), 'originalWorkflow': copy.deepcopy(workflow),
            'corePBR': copy.deepcopy(core), 'zeroSpecularExtension': copy.deepcopy(extensions[SPECULAR]),
            'alphaModePreserved': material.get('alphaMode', 'OPAQUE'),
            'alphaCutoffPreserved': material.get('alphaCutoff'), 'doubleSidedPreserved': material.get('doubleSided', False)})
    assert materials
    for declaration in ('extensionsUsed', 'extensionsRequired'):
        values = [item for item in doc.get(declaration, []) if item != LEGACY]
        if SPECULAR not in values:
            values.append(SPECULAR)
        doc[declaration] = values
    extras = doc['asset'].setdefault('extras', {})
    assert isinstance(extras, dict) and EXTRA not in extras
    extras[EXTRA] = {'owner': OWNER, 'sourceGLBSha256': original_sha, 'assetId': identity,
        'sourceWorkflowRetainedInMaterialExtras': True, 'geometrySkinAnimationAndEmbeddedImagesUnmodified': True,
        'purpose': 'Core PBR and supported zero-specular metadata for local Three.js GLTFLoader; original authorship/license/source fields retained'}
    converted_data = package_glb(doc, chunks)
    converted, converted_chunks = parse_glb(converted_data)
    assert converted_chunks[1:] == chunks[1:], 'A non-JSON GLB chunk changed'
    unchanged_fields = sorted(set(original) - {'materials', 'extensionsUsed', 'extensionsRequired', 'asset'})
    assert all(converted.get(key) == original[key] for key in unchanged_fields), 'Non-material JSON field changed'
    for key, value in original['asset'].items():
        if key != 'extras':
            assert converted['asset'][key] == value
    assert all(converted['asset']['extras'][key] == value for key, value in original['asset'].get('extras', {}).items()), 'Source attribution changed'
    for old, new in zip(original['materials'], converted['materials']):
        allowed = {'pbrMetallicRoughness', 'extensions', 'extras'}
        assert all(new[key] == value for key, value in old.items() if key not in allowed)
        assert all(new['extras'][key] == value for key, value in old.get('extras', {}).items())
        assert all(new['extensions'][key] == value for key, value in old.get('extensions', {}).items() if key != LEGACY)
        assert LEGACY not in new.get('extensions', {}) and new['extensions'][SPECULAR]['specularFactor'] == 0
    preserved = {key: canonical_digest(original.get(key)) for key in
        ('nodes', 'skins', 'animations', 'accessors', 'bufferViews', 'buffers', 'meshes', 'textures', 'images', 'samplers', 'scenes', 'scene')}
    assert all(canonical_digest(converted.get(key)) == checksum for key, checksum in preserved.items())
    bin_payload = next(payload for kind, payload in chunks if kind == BIN_CHUNK)
    evidence = {'id': identity, 'originalSha256': original_sha, 'convertedSha256': digest(converted_data),
        'originalBytes': len(original_data), 'convertedBytes': len(converted_data),
        'binaryChunkSha256Before': digest(bin_payload), 'binaryChunkSha256After': digest(next(payload for kind, payload in converted_chunks if kind == BIN_CHUNK)),
        'binaryChunkBytes': len(bin_payload), 'allNonJsonChunksByteIdentical': True,
        'unchangedTopLevelFields': unchanged_fields, 'preservedJSONFieldHashes': preserved,
        'nodesSkinsAnimationsAccessorsBufferViewsUnchanged': True, 'embeddedImagesByteIdentical': True,
        'sourceAttributionUnchanged': True, 'materials': materials,
        'extensionsUsedBefore': original.get('extensionsUsed'), 'extensionsUsedAfter': converted.get('extensionsUsed'),
        'extensionsRequiredBefore': original.get('extensionsRequired'), 'extensionsRequiredAfter': converted.get('extensionsRequired'),
        'blenderMaterialQA': 'pending'}
    return converted_data, evidence


def exclusive_copy(data, path):
    if path.exists():
        assert path.read_bytes() == data, 'Preserved checkpoint differs: ' + str(path)
        return
    with path.open('xb') as stream:
        stream.write(data)
    assert path.read_bytes() == data


def atomic_write(data, path):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temp.open('xb') as stream:
        stream.write(data)
    os.replace(str(temp), str(path))
    assert path.read_bytes() == data


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def main():
    catalog_bytes = CATALOG.read_bytes()
    current = json.loads(catalog_bytes)
    by_id = {record['id']: record for record in current}
    assert len(by_id) == len(current) and set(KNOWN) <= set(by_id)
    assert MEGALODON_ID in by_id
    for ident, checksum in KNOWN.items():
        assert by_id[ident]['sourceSha256'] == checksum
    untouched = copy.deepcopy(by_id[MEGALODON_ID])
    megalodon_path = ROOT / 'frontend/public' / untouched['url'].lstrip('/')
    assert digest(megalodon_path.read_bytes()) == untouched['sha256'] == MEGALODON_SHA
    if REPORT.exists():
        assert json.loads(REPORT.read_text('utf-8')).get('owner') == OWNER, 'Unknown existing compatibility report'
    BACKUP.mkdir(parents=True, exist_ok=True)
    if CATALOG_BACKUP.exists():
        original_catalog = json.loads(CATALOG_BACKUP.read_bytes())
    else:
        assert all(by_id[ident]['sha256'] == checksum for ident, checksum in KNOWN.items()), 'Initial catalog already differs from known originals'
        exclusive_copy(catalog_bytes, CATALOG_BACKUP)
        original_catalog = copy.deepcopy(current)
    original_by_id = {record['id']: record for record in original_catalog}
    assert all(original_by_id[ident]['sha256'] == checksum == original_by_id[ident]['sourceSha256'] for ident, checksum in KNOWN.items())
    assert original_by_id[MEGALODON_ID] == untouched, 'Megalodon catalog changed unexpectedly'
    prepared = []
    # Complete preflight and backups for all five files before the first public
    # replacement. Deterministic expected output bytes also make recovery safe.
    for ident, checksum in KNOWN.items():
        record = by_id[ident]
        public = ROOT / 'frontend/public' / record['url'].lstrip('/')
        assert public.parent.resolve() == (ROOT / 'frontend/public/assets/additions20261016').resolve()
        assert public.name == ident + '.glb'
        saved = BACKUP / public.name
        supplied = SOURCE_ROOT / record['sourceRelative']
        supplied_bytes = supplied.read_bytes()
        assert digest(supplied_bytes) == checksum, 'Downloaded source differs: ' + ident
        public_bytes = public.read_bytes()
        if saved.exists():
            original_bytes = saved.read_bytes()
            assert digest(original_bytes) == checksum
        else:
            assert digest(public_bytes) == checksum, 'Public input is not the known original: ' + ident
            exclusive_copy(public_bytes, saved)
            original_bytes = public_bytes
        converted_bytes, evidence = adapt(original_bytes, ident, checksum)
        current_sha = digest(public_bytes)
        assert current_sha in {checksum, evidence['convertedSha256']}, 'Unknown edited public file: ' + ident
        assert record['sha256'] in {checksum, evidence['convertedSha256']}, 'Unknown catalog delivery hash'
        evidence.update({'url': record['url'], 'originalCheckpoint': str(saved), 'sourceRelative': record['sourceRelative'],
                         'sourceFileSha256VerifiedUnchanged': checksum})
        prepared.append((ident, public, converted_bytes, evidence, current_sha))
    # Exact idempotent reuse also preserves a later root-agent QA promotion.
    already_done = all(current_sha == evidence['convertedSha256'] and by_id[ident]['sha256'] == evidence['convertedSha256']
                       for ident, _, _, evidence, current_sha in prepared)
    if already_done and REPORT.exists():
        old_report = json.loads(REPORT.read_text('utf-8'))
        assert {r['id']: r['convertedSha256'] for r in old_report['assets']} == {ident: evidence['convertedSha256'] for ident, _, _, evidence, _ in prepared}
        print(json.dumps({'owner': OWNER, 'status': 'reused-existing-compatible-bytes', 'assets': len(prepared),
                          'catalogStatusPreserved': True, 'blenderMaterialQA': 'See current catalog and root QA report'}))
        return
    for ident, public, converted_bytes, evidence, current_sha in prepared:
        assert digest(public.read_bytes()) == current_sha, 'Public file changed after preflight'
        if current_sha != evidence['convertedSha256']:
            atomic_write(converted_bytes, public)
        record = by_id[ident]
        record.update({'sha256': evidence['convertedSha256'], 'bytes': evidence['convertedBytes'],
            'status': 'pending-material-qa', 'reimportValidated': False,
            'originalReimportValidated': original_by_id[ident].get('reimportValidated', False),
            'modifications': 'GLB JSON material metadata adapted from audited zero-specular KHR_materials_pbrSpecularGlossiness to core PBR plus supported KHR_materials_specular.specularFactor=0. Original BIN chunk, images, mesh attributes, node transforms, inverse binds, weights, skeletons and clips are byte-identical; original alpha modes/cutoffs, double-sided flags and attribution retained. No Blender skin re-export.',
            'deliveryMethod': 'BIN-skins-animations-images-unmodified; zero-specular-PBR-material-metadata-adapted; pending-independent-Blender-material-QA',
            'materialCompatibility': {'owner': OWNER, 'legacyExtensionRemoved': LEGACY, 'supportedZeroSpecularExtension': SPECULAR,
                'corePBRBaseColorTextureFromOriginalDiffuse': True, 'binaryChunkSha256': evidence['binaryChunkSha256After'],
                'materialCount': len(evidence['materials']), 'blenderMaterialQA': 'pending',
                'originalGLBCheckpoint': str(BACKUP / public.name), 'sourceAttributionPreserved': True}})
    assert by_id[MEGALODON_ID] == untouched and digest(megalodon_path.read_bytes()) == MEGALODON_SHA
    # Other catalog rows are unchanged; only the five explicitly allowed IDs can
    # differ from the catalog read at the beginning of this invocation.
    for original in json.loads(catalog_bytes):
        if original['id'] not in KNOWN:
            assert by_id[original['id']] == original
    assert CATALOG.read_bytes() == catalog_bytes, 'Catalog changed concurrently; preserve it and inspect partial output'
    updated_catalog_bytes = json_bytes(current)
    report = {'owner': OWNER, 'status': 'metadata-validated-pending-blender-material-qa',
        'timeLocal': datetime.now().astimezone().isoformat(), 'assetsModified': len(prepared),
        'catalogBeforeCheckpoint': str(CATALOG_BACKUP), 'catalogBeforeCheckpointSha256': digest(CATALOG_BACKUP.read_bytes()),
        'catalogAfterSha256': digest(updated_catalog_bytes), 'method': 'JSON material metadata only; all non-JSON GLB chunks byte-identical',
        'preconditions': 'Five hardcoded audited source hashes; every material specularFactor exactly [0,0,0]; no specularGlossinessTexture or unknown legacy parameters',
        'renderValidation': 'Not yet performed for the adapted files; root agent must import and render these five deliveries in Blender before promotion',
        'megalodonUnmodified': {'id': MEGALODON_ID, 'sha256': MEGALODON_SHA, 'catalogRowUnchanged': True},
        'assets': [evidence for _, _, _, evidence, _ in prepared]}
    atomic_write(updated_catalog_bytes, CATALOG)
    atomic_write(json_bytes(report), REPORT)
    print(json.dumps({'owner': OWNER, 'status': report['status'], 'assetsModified': len(prepared),
        'allBinaryChunksByteIdentical': True, 'megalodonUnmodified': True,
        'report': str(REPORT), 'independentBlenderMaterialQARequired': True}))


if __name__ == '__main__':
    main()
