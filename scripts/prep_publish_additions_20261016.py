"""Publish only exact, validated Blender deliveries into the additive catalog."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reports = ['fauna_catalog_entries_20261016.json', 'anatomy_catalog_entries_20261016.json',
           'train_catalog_entries_20261016.json', 'station_catalog_entries_20261016.json']
records = []
for name in reports:
    value = json.loads((ROOT / 'reports' / name).read_text(encoding='utf-8'))
    if isinstance(value, dict):
        assert value.get('status') == 'validated', name
        value = value['entries']
    assert isinstance(value, list) and value, name
    records.extend(value)
assert len(records) == 13, len(records)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

seen_ids, seen_hashes = set(), set()
for record in records:
    assert record['status'] == 'validated' and record['reimportValidated'] is True
    assert record['id'] not in seen_ids and record['sha256'] not in seen_hashes
    seen_ids.add(record['id']); seen_hashes.add(record['sha256'])
    assert record['url'].startswith('/assets/') and record['preview'].startswith('/assets/')
    path = ROOT / 'frontend/public' / record['url'].lstrip('/')
    preview = ROOT / 'frontend/public' / record['preview'].lstrip('/')
    assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']
    assert preview.is_file() and preview.stat().st_size > 500
    if record.get('previewSha256'):
        assert sha(preview) == record['previewSha256']
    record['previewSha256'] = sha(preview)
    record['rigged'] = record.get('rigged', bool(record.get('originalRig')))
    record['playable'] = False
    record['catalogAdded'] = '2026-10-16'
    record['tags'] = list(dict.fromkeys([*record.get('tags', []), 'Entrega de 16/10/2026']))

dest = ROOT / 'frontend/src/config/suppliedAdditions20261016.json'
if dest.exists():
    existing = json.loads(dest.read_text(encoding='utf-8'))
    assert all(any(r['id'] == old['id'] and r['sha256'] == old['sha256'] for r in records) for old in existing)
dest.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'added':len(records), 'bytes':sum(r['bytes'] for r in records),
                  'animated':sum(bool(r['animations']) for r in records), 'clips':sum(len(r['animations']) for r in records)}, ensure_ascii=True))
