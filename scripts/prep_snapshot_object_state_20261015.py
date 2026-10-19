"""Capture live stored channels for read-back validation; no Blender mutations."""
import bpy
import json
import sys
from pathlib import Path
ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
if str(ROOT/"scripts") not in sys.path:
    sys.path.insert(0,str(ROOT/"scripts"))
from prep_object_state_20261015 import object_state,state_hash
objects = [o for o in bpy.data.objects if not o.name.startswith("MACRO14_")]
state = object_state(objects)
target = ROOT/"reports/blender_stored_object_state_20261015.json"
assert not target.exists(), "Preserve the original validation baseline."
result = {"source":bpy.data.filepath,"objects":len(objects),"hash":state_hash(state),"state":state}
target.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
print(json.dumps({"file":str(target),"objects":len(objects),"hash":result["hash"],"bytes":target.stat().st_size}))
