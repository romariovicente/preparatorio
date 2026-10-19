from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo')
inventory = json.loads((ROOT / 'reports/supplied_assets_inventory.json').read_text(encoding='utf-8'))
reports = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'reports/supplied').glob('*.json'))]
inventory_paths = {str(Path(i['path'])).casefold(): i for i in inventory}
for entry in inventory:
    for p in entry.get('objFiles', []):
        inventory_paths[str(Path(p)).casefold()] = entry
old_files = json.loads((ROOT / 'reports/all_source_files_20261001.json').read_text(encoding='utf-8'))
old_relatives = {x['relative'].casefold(): x for x in old_files}
all_files = []
pending_models = []
new_files = []
changed_files = []
current_hashes = defaultdict(list)
source_glb_warnings = []

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

for p in sorted(SOURCE.rglob('*')):
    if not p.is_file():
        continue
    relative = str(p.relative_to(SOURCE))
    stat = p.stat()
    record = {'relative': relative, 'bytes': stat.st_size, 'extension': p.suffix.lower(), 'modified': stat.st_mtime}
    prior = old_relatives.get(relative.casefold())
    if prior is None:
        new_files.append(record)
    elif prior.get('bytes') != stat.st_size:
        changed_files.append(record)
    if p.suffix.lower() in {'.glb', '.gltf', '.obj', '.fbx', '.blend', '.stl', '.dae'}:
        record['sha256'] = sha(p)
        current_hashes[record['sha256']].append(relative)
        indexed = inventory_paths.get(str(p).casefold())
        if indexed is None:
            pending_models.append(record)
        elif not indexed.get('objFiles') and indexed.get('sha256') != record['sha256']:
            record['warning'] = 'Source hash differs from current integration manifest'
            changed_files.append(record)
        if p.suffix.lower() == '.glb':
            try:
                with p.open('rb') as f:
                    magic, version, total = struct.unpack('<III', f.read(12))
                    length, chunk_type = struct.unpack('<II', f.read(8))
                    gltf = json.loads(f.read(length))
                warnings = []
                if not gltf.get('materials'):
                    warnings.append('no_materials')
                if any('material' not in primitive for mesh in gltf.get('meshes', []) for primitive in mesh.get('primitives', [])):
                    warnings.append('primitive_without_material')
                if any(not str(image.get('uri', '')).startswith('data:') and image.get('uri') for image in gltf.get('images', [])):
                    warnings.append('external_image_uri')
                if warnings:
                    source_glb_warnings.append({'relative': relative, 'warnings': warnings})
            except Exception as exc:
                source_glb_warnings.append({'relative': relative, 'warnings': ['parse_error'], 'error': str(exc)})
    all_files.append(record)

report_hashes = {r.get('sourceSha256') for r in reports}
unique_inventory = defaultdict(list)
for index, entry in enumerate(inventory):
    unique_inventory[entry['sha256']].append({'index': index, 'relative': entry['relative']})
unpublished_inventory = []
for source_hash, entries in unique_inventory.items():
    if source_hash not in report_hashes:
        unpublished_inventory.extend(entries)
outputs = []
output_warnings = []
for report in reports:
    p = ROOT / 'frontend/public' / report['url'].lstrip('/')
    exists = p.is_file()
    output = {'id': report['id'], 'category': report['category'], 'status': report.get('status'), 'exists': exists, 'bytesMatch': exists and p.stat().st_size == report['bytes'], 'hashMatches': exists and sha(p) == report['sha256']}
    if exists:
        with p.open('rb') as f:
            f.read(12)
            length, chunk_type = struct.unpack('<II', f.read(8))
            gltf = json.loads(f.read(length))
        output.update(materials=len(gltf.get('materials', [])), meshes=len(gltf.get('meshes', [])), skins=len(gltf.get('skins', [])), animations=[a.get('name') for a in gltf.get('animations', [])])
        primitive_without_material = sum('material' not in q for m in gltf.get('meshes', []) for q in m.get('primitives', []))
        if primitive_without_material or not gltf.get('materials'):
            output_warnings.append({'id': report['id'], 'sourceRelative': report['sourceRelative'], 'materials': output['materials'], 'primitiveWithoutMaterial': primitive_without_material})
    outputs.append(output)

audit = {
    'date': '2026-10-02', 'sourceRoot': str(SOURCE),
    'files': len(all_files), 'extensions': dict(Counter(x['extension'] for x in all_files)),
    'inventoryLogicalEntries': len(inventory), 'uniqueInventoryHashes': len(unique_inventory),
    'inventoryDuplicates': [v for v in unique_inventory.values() if len(v) > 1],
    'rawModelFiles': sum(x['extension'] in {'.glb', '.gltf', '.obj', '.fbx', '.blend', '.stl', '.dae'} for x in all_files),
    'sourceModelDuplicates': [v for v in current_hashes.values() if len(v) > 1],
    'newFilesSinceOct1': new_files, 'changedFilesSinceOct1': changed_files,
    'modelsAbsentFromInventory': pending_models, 'inventoryWithoutIndividualSuppliedReport': unpublished_inventory,
    'validatedReports': len(reports), 'categories': dict(Counter(x['category'] for x in reports)),
    'outputHashAndByteFailures': [x for x in outputs if not (x['exists'] and x['bytesMatch'] and x['hashMatches'])],
    'sourceMaterialWarnings': source_glb_warnings, 'outputMaterialWarnings': output_warnings,
    'outputs': outputs,
}
(ROOT / 'reports/source_expansion_audit_20261002.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'reports/all_source_files_20261002_audit.json').write_text(json.dumps(all_files, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in audit.items() if k not in {'outputs', 'sourceMaterialWarnings', 'sourceModelDuplicates', 'inventoryDuplicates', 'newFilesSinceOct1'}}, ensure_ascii=False, indent=2))
