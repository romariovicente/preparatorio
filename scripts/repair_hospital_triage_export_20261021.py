import bpy
import hashlib
import json
from pathlib import Path


ROOT = Path(r'C:/Users/Senac/Documents/Codex/2026-09-28/referenced-chatgpt-conversation-this-is-an/outputs/preparatorio')
MASTER = ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend'
ASSET = ROOT / 'frontend/public/assets/additions20261021/PROP_Hospital_Triage_Terminal_20261021.glb'
REPORT = ROOT / 'reports/HOSPITAL_TRIAGE_BLENDER_20261021.json'
SCENE_NAME = 'PREP_HOSPITAL_TRIAGE_TERMINAL_20261021'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


if Path(bpy.data.filepath).resolve() != MASTER.resolve():
    raise RuntimeError(f'Unexpected live file: {bpy.data.filepath}')
scene = bpy.data.scenes.get(SCENE_NAME)
model = bpy.data.collections.get('HSP21_TRIAGE_MODEL')
if not scene or not model:
    raise RuntimeError('The authored triage scene is incomplete')
meshes = [obj for obj in model.objects if obj.type == 'MESH']
roots = [obj for obj in model.objects if obj.type == 'EMPTY' and obj.name.startswith('HSP21_TRIAGE_ROOT')]
if len(roots) != 1:
    raise AssertionError(f'Expected one scene-owned terminal root, found {[obj.name for obj in roots]}')
root = roots[0]
if len(meshes) < 10:
    raise AssertionError(f'Expected terminal mesh objects, found {len(meshes)}')
for mesh in meshes:
    mesh.parent = root
stale_root = bpy.data.objects.get('HSP21_TRIAGE_ROOT')
if stale_root is not root and stale_root and stale_root.users == 0:
    bpy.data.objects.remove(stale_root)
for window in bpy.context.window_manager.windows:
    window.scene = scene
bpy.ops.export_scene.gltf(
    filepath=str(ASSET),
    export_format='GLB',
    use_active_scene=True,
    use_selection=False,
    export_cameras=False,
    export_lights=False,
    export_animations=False,
    export_extras=True,
    export_yup=True,
)
if ASSET.stat().st_size < 10_000:
    raise AssertionError(f'Repaired export is still empty: {ASSET.stat().st_size} bytes')
root['runtime_asset'] = str(ASSET.relative_to(ROOT)).replace('\\', '/')
root['runtime_sha256'] = sha256(ASSET)
root['runtime_bytes'] = ASSET.stat().st_size
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), compress=True)
report = json.loads(REPORT.read_text(encoding='utf-8'))
report.update({
    'assetBytes': ASSET.stat().st_size,
    'assetSha256': sha256(ASSET),
    'masterBytes': MASTER.stat().st_size,
    'masterSha256': sha256(MASTER),
    'emptySelectionExportRejectedBytes': 452,
    'exportRepairPassed': True,
    'exportedMeshObjects': len(meshes),
})
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('HOSPITAL_TRIAGE_EXPORT_REPAIRED ' + json.dumps({
    'assetBytes': report['assetBytes'],
    'assetSha256': report['assetSha256'],
    'meshObjects': len(meshes),
    'masterBytes': report['masterBytes'],
    'masterSha256': report['masterSha256'],
}))
