"""Apply the visual review to the new macro scene, preserving all legacy objects."""
import bpy
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
REPORT = ROOT / "reports/PLANO_MACRO_20261014.json"
scene = bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"]
assert not scene.get("visual_review_applied"), "Review was already applied; inspect before repeating."
report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
execution = report["blockoutExecution"]
original = sorted([o for o in bpy.data.objects if not o.name.startswith("MACRO14_")], key=lambda o: o.name)
def fingerprint():
    entries = []
    for obj in original:
        entries.append({"name": obj.name, "type": obj.type,
                        "matrix": [list(row) for row in obj.matrix_world],
                        "parent": obj.parent.name if obj.parent else None,
                        "data": obj.data.name if obj.data else None,
                        "collections": sorted(col.name for col in obj.users_collection),
                        "hidden": [obj.hide_viewport, obj.hide_render],
                        "action": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None})
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
assert len(original) == execution["preservedObjectCount"]
assert fingerprint() == execution["originalObjectsFingerprintBefore"]
for mat in bpy.data.materials:
    if not mat.name.startswith("MACRO14_"):
        continue
    rgba = tuple(mat.diffuse_color)
    linear = tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgba[:3]) + (rgba[3],)
    mat.diffuse_color = linear
    node = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    node.inputs["Base Color"].default_value = linear
for obj in scene.objects:
    if obj.type == "FONT" and obj.name != "MACRO14_HELIPAD_H":
        obj.location.z = 0.65
parking = bpy.data.objects["MACRO14_HOSPITAL_PARKING_RESERVE"]
parking.location.x = 445
assert parking.location.x + parking.dimensions.x / 2 < 498.4
assert bpy.data.objects["MACRO14_HELIPAD_H"].location.z > 24.4
bpy.data.objects["MACRO14_CAM_OBLIQUE"].data.ortho_scale = 6400
bpy.data.objects["MACRO14_SUN"].data.energy = 1.5
bpy.data.objects["MACRO14_SUN"].data.use_shadow = False
scene["visual_review_applied"] = True
execution["visualCorrections"] = ["Hospital parking moved west to clear the 3.2m pedestrian approach", "Oblique camera widened to include terrain corners", "Labels lowered and diagram lighting shadows removed for readable labels", "Macro swatches converted from sRGB to linear shader colors"]
assert fingerprint() == execution["originalObjectsFingerprintBefore"]
execution["originalObjectsFingerprintAfterVisualReview"] = fingerprint()
previews = []
for suffix, camera in [("visao_geral_revisada", "MACRO14_CAM_OVERVIEW"), ("perspectiva_revisada", "MACRO14_CAM_OBLIQUE"), ("hospital_reserva", "MACRO14_CAM_HOSPITAL")]:
    path = ROOT / ("reports/mapa_macro_" + suffix + "_20261015.png")
    if path.exists():
        raise RuntimeError("Preserve existing preview before re-render: " + str(path))
    scene.camera = bpy.data.objects[camera]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    previews.append({"path": str(path), "camera": camera, "bytes": path.stat().st_size})
scene.camera = bpy.data.objects["MACRO14_CAM_OBLIQUE"]
scene.render.filepath = str(ROOT / "reports/mapa_macro_perspectiva_revisada_20261015.png")
for window in bpy.context.window_manager.windows:
    window.scene = scene
    for area in window.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.clip_end = 20000
            area.spaces.active.region_3d.view_perspective = "CAMERA"
missing_images = []
packed_count = 0
for image in bpy.data.images:
    if image.packed_file or len(image.packed_files):
        packed_count += 1
    elif image.source == "FILE" and image.filepath and not Path(bpy.path.abspath(image.filepath)).exists():
        missing_images.append({"name": image.name, "path": image.filepath})
missing_libraries = [lib.filepath for lib in bpy.data.libraries if not Path(bpy.path.abspath(lib.filepath)).exists()]
execution["reviewedPreviews"] = previews
execution["status"] = "saved-revised-renders-awaiting-human-visual-review"
execution["assetCheck"] = {"packedImageCount": packed_count, "missingExternalImages": missing_images, "missingLinkedLibraries": missing_libraries}
execution["saveTimeLocal"] = datetime.now().isoformat(timespec="seconds")
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), check_existing=False)
execution["savedBytes"] = MASTER.stat().st_size
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_MACRO_REVIEW " + json.dumps({"master": str(MASTER), "savedBytes": execution["savedBytes"], "preserved": fingerprint() == execution["originalObjectsFingerprintBefore"], "previews": previews, "assetCheck": execution["assetCheck"]}, ensure_ascii=False))
