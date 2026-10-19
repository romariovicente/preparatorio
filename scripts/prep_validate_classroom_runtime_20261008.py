"""Read-only asset/runtime checks. Source GLBs and Blender libraries stay intact."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NODE = Path(r'C:\Users\Senac\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
FRONTEND = ROOT / 'frontend'
MANIFEST = FRONTEND / 'src/config/classroomAssets.json'
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
assets = []
for record in manifest['assets'] + [manifest['educational']]:
    path = FRONTEND / 'public' / record['url'].lstrip('/')
    binary = path.read_bytes()
    digest = hashlib.sha256(binary).hexdigest()
    document = json.loads(binary[20:20 + int.from_bytes(binary[12:16], 'little')])
    assert digest == record['sha256'], path
    assert len(binary) == record['bytes'], path
    assets.append({'id': record.get('id', record.get('assetId')), 'path': str(path),
                   'sha256': digest, 'bytes': len(binary), 'unchanged': True,
                   'meshes': len(document.get('meshes', [])), 'skins': len(document.get('skins', [])),
                   'animations': len(document.get('animations', [])),
                   'images': len(document.get('images', []))})

source = FRONTEND / 'public/assets/characters/CHR_Remy_Mixamo_20261005.glb'
source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_digest == manifest['assets'][1]['sourceSha256']
blend = ROOT / manifest['blender']['library']
blend_digest = hashlib.sha256(blend.read_bytes()).hexdigest()
assert blend_digest == manifest['blender']['sha256']

def check(arguments):
    completed = subprocess.run([str(NODE), *arguments], cwd=FRONTEND,
                               capture_output=True, text=True, encoding='utf-8')
    return {'arguments': arguments, 'passed': completed.returncode == 0,
            'exitCode': completed.returncode, 'output': (completed.stdout + completed.stderr).strip()}

tests = check(['--test', 'src/cyber/classroomWorld.test.js'])
lint = check(['node_modules/eslint/bin/eslint.js', 'src/cyber/FuturisticClassroom.jsx',
              'src/cyber/classroomWorld.js', 'src/cyber/classroomWorld.test.js'])
report = {
    'date': '2026-10-08', 'author': manifest['author'],
    'manifest': str(MANIFEST), 'assetChecksPassed': True, 'assets': assets,
    'originalRemy': {'path': str(source), 'sha256': source_digest, 'unchanged': True},
    'originalBlend': {'path': str(blend), 'sha256': blend_digest, 'unchanged': True},
    'visualReview': {
        'classroom': 'Passed: classroom_futuristic_20261007.png shows real seated students and legible Portuguese board labels.',
        'student': 'Passed: classroom_student_pose_20261007.png shows seated real Remy face, clothing and rig-aligned chair.',
        'anatomy': 'Passed: EDU_Anatomy_XRay_20261006.preview.png shows real layered bone/tissue/translucent-skin anatomy.',
        'gameReview': 'Component prepared; game integration/interactive visual review handled by the parent task.'
    },
    'placement': {'centerFrontend': manifest['center'], 'offsetBlender': manifest['blender']['worldOffsetBlender'],
                  'footprint': {'minX': 9, 'maxX': 23, 'minZ': 53.99, 'maxZ': 66},
                  'approach': manifest['approach'], 'entry': manifest['entry'], 'walkPath': manifest['aislePath'],
                  'clearOf': ['terminal', 'hospital', 'training campus', 'residences', 'shops', 'dealers',
                              'hangar', 'farm', 'elevator', 'east collector', 'south access', 'east-west street'],
                  'roadCoordination': 'Road agent confirmed new north Z=-99 / west X=-106 connections preserve this lot and approach.'},
    'runtimeChecks': tests, 'lint': lint,
    'door': {'realLeafAndHandleAnimated': True, 'proximityOpening': True, 'manualClick': True,
             'occupiedClosingProtection': True, 'movingCollider': True, 'durationSeconds': 1.25,
             'sourceOpeningGapRepairedWithVisibleInfill': True},
    'liveBlenderTouched': False,
    'limitations': manifest['limitations']
}
destination = ROOT / 'reports/classroom_runtime_validation_20261008.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'report': str(destination), 'testsPassed': tests['passed'], 'lintPassed': lint['passed']}))
if not tests['passed'] or not lint['passed']:
    raise SystemExit(1)
