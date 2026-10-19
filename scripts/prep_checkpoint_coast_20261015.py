import bpy
import json
from pathlib import Path
from datetime import datetime
ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
master = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
assert Path(bpy.data.filepath).resolve() == master.resolve()
target = ROOT / ("art/blender/checkpoints/BEFORE_COAST_20261015_" + datetime.now().strftime("%H%M%S_%f") + ".blend")
bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True, check_existing=True)
assert target.is_file() and target.stat().st_size > 1000000
report = {"checkpoint": str(target), "bytes": target.stat().st_size, "source": str(master), "timeLocal": datetime.now().isoformat(timespec="seconds")}
(ROOT / "reports/coast_checkpoint_20261015.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
