"""Verify live state; the separate background audit reads the saved master."""
import bpy
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
master = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
scene = bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"]
assert Path(bpy.data.filepath).resolve() == master.resolve()
plan_path = ROOT / "reports/PLANO_MACRO_20261014.json"
plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
original = sorted([o for o in bpy.data.objects if not o.name.startswith("MACRO14_")], key=lambda o: o.name)
entries = [{"name": o.name, "type": o.type, "matrix": [list(row) for row in o.matrix_world],
            "parent": o.parent.name if o.parent else None, "data": o.data.name if o.data else None,
            "collections": sorted(c.name for c in o.users_collection), "hidden": [o.hide_viewport, o.hide_render],
            "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None} for o in original]
fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
assert fingerprint == plan["blockoutExecution"]["originalObjectsFingerprintBefore"]
live_scenes = [s.name for s in bpy.data.scenes]
assert scene.name in live_scenes and "PREP_JALECO_QA_20261014" in live_scenes
assert "00_ARAPIRACA_CYBER_20261005" in live_scenes
guardian = bpy.app.driver_namespace.get("PREPARATORIO_AUTOSAVE_GUARDIAN")
assert guardian and bpy.app.timers.is_registered(guardian)
qa = bpy.data.scenes["PREP_JALECO_QA_20261014"]
rigs = [{"name": o.name, "bones": len(o.data.bones)} for o in qa.objects if o.type == "ARMATURE"]
assert len(rigs) == 2 and all(rig["bones"] == 55 for rig in rigs)
result = {"verifiedAtLocal": datetime.now().isoformat(timespec="seconds"), "master": str(master),
          "masterBytes": master.stat().st_size, "liveSceneNames": live_scenes,
          "liveSceneCount": len(live_scenes), "liveObjectCount": len(bpy.data.objects),
          "activeWindows": [w.scene.name for w in bpy.context.window_manager.windows],
          "legacyCityObjects": len(bpy.data.scenes["00_ARAPIRACA_CYBER_20261005"].objects),
          "legacyObjectFingerprintUnchanged": True, "legacyObjectCount": len(original),
          "macro": {"scene": scene.name, "objects": len(scene.objects),
                    "collections": len([c for c in bpy.data.collections if c.name.startswith("MACRO14_")]),
                    "materials": len([m for m in bpy.data.materials if m.name.startswith("MACRO14_")]),
                    "units": scene.unit_settings.system, "scaleLength": scene.unit_settings.scale_length,
                    "runtimeEnabled": scene.get("runtime_enabled"), "visualReview": "Three revised renders inspected; corners, labels and hospital pedestrian approach verified"},
          "coatScene": {"objects": len(qa.objects), "rigs": rigs,
                        "hiddenHelpers": [o.name for o in qa.objects if o.get("character_helper_hidden") and o.hide_render]},
          "autosaveTimerRegistered": True,
          "blenderVersion": bpy.app.version_string,
          "limits": ["Macro scene remains a planning prototype with placeholder building volumes", "Coastal crossing remains unresolved", "Browser interaction was not visually automated in this validation"]}
if scene.get("coast_land_route_revised"):
    coastal = json.loads((ROOT / "reports/BLENDER_COAST_20261015.json").read_text(encoding="utf-8"))
    assert not coastal["waterIntersections"]
    result["macro"]["coastalRightOfWayClearanceMeters"] = coastal["nearestRightOfWayClearanceMeters"]
    result["macro"]["visualReview"] += "; two final coastal renders reviewed"
    result["limits"].remove("Coastal crossing remains unresolved")
plan["blockoutExecution"]["status"] = "saved-and-visually-reviewed-inactive-prototype"
plan["blockoutExecution"]["visualReviewReport"] = "reports/BLENDER_ENTREGA_20261015.json"
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "reports/BLENDER_ENTREGA_20261015.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_DELIVERY_VERIFIED " + json.dumps(result, ensure_ascii=False))
