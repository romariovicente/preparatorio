"""Create and validate an unarmed civilian derivative of the supplied cyberpunk character.

The original user-supplied GLB remains untouched.  Only meshes and materials that
belong to the embedded SMG are excluded from the derivative used by the game.
"""
import bpy
import hashlib
import json
import math
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "art/source/SUP_character_cyberpunk_free_3d_by_oscar_cre_BodyRig_armed_archived.glb"
TARGET = ROOT / "frontend/public/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre_Civilian_v1.glb"
PREVIEW = ROOT / "frontend/public/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre_Civilian_v1.jpg"
LIBRARY = ROOT / "art/blender/libraries/PREP_CHARACTER_CYBERPUNK_CIVILIAN_20261021.blend"
REPORT = ROOT / "reports/CHARACTER_CYBERPUNK_CIVILIAN_20261021.json"
LOG = ROOT / "reports/CHARACTER_CYBERPUNK_CIVILIAN_20261021.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_log = LOG.open("w", encoding="utf-8", buffering=1)
sys.stdout = _log
sys.stderr = _log

WEAPON = re.compile(r"(?:^|[_\-])(smg|guns?|rifle|sniper|pistol|weapon|mag|trigger)(?:[_\-]|$)", re.I)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb_doc(path):
    raw = path.read_bytes()
    assert raw[:4] == b"glTF" and struct.unpack_from("<I", raw, 8)[0] == len(raw)
    length, kind = struct.unpack_from("<II", raw, 12)
    assert kind == 0x4E4F534A
    return raw, json.loads(raw[20:20 + length].rstrip(b"\x00 ").decode("utf-8"))


def triangle_count(doc):
    total = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) == 4:
                total += doc["accessors"][primitive["indices"]]["count"] // 3
    return total


def weapon_signal(obj):
    values = [obj.name, getattr(obj.data, "name", "")]
    if obj.type == "MESH":
        values.extend(slot.material.name for slot in obj.material_slots if slot.material)
    return next((value for value in values if WEAPON.search(value or "")), None)


assert SOURCE.exists(), SOURCE
if TARGET.exists() and not REPORT.exists():
    TARGET.unlink()
for path in (TARGET.parent, PREVIEW.parent, LIBRARY.parent, REPORT.parent):
    path.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "PREP_CHARACTER_CYBERPUNK_CIVILIAN_20261021"
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
assert "FINISHED" in bpy.ops.import_scene.gltf(filepath=str(SOURCE))
bpy.context.view_layer.update()

model_objects = list(scene.objects)
weapon_objects = [obj for obj in model_objects if obj.type == "MESH" and weapon_signal(obj)]
assert weapon_objects, "The embedded weapon meshes were not found."
removed = [{
    "object": obj.name,
    "mesh": getattr(obj.data, "name", None),
    "materials": [slot.material.name for slot in obj.material_slots if slot.material],
    "triangles": sum(len(poly.vertices) - 2 for poly in obj.data.polygons),
} for obj in weapon_objects]

for obj in weapon_objects:
    bpy.data.objects.remove(obj, do_unlink=True)

# Remove empty weapon sockets only when they no longer contain a visible child.
for obj in list(scene.objects):
    if obj.type == "EMPTY" and WEAPON.search(obj.name or "") and not obj.children:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.context.view_layer.update()
remaining = [obj for obj in scene.objects if obj.type in {"MESH", "ARMATURE", "EMPTY"}]
assert any(obj.type == "ARMATURE" for obj in remaining)
assert any(obj.type == "MESH" for obj in remaining)
assert not any(weapon_signal(obj) for obj in remaining if obj.type == "MESH")

bpy.ops.object.select_all(action="DESELECT")
for obj in remaining:
    obj.select_set(True)
bpy.context.view_layer.objects.active = next(obj for obj in remaining if obj.type == "ARMATURE")
assert "FINISHED" in bpy.ops.export_scene.gltf(
    filepath=str(TARGET), export_format="GLB", use_selection=True, use_active_scene=True,
    export_yup=True, export_animations=True, export_skins=True,
    export_animation_mode="NLA_TRACKS", export_cameras=False, export_lights=False,
    export_extras=True, export_image_format="AUTO")

raw, doc = glb_doc(TARGET)
names = []
for section in ("meshes", "materials"):
    names.extend(item.get("name", "") for item in doc.get(section, []))
assert not any(WEAPON.search(name or "") for name in names), names
assert doc.get("skins") and doc.get("animations")
assert [clip.get("name") for clip in doc["animations"]] == ["motion"]

# Fresh Blender reimport verifies that the exported rig, animation and meshes are usable.
validation = bpy.data.scenes.new("VALIDATE_CYBERPUNK_CIVILIAN_20261021")
bpy.context.window.scene = validation
assert "FINISHED" in bpy.ops.import_scene.gltf(filepath=str(TARGET))
bpy.context.view_layer.update()
validated_meshes = [obj for obj in validation.objects if obj.type == "MESH"]
validated_armatures = [obj for obj in validation.objects if obj.type == "ARMATURE"]
assert validated_meshes and validated_armatures
assert not any(weapon_signal(obj) for obj in validated_meshes)
assert all(math.isfinite(coordinate) for obj in validated_meshes for vertex in obj.data.vertices for coordinate in vertex.co)

# Render the actual validated derivative.  This preview replaces the armed catalog image.
armature = validated_armatures[0]
if armature.animation_data:
    armature.animation_data.action = None
    for track in armature.animation_data.nla_tracks:
        track.mute = False
validation.frame_set(1)
validation.world = bpy.data.worlds.new("CYBERPUNK_CIVILIAN_WORLD")
validation.world.color = (0.035, 0.045, 0.055)
for location, energy, size in [((3.0, -4.2, 4.8), 900, 4.0), ((-3.0, -1.0, 2.6), 500, 3.0)]:
    bpy.ops.object.light_add(type="AREA", location=location)
    bpy.context.object.data.energy = energy
    bpy.context.object.data.size = size
bpy.ops.object.camera_add(location=(2.4, -4.8, 2.0))
camera = bpy.context.object
points = [obj.matrix_world @ Vector(corner) for obj in validated_meshes for corner in obj.bound_box]
minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
center = (minimum + maximum) * 0.5
height = max(.1, maximum.z - minimum.z)
camera.location = center + Vector((height * .55, -height * 1.65, height * .08))
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = height * 1.12
validation.camera = camera
validation.render.engine = "BLENDER_EEVEE"
validation.render.resolution_x = 720
validation.render.resolution_y = 900
validation.render.resolution_percentage = 100
validation.render.image_settings.file_format = "JPEG"
validation.render.image_settings.color_mode = "RGB"
validation.render.image_settings.quality = 92
validation.render.film_transparent = False
validation.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)
assert PREVIEW.exists() and PREVIEW.stat().st_size > 10_000

validation["prep_status"] = "civilian-unarmed-validated"
validation["source_preserved"] = str(SOURCE)
validation["public_derivative"] = str(TARGET)
bpy.ops.wm.save_as_mainfile(filepath=str(LIBRARY), compress=True)

report = {
    "owner": "preparatorio-civilian-character-20261021-v1",
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "status": "validated-unarmed-civilian-derivative",
    "source": {"path": str(SOURCE), "bytes": SOURCE.stat().st_size, "sha256": sha(SOURCE), "preserved": True},
    "output": {"path": str(TARGET), "url": "/assets/supplied/" + TARGET.name,
               "bytes": TARGET.stat().st_size, "sha256": sha(TARGET),
               "triangles": triangle_count(doc), "meshes": len(doc.get("meshes", [])),
               "skins": len(doc.get("skins", [])), "animations": [a.get("name") for a in doc.get("animations", [])]},
    "removedWeaponMeshes": removed,
    "weaponMaterialOrMeshSignalsAfterExport": [name for name in names if WEAPON.search(name or "")],
    "validation": {"freshBlenderReimport": True, "finiteVertices": True,
                   "armatures": len(validated_armatures), "meshes": len(validated_meshes)},
    "preview": str(PREVIEW),
    "blendLibrary": str(LIBRARY),
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
