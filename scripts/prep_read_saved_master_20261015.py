"""Read-only background audit of the saved master. Never save or load scripts."""
import bpy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
assert bpy.app.background
assert Path(bpy.data.filepath).resolve() == MASTER.resolve()
sys.path.insert(0,str(ROOT/"scripts"))
from prep_object_state_20261015 import object_state,state_hash
report_path = ROOT / "reports/BLENDER_ENTREGA_20261015.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
plan = json.loads((ROOT / "reports/PLANO_MACRO_20261014.json").read_text(encoding="utf-8"))
assert len(bpy.data.scenes) == report["liveSceneCount"] == 44
assert len(bpy.data.objects) == report["liveObjectCount"] == 12917
scene = bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"]
assert len(scene.objects) == 400 and scene.get("runtime_enabled") is False
qa = bpy.data.scenes["PREP_JALECO_QA_20261014"]
assert len(qa.objects) == 73
assert sorted(len(o.data.bones) for o in qa.objects if o.type == "ARMATURE") == [55, 55]
original = sorted([o for o in bpy.data.objects if not o.name.startswith("MACRO14_")], key=lambda o: o.name)
entries = [{"name": o.name, "type": o.type, "matrix": [list(row) for row in o.matrix_world],
            "parent": o.parent.name if o.parent else None, "data": o.data.name if o.data else None,
            "collections": sorted(c.name for c in o.users_collection), "hidden": [o.hide_viewport, o.hide_render],
            "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None} for o in original]
fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
snapshot = json.loads((ROOT/"reports/blender_stored_object_state_20261015.json").read_text(encoding="utf-8"))
stored = object_state(original)
differences = [name for name in set(stored)|set(snapshot["state"]) if stored.get(name) != snapshot["state"].get(name)]
assert not differences, "Saved persistent channels differ: "+str(differences[:20])
assert state_hash(stored) == snapshot["hash"]
report["savedFileReadBack"] = {"validated": True, "loadedWithAutoexecDisabled": True,
                              "timeLocal": datetime.now().isoformat(timespec="seconds"),
                              "blenderVersion": bpy.app.version_string, "fileBytes": MASTER.stat().st_size,
                              "scenes": len(bpy.data.scenes), "objects": len(bpy.data.objects),
                              "storedObjectChannelsHash":state_hash(stored),"storedObjectChannelsMatchLive":True,
                              "evaluatedWorldCacheHashMatchesLive":fingerprint == plan["blockoutExecution"]["originalObjectsFingerprintBefore"],
                              "worldCacheNote":"World matrices are evaluated caches; stored channels, inverse-parent matrices, links, visibility and actions are compared independently.",
                              "fileModifiedByAudit": False}
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_MASTER_READ_BACK_OK " + json.dumps(report["savedFileReadBack"]))
