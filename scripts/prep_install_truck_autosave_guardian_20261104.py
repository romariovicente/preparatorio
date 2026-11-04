"""Session-only checkpoints for truck libraries. Execute explicitly via Blender MCP.

Copies never replace the editable library. File load/Blender exit stops this timer;
run this installer again after opening a library. No startup autoexec is installed.
"""
import bpy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = (ROOT / 'art/blender/libraries').resolve()
FOLDER = ROOT / 'art/blender/checkpoints/trucks_automaticos'
MANIFEST = FOLDER / 'guardian.json'
REPORT = ROOT / 'reports/TRUCK_AUTOSAVE_SESSION_20261104.json'
OWNER = 'preparatorio-truck-session-guardian-v1'
KEY = 'PREPARATORIO_TRUCK_AUTOSAVE_GUARDIAN'
INTERVAL = 120.0


def read_state():
    if not MANIFEST.exists():
        return {'owner': OWNER, 'projectRoot': str(ROOT), 'nextSlot': 1, 'saves': []}
    state = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert state['owner'] == OWNER and state['projectRoot'] == str(ROOT)
    return state


def write_state(state):
    temporary = MANIFEST.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(MANIFEST)


def checkpoint(force=False):
    source = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if source is None or source.parent != LIBRARIES or not re.fullmatch(
            r'PREPARATORIO_TRUCK_WORKSHOP_\d{8}(?:_WORK|_FINAL|_DETAIL_V\d+)?\.blend', source.name):
        return {'status': 'skipped-other-file'}
    if not force and not bpy.data.is_dirty:
        return {'status': 'skipped-clean'}
    if bpy.app.is_job_running('RENDER') or bpy.app.is_job_running('RENDER_PREVIEW') or bpy.context.mode != 'OBJECT':
        return {'status': 'deferred-busy'}
    state = read_state()
    slot = int(state['nextSlot'])
    assert slot in (1, 2, 3)
    target = FOLDER / f'TRUCK_AUTO_SLOT_{slot}.blend'
    if target.exists() and str(target) not in {entry['file'] for entry in state['saves']}:
        raise RuntimeError('Preserving unrecognized checkpoint: ' + str(target))
    source_path = bpy.data.filepath
    bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, check_existing=False)
    assert bpy.data.filepath == source_path
    assert target.stat().st_size > 1000000
    # Read native datablock names without importing anything into the active file.
    with bpy.data.libraries.load(str(target), link=False) as (saved, destination):
        assert {'ASSET_scania', 'ASSET_flatbed', 'ASSET_box', 'ASSET_tanker'}.issubset(saved.scenes)
    entry = {'file': str(target), 'source': str(source), 'bytes': target.stat().st_size,
             'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
             'timeLocal': datetime.now().astimezone().isoformat(timespec='seconds'),
             'nativeLibraryReadValidated': True}
    state['saves'] = [old for old in state['saves'] if old['file'] != str(target)] + [entry]
    state['nextSlot'] = slot % 3 + 1
    state['lastError'] = None
    write_state(state)
    return {'status': 'saved', **entry}


def timer():
    try:
        checkpoint()
    except Exception as error:
        state = read_state()
        state['lastError'] = {'timeLocal': datetime.now().astimezone().isoformat(), 'message': str(error)}
        write_state(state)
        print('TRUCK_AUTOSAVE_ERROR', repr(error))
    return INTERVAL


FOLDER.mkdir(parents=True, exist_ok=True)
read_state()
previous = bpy.app.driver_namespace.get(KEY)
if previous and bpy.app.timers.is_registered(previous):
    bpy.app.timers.unregister(previous)
initial = checkpoint(force=True)
assert initial['status'] == 'saved'
bpy.app.driver_namespace[KEY] = timer
bpy.app.timers.register(timer, first_interval=INTERVAL, persistent=False)
report = {'status': 'active-this-blender-session', 'registered': bpy.app.timers.is_registered(timer),
          'intervalSeconds': INTERVAL, 'slots': 3, 'initialCheckpoint': initial,
          'manifest': str(MANIFEST), 'sourceUnchanged': bpy.data.filepath,
          'limitations': ['Stops on file load or Blender exit; reinstall after opening another library',
                          'Only saves dirty truck libraries in Object mode; rendering defers a copy',
                          'Explicit saves remain required for scripted changes that do not set dirty state',
                          'No recovery after power loss can capture edits made since the last checkpoint']}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('TRUCK_AUTOSAVE_INSTALLED', json.dumps(report, ensure_ascii=False))
