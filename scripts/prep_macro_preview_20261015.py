"""Save and render only the new, inactive macro scene in the recovered master."""
import bpy
import json
from datetime import datetime
from pathlib import Path
from mathutils import Vector

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
REPORT = ROOT / "reports/PLANO_MACRO_20261014.json"
scene = bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"]
assert Path(bpy.data.filepath).resolve() == MASTER.resolve()
assert scene.get("runtime_enabled") is False
assert "PREP_JALECO_QA_20261014" in bpy.data.scenes
report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
execution = report["blockoutExecution"]
assert execution["originalObjectsFingerprintBefore"] == execution["originalObjectsFingerprintAfter"]
for window in bpy.context.window_manager.windows:
    window.scene = scene
    for area in window.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.clip_end = 20000
            space.shading.type = "MATERIAL"
            space.region_3d.view_distance = 5200
            space.region_3d.view_location = Vector((0, 0, 0))
            space.region_3d.view_perspective = "CAMERA"
scene.camera = bpy.data.objects["MACRO14_CAM_OBLIQUE"]
execution.update({"status": "saved-awaiting-render-review", "masterFile": str(MASTER),
                  "saveTimeLocal": datetime.now().isoformat(timespec="seconds"),
                  "sceneCountAfter": len(bpy.data.scenes), "objectCountAfter": len(bpy.data.objects)})
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), check_existing=False)
execution["savedBytes"] = MASTER.stat().st_size
previews = []
for suffix, camera in [("visao_geral", "MACRO14_CAM_OVERVIEW"), ("perspectiva", "MACRO14_CAM_OBLIQUE")]:
    path = ROOT / ("reports/mapa_macro_" + suffix + "_20261015.png")
    if path.exists():
        raise RuntimeError("Preserve the existing preview before rendering again: " + str(path))
    scene.camera = bpy.data.objects[camera]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    assert path.exists() and path.stat().st_size > 0
    previews.append({"path": str(path), "bytes": path.stat().st_size, "camera": camera})
execution["previews"] = previews
execution["status"] = "saved-and-rendered-awaiting-visual-review"
execution["limitations"] = ["Inactive planning scene; not exported to runtime", "Conceptual building volumes; hospital interiors reserved only", "Coastal road crossing remains unresolved", "No claim of traffic or CTB compliance in this prototype"]
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_MACRO_PREVIEWS " + json.dumps(execution, ensure_ascii=False))
