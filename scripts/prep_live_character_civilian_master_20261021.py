from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import bpy


ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261016.blend"
LIBRARY = ROOT / "art/blender/libraries/PREP_CHARACTER_CYBERPUNK_CIVILIAN_20261021.blend"
REPORT = ROOT / "reports/CHARACTER_CYBERPUNK_CIVILIAN_MASTER_20261021.json"
SOURCE_SCENE = "PREP_CHARACTER_CYBERPUNK_CIVILIAN_20261021"
WEAPON_SIGNALS = ("sniper", "smg", "gun", "rifle", "weapon", "arma", "pistol")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


assert Path(bpy.data.filepath).resolve() == MASTER.resolve(), (
    f"Arquivo aberto inesperado: {bpy.data.filepath}"
)
assert LIBRARY.is_file(), LIBRARY

scene = bpy.data.scenes.get(SOURCE_SCENE)
appended = scene is None
if appended:
    with bpy.data.libraries.load(str(LIBRARY), link=False) as (source, target):
        assert SOURCE_SCENE in source.scenes, source.scenes
        target.scenes = [SOURCE_SCENE]
    scene = bpy.data.scenes.get(SOURCE_SCENE)

assert scene is not None

signals = []
for obj in scene.objects:
    names = [obj.name]
    if obj.data is not None:
        names.append(obj.data.name)
    if obj.type == "MESH":
        names.extend(slot.material.name for slot in obj.material_slots if slot.material)
    lowered = " ".join(names).lower()
    if any(signal in lowered for signal in WEAPON_SIGNALS):
        signals.append({"object": obj.name, "names": names})

assert not signals, signals

scene["PREP_role"] = "playable-character-civilian-review"
scene["PREP_weapon_policy"] = "unarmed-civilian-validated"
scene["PREP_runtime_asset"] = "/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre_Civilian_v1.glb"
scene["PREP_updated_at"] = datetime.now(timezone.utc).isoformat()

bpy.context.window.scene = scene
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER), compress=True)

mesh_objects = [obj for obj in scene.objects if obj.type == "MESH"]
armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
animations = sorted(action.name for action in bpy.data.actions if action.name == "motion")
REPORT.write_text(
    json.dumps(
        {
            "status": "validated-unarmed-civilian-appended-to-master",
            "master": str(MASTER),
            "masterBytes": MASTER.stat().st_size,
            "masterSha256": sha256(MASTER),
            "scene": scene.name,
            "appended": appended,
            "objects": len(scene.objects),
            "meshObjects": len(mesh_objects),
            "armatures": len(armatures),
            "animations": animations,
            "weaponSignals": signals,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    {
        "status": "saved",
        "scene": scene.name,
        "appended": appended,
        "objects": len(scene.objects),
        "meshObjects": len(mesh_objects),
        "armatures": len(armatures),
        "weaponSignals": signals,
        "report": str(REPORT),
    }
)
