"""Build a reversible neutral-pose staging library for the Cyberpunk civilian.

This script must run only while the dedicated staging copy is open.  It never
writes the master project, the public GLB, or the validated source library.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LIBRARY = ROOT / "art/blender/libraries/PREP_CHARACTER_CYBERPUNK_CIVILIAN_20261021.blend"
STAGE_LIBRARY = ROOT / "art/blender/libraries/PREP_CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022.blend"
REPORT = ROOT / "reports/CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022.json"
FRONT_RENDER = ROOT / "reports/CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022_front.png"
SIDE_RENDER = ROOT / "reports/CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022_side.png"
INITIAL_SHA256 = "3a76658b34c7db299f41130a02612b489991336b50b18bf325bece139b41ef4f"
TARGET_HEIGHT_M = 1.70
SOURCE_SCENE = "VALIDATE_CYBERPUNK_CIVILIAN_20261021"
STAGE_SCENE = "PREP_CHARACTER_CYBERPUNK_NEUTRAL_STAGE_20261022"
WEAPON_SIGNALS = ("sniper", "smg", "gun", "rifle", "weapon", "arma", "pistol")

ARM_PAIRS = (
    ("CC_Base_L_Clavicle_049", "CC_Base_R_Clavicle_077"),
    ("CC_Base_L_Upperarm_050", "CC_Base_R_Upperarm_078"),
    ("CC_Base_L_UpperarmTwist01_071", "CC_Base_R_UpperarmTwist01_0104"),
    ("CC_Base_L_UpperarmTwist02_072", "CC_Base_R_UpperarmTwist02_0105"),
    ("CC_Base_L_Forearm_051", "CC_Base_R_Forearm_079"),
    ("CC_Base_L_ForearmTwist01_052", "CC_Base_R_ForearmTwist01_081"),
    ("CC_Base_L_ForearmTwist02_053", "CC_Base_R_ForearmTwist02_082"),
    ("CC_Base_L_Hand_055", "CC_Base_R_Hand_083"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluated_bounds(scene: bpy.types.Scene, objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points: list[Vector] = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    assert points, "No evaluated mesh vertices were found."
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def vector(value: Vector) -> list[float]:
    return [round(component, 6) for component in value]


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(scene: bpy.types.Scene, camera: bpy.types.Object, target: Path, location: Vector, center: Vector, height: float) -> None:
    camera.location = location
    look_at(camera, center)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = height * 1.12
    scene.camera = camera
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    assert target.is_file() and target.stat().st_size > 10_000, target


assert SOURCE_LIBRARY.is_file(), SOURCE_LIBRARY
assert STAGE_LIBRARY.is_file(), STAGE_LIBRARY
assert Path(bpy.data.filepath).resolve() == STAGE_LIBRARY.resolve(), bpy.data.filepath
assert sha256(STAGE_LIBRARY) == INITIAL_SHA256, "The staging copy was already changed; recreate it from the source library before rerunning."
assert sha256(SOURCE_LIBRARY) == INITIAL_SHA256, "The validated source library changed unexpectedly."

scene = bpy.data.scenes.get(SOURCE_SCENE)
assert scene is not None, [candidate.name for candidate in bpy.data.scenes]
bpy.context.window.scene = scene
scene.frame_set(1)
bpy.context.view_layer.update()

armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
meshes = [obj for obj in scene.objects if obj.type == "MESH"]
assert len(armatures) == 1, [obj.name for obj in armatures]
assert meshes
armature = armatures[0]
assert all(armature.pose.bones.get(name) for pair in ARM_PAIRS for name in pair)

weapon_signals: list[dict[str, object]] = []
for obj in meshes:
    names = [obj.name, obj.data.name]
    names.extend(slot.material.name for slot in obj.material_slots if slot.material)
    lowered = " ".join(names).lower()
    matched = [signal for signal in WEAPON_SIGNALS if signal in lowered]
    if matched:
        weapon_signals.append({"object": obj.name, "signals": matched, "names": names})
assert not weapon_signals, weapon_signals

# Freeze the validated frame-one body pose, detach animation, then replace the
# raised right arm with a true X-axis matrix reflection of the relaxed left arm.
frozen_pose = {bone.name: bone.matrix.copy() for bone in armature.pose.bones}
left_arm_pose = {left: armature.pose.bones[left].matrix.copy() for left, _right in ARM_PAIRS}
if armature.animation_data:
    armature.animation_data_clear()
bpy.context.view_layer.update()

def depth(pose_bone: bpy.types.PoseBone) -> int:
    value = 0
    parent = pose_bone.parent
    while parent:
        value += 1
        parent = parent.parent
    return value

for pose_bone in sorted(armature.pose.bones, key=depth):
    pose_bone.matrix = frozen_pose[pose_bone.name]
bpy.context.view_layer.update()

reflection = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
for left_name, right_name in ARM_PAIRS:
    right_pose_bone = armature.pose.bones[right_name]
    right_data_bone = right_pose_bone.bone
    desired_pose_matrix = reflection @ left_arm_pose[left_name] @ reflection
    conversion_arguments = {}
    if right_pose_bone.parent:
        conversion_arguments = {
            "parent_matrix": right_pose_bone.parent.matrix,
            "parent_matrix_local": right_data_bone.parent.matrix_local,
        }
    right_pose_bone.matrix_basis = right_data_bone.convert_local_to_pose(
        desired_pose_matrix,
        right_data_bone.matrix_local,
        invert=True,
        **conversion_arguments,
    )
    bpy.context.view_layer.update()
bpy.context.view_layer.update()

scene.name = STAGE_SCENE
armature.name = "PREP_Cyberpunk_Civilian_Neutral_Rig"
armature.data.name = "PREP_Cyberpunk_Civilian_Neutral_Armature"

# Scale and ground the complete imported hierarchy through its single model root.
model_roots = [
    obj for obj in scene.objects
    if obj.parent is None and obj.type == "EMPTY" and any(child == armature or armature in child.children_recursive for child in obj.children_recursive)
]
if not model_roots:
    model_roots = [obj for obj in scene.objects if obj.parent is None and obj.type == "EMPTY"]
assert len(model_roots) == 1, [obj.name for obj in model_roots]
model_root = model_roots[0]

minimum_before, maximum_before = evaluated_bounds(scene, meshes)
height_before = maximum_before.z - minimum_before.z
assert height_before > 0.1
scale_factor = TARGET_HEIGHT_M / height_before
model_root.scale = tuple(component * scale_factor for component in model_root.scale)
bpy.context.view_layer.update()
minimum_scaled, maximum_scaled = evaluated_bounds(scene, meshes)
model_root.location.z -= minimum_scaled.z
bpy.context.view_layer.update()
minimum, maximum = evaluated_bounds(scene, meshes)
height = maximum.z - minimum.z

# Remove the old review camera/lights and build deterministic review lighting.
for obj in list(scene.objects):
    if obj.type in {"CAMERA", "LIGHT"} or obj.name == "PREP_REVIEW_GROUND":
        bpy.data.objects.remove(obj, do_unlink=True)

scene.world = scene.world or bpy.data.worlds.new("PREP_CYBERPUNK_NEUTRAL_WORLD")
scene.world.color = (0.025, 0.035, 0.05)
for name, location, energy, size in (
    ("PREP_Key", (2.4, -3.4, 3.0), 850.0, 3.0),
    ("PREP_Fill", (-2.4, -1.0, 2.0), 500.0, 2.5),
    ("PREP_Rim", (0.0, 2.5, 2.8), 650.0, 2.0),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    look_at(light, (minimum + maximum) * 0.5)

bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.0, 0.0, -0.003))
ground = bpy.context.object
ground.name = "PREP_REVIEW_GROUND"
ground_material = bpy.data.materials.new("PREP_REVIEW_GROUND_MAT")
ground_material.diffuse_color = (0.035, 0.045, 0.06, 1.0)
ground.data.materials.append(ground_material)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "PREP_Cyberpunk_Neutral_Review_Camera"
center = (minimum + maximum) * 0.5
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 720
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False

render_view(
    scene, camera, FRONT_RENDER,
    Vector((center.x, minimum.y - height * 2.8, center.z)), center, height,
)
render_view(
    scene, camera, SIDE_RENDER,
    Vector((maximum.x + height * 2.8, center.y, center.z)), center, height,
)

left_hand_local = armature.pose.bones["CC_Base_L_Hand_055"].head.copy()
right_hand_local = armature.pose.bones["CC_Base_R_Hand_083"].head.copy()
left_hand = armature.matrix_world @ left_hand_local
right_hand = armature.matrix_world @ right_hand_local
left_shoulder = armature.matrix_world @ armature.pose.bones["CC_Base_L_Upperarm_050"].head
right_shoulder = armature.matrix_world @ armature.pose.bones["CC_Base_R_Upperarm_078"].head
uniform_scale = sum(armature.matrix_world.to_scale()) / 3.0
symmetry_error = (reflection @ left_hand_local.to_4d() - right_hand_local.to_4d()).to_3d().length * uniform_scale
max_vertex_groups = max(len(vertex.groups) for obj in meshes for vertex in obj.data.vertices)

checks = {
    "heightWithin2cm": abs(height - TARGET_HEIGHT_M) <= 0.02,
    "feetWithin2cmOfFloor": abs(minimum.z) <= 0.02,
    "bothHandsBelowShoulders": left_hand.z < left_shoulder.z and right_hand.z < right_shoulder.z,
    "handMirrorErrorWithin2cm": symmetry_error <= 0.02,
    "weaponSignalsAbsent": not weapon_signals,
    "animationDetached": armature.animation_data is None,
    "maximumFourWeightsPerVertex": max_vertex_groups <= 4,
}
assert all(checks.values()), checks

scene["PREP_status"] = "neutral-stage-validated"
scene["PREP_source_library"] = str(SOURCE_LIBRARY)
scene["PREP_target_height_m"] = TARGET_HEIGHT_M
scene["PREP_matrix_mirror_axis"] = "armature-local-X"
scene["PREP_updated_at"] = datetime.now(timezone.utc).isoformat()
bpy.ops.wm.save_as_mainfile(filepath=str(STAGE_LIBRARY), compress=True)

report = {
    "status": "validated-neutral-stage",
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "source": {"path": str(SOURCE_LIBRARY), "sha256": INITIAL_SHA256, "preserved": True},
    "stage": {"path": str(STAGE_LIBRARY), "bytes": STAGE_LIBRARY.stat().st_size, "sha256": sha256(STAGE_LIBRARY)},
    "scene": scene.name,
    "armature": armature.name,
    "meshObjects": len(meshes),
    "heightBeforeMeters": round(height_before, 6),
    "scaleFactor": round(scale_factor, 9),
    "boundsMeters": {"minimum": vector(minimum), "maximum": vector(maximum), "height": round(height, 6)},
    "pose": {
        "method": "freeze-frame-1-and-reflect-left-arm-matrices-across-armature-local-X",
        "pairs": [{"left": left, "right": right} for left, right in ARM_PAIRS],
        "leftHand": vector(left_hand), "rightHand": vector(right_hand),
        "leftShoulder": vector(left_shoulder), "rightShoulder": vector(right_shoulder),
        "handMirrorErrorMeters": round(symmetry_error, 6),
    },
    "animation": {"action": None, "nlaTracks": []},
    "maxVertexGroups": max_vertex_groups,
    "weaponSignals": weapon_signals,
    "renders": {"front": str(FRONT_RENDER), "side": str(SIDE_RENDER)},
    "checks": checks,
    "integration": "staging-only; master and public runtime asset intentionally unchanged pending visual review and Remy/Mixamo retarget",
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PREP_STAGE_RESULT=" + json.dumps(report, ensure_ascii=False, separators=(",", ":")))
