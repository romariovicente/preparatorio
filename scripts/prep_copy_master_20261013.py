"""Make an exclusive byte-for-byte working master; never replace either file."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
source = PROJECT / 'art/blender/PREPARATORIO_PROJETO_20261008.blend'
target = PROJECT / 'art/blender/PREPARATORIO_PROJETO_20261013.blend'
if not source.is_file():
    raise FileNotFoundError(source)
if target.exists():
    raise FileExistsError(f'Refusing to replace working master: {target}')
source_before = source.stat()
with source.open('rb') as src, target.open('xb') as dst:
    shutil.copyfileobj(src, dst, 8 * 1024 * 1024)

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()

source_after = source.stat()
source_hash, target_hash = digest(source), digest(target)
report = {'time_local': datetime.now().isoformat(timespec='seconds'), 'source': str(source), 'target': str(target),
    'source_bytes': source_before.st_size, 'target_bytes': target.stat().st_size,
    'source_sha256': source_hash, 'target_sha256': target_hash, 'hashes_match': source_hash == target_hash,
    'source_size_preserved': source_before.st_size == source_after.st_size,
    'source_mtime_preserved': source_before.st_mtime_ns == source_after.st_mtime_ns, 'exclusive_target_creation': True}
(PROJECT / 'reports/blender_master_copy_20261013.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
if not all(report[key] for key in ('hashes_match', 'source_size_preserved', 'source_mtime_preserved')):
    raise RuntimeError('Copy validation failed; inspect report before opening the new master')
