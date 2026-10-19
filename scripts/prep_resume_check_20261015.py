"""Read-only check after a paused turn; do not overwrite subsequent user edits."""
import bpy
import hashlib
import json
from pathlib import Path
from datetime import datetime
ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
original = sorted([o for o in bpy.data.objects if not o.name.startswith("MACRO14_")], key=lambda o: o.name)
entries = [{"name": o.name, "type": o.type, "matrix": [list(row) for row in o.matrix_world],
            "parent": o.parent.name if o.parent else None, "data": o.data.name if o.data else None,
            "collections": sorted(c.name for c in o.users_collection), "hidden": [o.hide_viewport, o.hide_render],
            "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None} for o in original]
fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
guardian = bpy.app.driver_namespace.get("PREPARATORIO_AUTOSAVE_GUARDIAN")
report = {"timeLocal": datetime.now().isoformat(timespec="seconds"), "filepath": bpy.data.filepath,
          "dirty": bpy.data.is_dirty, "objects": len(bpy.data.objects), "scenes": len(bpy.data.scenes),
          "windows": [w.scene.name for w in bpy.context.window_manager.windows],
          "originalObjectFingerprint": fingerprint,
          "macroObjects": len(bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"].objects) if "PREP_MACRO_BLOCKOUT_20261014" in bpy.data.scenes else None,
          "guardianRegistered": bool(guardian and bpy.app.timers.is_registered(guardian))}
(ROOT / "reports/blender_resume_afternoon_20261015.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
