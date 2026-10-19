"""Install a credit-independent, session-only Blender checkpoint timer.

The three owned slots are backups, never replacements of the editable master.
Loading a file or closing Blender stops the timer; rerun after restoring a file.
"""
import bpy
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
FOLDER = ROOT / "art/blender/checkpoints/automaticos"
MANIFEST = FOLDER / "guardian.json"
REPORT = ROOT / "reports/salvamento_automatico_20261015.json"
KEY = "PREPARATORIO_AUTOSAVE_GUARDIAN"
OWNER = "preparatorio-blender-guardian-v1"
INTERVAL = 600.0
FOLDER.mkdir(parents=True, exist_ok=True)
if MANIFEST.exists():
    state = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert state.get("owner") == OWNER and state.get("projectRoot") == str(ROOT)
else:
    assert not any(FOLDER.iterdir()), "Unknown backup files must be preserved before installation."
    state = {"owner": OWNER, "projectRoot": str(ROOT), "nextSlot": 1, "saves": []}
    MANIFEST.write_text(json.dumps(state, indent=2), encoding="utf-8")
previous = bpy.app.driver_namespace.get(KEY)
if previous and bpy.app.timers.is_registered(previous):
    bpy.app.timers.unregister(previous)

def checkpoint(force=False):
    source = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    allowed = (ROOT / "art/blender").resolve()
    if source is None or source.parent != allowed or not source.name.startswith("PREPARATORIO_PROJETO_"):
        return {"status": "skipped-other-file"}
    if not force and not bpy.data.is_dirty:
        return {"status": "skipped-clean"}
    if bpy.app.is_job_running("RENDER") or bpy.app.is_job_running("RENDER_PREVIEW") or bpy.context.mode != "OBJECT":
        return {"status": "deferred-busy"}
    current = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert current["owner"] == OWNER and current["projectRoot"] == str(ROOT)
    slot = int(current["nextSlot"])
    assert slot in (1, 2, 3)
    target = FOLDER / ("AUTO_PREP_SLOT_" + str(slot) + ".blend")
    owned = {entry["file"] for entry in current["saves"]}
    if target.exists() and str(target) not in owned:
        raise RuntimeError("Refusing to overwrite an unrecognized checkpoint: " + str(target))
    before = bpy.data.filepath
    bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, check_existing=False)
    assert bpy.data.filepath == before, "Backup must not replace the current master path."
    assert target.stat().st_size > 1000000
    with target.open("rb") as stream:
        header = stream.read(7)
        assert header == b"BLENDER" or header[:4] == b"\x28\xb5\x2f\xfd", "Expected a raw or Zstandard-compressed Blender file."
    entry = {"file": str(target), "source": before, "bytes": target.stat().st_size,
             "timeLocal": datetime.now().isoformat(timespec="seconds")}
    current["saves"] = [item for item in current["saves"] if item["file"] != str(target)] + [entry]
    current["nextSlot"] = slot % 3 + 1
    current["lastError"] = None
    MANIFEST.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "saved", **entry}

def timer():
    try:
        checkpoint()
    except Exception as exc:
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        current["lastError"] = {"timeLocal": datetime.now().isoformat(timespec="seconds"), "message": str(exc)}
        MANIFEST.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        print("PREP_AUTOSAVE_ERROR " + str(exc))
    return INTERVAL

test = checkpoint(force=True)
assert test["status"] == "saved", "Initial checkpoint must pass before registering the timer."
with bpy.data.libraries.load(test["file"], link=False) as (source_data, destination_data):
    assert "PREP_JALECO_QA_20261014" in source_data.scenes
    assert "PREP_MACRO_BLOCKOUT_20261014" in source_data.scenes
test["libraryReadValidated"] = True
bpy.app.driver_namespace[KEY] = timer
bpy.app.timers.register(timer, first_interval=INTERVAL, persistent=False)
report = {"status": "active-this-blender-session", "registered": bpy.app.timers.is_registered(timer),
          "intervalSeconds": INTERVAL, "slots": 3, "manifest": str(MANIFEST), "initialCheckpoint": test,
          "limitations": ["Stops when loading another file or closing Blender; reinstall after opening a project", "No timer can save after unexpected power loss or after Blender exits", "Copies can pause Blender briefly; rendering and non-object mode defer the save", "No shutdown or BIOS task is installed by this script"]}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_AUTOSAVE_INSTALLED " + json.dumps(report, ensure_ascii=False))
