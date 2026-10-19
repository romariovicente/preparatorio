"""Add the inactive macro planning scene. Execute inside the preserved master.

No existing scene, object, mesh, armature, action, GLB or runtime file is edited.
This script intentionally does not render, save the .blend, or export GLBs.
The operator inspects the scene and saves the next master version separately.
"""
import bpy
import hashlib
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(globals().get("PREP_PROJECT_ROOT", r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio"))
CONFIG = ROOT / "frontend/src/config/macroWorldPlan.json"
REPORT = ROOT / "reports/PLANO_MACRO_20261014.json"
SCENE_NAME = "PREP_MACRO_BLOCKOUT_20261014"
PREFIX = "MACRO14_"
raw_config = CONFIG.read_bytes()
plan = json.loads(raw_config.decode("utf-8-sig"))
config_sha = hashlib.sha256(raw_config).hexdigest()
assert plan["runtimeEnabled"] is False and plan["status"] == "planning-only"
assert plan["legacy"]["transform"]["scale"] == [1, 1, 1]
if bpy.data.scenes.get(SCENE_NAME):
    raise RuntimeError("Macro scene already exists; inspect it instead of deleting or rebuilding it.")


def existing_signature():
    """Fingerprint original transforms and datablock links, not new prototypes."""
    entries = []
    for obj in sorted(original_objects, key=lambda item: item.name):
        entries.append({"name": obj.name, "type": obj.type,
                        "matrix": [list(row) for row in obj.matrix_world],
                        "parent": obj.parent.name if obj.parent else None,
                        "data": obj.data.name if obj.data else None,
                        "collections": sorted(col.name for col in obj.users_collection),
                        "hidden": [obj.hide_viewport, obj.hide_render],
                        "action": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None})
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


original_objects = list(bpy.data.objects)
original_scenes = list(bpy.data.scenes)
original_scene_names = [item.name for item in original_scenes]
original_signature = existing_signature()
scene = bpy.data.scenes.new(SCENE_NAME)
scene["status"] = "INACTIVE_PLANNING_PROTOTYPE"
scene["runtime_enabled"] = False
scene["source_config_sha256"] = config_sha
scene["preservation"] = "Separate scene. Existing 260 m terrain and 236 m playable area stay at scale 1."
scene["limitations"] = "Conceptual volumes; no road traffic, operating coast/airport, completed interiors or clinical compliance."
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = "METERS"
cols = {}
for name in ["WORLD", "DISTRICTS", "ROADS", "LOTS", "BUILDINGS", "INTERIORS", "FURNITURE", "INTERACTIONS", "EDUCATIONAL", "MULTIPLAYER"]:
    col = bpy.data.collections.new(PREFIX + name)
    col["logical_layer"] = name
    col["runtime_enabled"] = False
    scene.collection.children.link(col)
    cols[name] = col
for name in ["TERRAIN", "WATER", "LIGHTING", "NAVIGATION"]:
    col = bpy.data.collections.new(PREFIX + name)
    cols["WORLD"].children.link(col)
    cols[name] = col


def color(hex_color):
    text = hex_color.lstrip("#")
    channels = [int(text[index:index + 2], 16) / 255 for index in [0, 2, 4]]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels) + (1.0,)


def material(name, hex_color):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = color(hex_color)
    mat.use_nodes = True
    node = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    node.inputs["Base Color"].default_value = mat.diffuse_color
    node.inputs["Roughness"].default_value = 0.85
    return mat


mats = {name: material(name, shade) for name, shade in {
    "TERRAIN": "#b8c1b2", "WATER": "#277d9b", "ROW": "#868a83",
    "ASPHALT": "#313b42", "SIDEWALK": "#d3d4c8", "CYCLE": "#ad5057",
    "MEDIAN": "#737f67", "INK": "#172d40", "WHITE": "#eeeeea",
    "LOT": "#aeb69f", "BUILDING": "#d8e6e3", "LEGACY": "#82939a",
    "CAUTION": "#dd854b", "PUBLIC": "#3688c6", "EMERGENCY": "#d75662",
    "SERVICE": "#906aab", "HELIPAD": "#739b81"}.items()}


def box(name, center, size, collection, mat, rotation=0.0, props=None):
    dx, dy, dz = (value / 2 for value in size)
    vertices = [(x, y, z) for z in [-dz, dz] for y in [-dy, dy] for x in [-dx, dx]]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    mesh = bpy.data.meshes.new(PREFIX + name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    collection.objects.link(obj)
    obj.location = center
    obj.rotation_euler.z = rotation
    obj.data.materials.append(mat)
    obj["runtime_enabled"] = False
    obj["prototype"] = True
    for key, value in (props or {}).items():
        obj[key] = value
    return obj


def xz_box(name, center, width, depth, height, bottom, collection, mat, props=None):
    return box(name, (center[0], -center[1], bottom + height / 2), (width, depth, height), collection, mat, props=props)


def label(name, text, center, size=22, height=35, collection=None, mat=None):
    curve = bpy.data.curves.new(PREFIX + name, "FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.01
    obj = bpy.data.objects.new(PREFIX + name, curve)
    (collection or cols["NAVIGATION"]).objects.link(obj)
    obj.location = (center[0], -center[1], height if name == "HELIPAD_H" else 0.65)
    curve.materials.append(mat or mats["INK"])
    obj["runtime_enabled"] = False
    return obj


def strip(name, start, end, width, offset, bottom, height, mat, collection=None, props=None):
    x1, y1 = start[0], -start[1]
    x2, y2 = end[0], -end[1]
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    assert length > 0 and width > 0
    nx, ny = -dy / length, dx / length
    return box(name, ((x1 + x2) / 2 + nx * offset, (y1 + y2) / 2 + ny * offset, bottom + height / 2),
               (length, width, height), collection or cols["ROADS"], mat,
               math.atan2(dy, dx), props)


world = plan["world"]
xz_box("TERRAIN_4000m_PLANNING_ONLY", [0, 0], *world["terrainSize"], 0.25,
       world["terrainElevation"] - 0.25, cols["TERRAIN"], mats["TERRAIN"])
water = world["coastalWater"]
b = water["bounds"]
xz_box("WATER_RESERVE_NOT_OPERATING_COAST", [(b["minX"] + b["maxX"]) / 2, (b["minZ"] + b["maxZ"]) / 2],
       b["maxX"] - b["minX"], b["maxZ"] - b["minZ"], 0.1, water["surfaceY"] - 0.1, cols["WATER"], mats["WATER"])
for district in plan["districts"]:
    col = bpy.data.collections.new(PREFIX + district["collection"])
    cols["DISTRICTS"].children.link(col)
    col["district_id"] = district["id"]
    col["phase"] = district["phase"]
    col["runtime_enabled"] = False
    district_mat = material("DISTRICT_" + district["id"], district["color"])
    xz_box("DISTRICT_" + district["id"], district["center"], *district["size"], 0.08, -0.5, col, district_mat,
           {"district_id": district["id"], "phase": district["phase"]})
    short = {"legacy-central": "NÚCLEO PRESERVADO\n236 m jogáveis", "hospital": "SAÚDE / HOSPITAL",
             "university": "UNIVERSIDADE", "downtown": "COMÉRCIO / SERVIÇOS", "residential": "RESIDENCIAL",
             "industrial": "INDÚSTRIA / LOGÍSTICA", "airport": "AEROPORTO / RESERVA",
             "beach": "PRAIA / RESERVA", "marina": "MARINA / RESERVA",
             "expansion-north": "EXPANSÃO NORTE", "expansion-south": "EXPANSÃO SUL"}[district["id"]]
    label("LABEL_" + district["id"], short, [district["center"][0], district["center"][1] - district["size"][1] * 0.32], 24)

# Only a footprint proxy for the legacy district, without linking detailed assets.
for edge, start, end in [
    ("N", [-130, -130], [130, -130]), ("S", [-130, 130], [130, 130]),
    ("W", [-130, -130], [-130, 130]), ("E", [130, -130], [130, 130])]:
    strip("LEGACY_260m_OUTLINE_" + edge, start, end, 2, 0, 0.15, 0.12, mats["WHITE"], cols["DISTRICTS"])

road_segment_count = cycle_band_count = 0
for road in plan["roads"]:
    profile = plan["roadProfiles"][road["profile"]]
    for index, (start, end) in enumerate(zip(road["points"], road["points"][1:])):
        name = "ROAD_" + road["id"] + "_" + str(index)
        props = {"road_id": road["id"], "profile": road["profile"], "segment_index": index,
                 "from_xz": start, "to_xz": end, "right_of_way_m": profile["rightOfWayWidth"]}
        strip(name + "_ROW", start, end, profile["rightOfWayWidth"], 0, -0.05, 0.15, mats["ROW"], props=props)
        carriage = profile["drivableWidth"] + profile["medianWidth"]
        strip(name + "_ASPHALT", start, end, carriage, 0, 0.10, 0.08, mats["ASPHALT"], props=props)
        if profile["medianWidth"]:
            strip(name + "_MEDIAN", start, end, profile["medianWidth"], 0, 0.18, 0.08, mats["MEDIAN"])
        for side in [-1, 1]:
            offset = carriage / 2
            for kind, field, mat in [("SHOULDER", "shoulderWidthEachSide", mats["ROW"]),
                                     ("CYCLE", "cycleWidthEachSide", mats["CYCLE"]),
                                     ("SIDEWALK", "sidewalkWidthEachSide", mats["SIDEWALK"])]:
                width = profile[field]
                if width:
                    strip(name + "_" + kind + "_" + str(side), start, end, width, side * (offset + width / 2),
                          0.18, 0.06, mat, props={"road_id": road["id"], "band_role": kind, "width_m": width})
                    offset += width
                    if kind == "CYCLE":
                        cycle_band_count += 1
        road_segment_count += 1

for lot in plan["lots"]:
    props = {"lot_id": lot["id"], "district_id": lot["districtId"], "role": lot["role"]}
    xz_box("LOT_" + lot["id"], lot["center"], *lot["size"], 0.10, 0.0, cols["LOTS"], mats["LOT"], props)
    width, height, depth = lot["buildingSize"]
    xz_box("BUILDING_" + lot["id"], lot["center"], width, depth, height, 0.15, cols["BUILDINGS"],
           mats["ASPHALT"] if lot["role"] == "runway-reserve" else mats["BUILDING"], props)
    if "approach" in lot:
        xz_box("ARRIVAL_" + lot["id"], lot["approach"], 6, 6, 0.25, 0.2, cols["INTERACTIONS"], mats["PUBLIC"], props)
        strip("PEDESTRIAN_APPROACH_" + lot["id"], lot["approach"], lot["entrance"], 3.2, 0, 0.20, 0.1,
              mats["PUBLIC"], cols["LOTS"], {"planning_only": True, "not_physical_door": True})

# Hospital external reservations fit its lot. Their dimensions are game targets.
xz_box("HOSPITAL_PARKING_RESERVE", [445, 380], 90, 28, 0.08, 0.16, cols["LOTS"], mats["ASPHALT"])
xz_box("HOSPITAL_AMBULANCE_BAYS_RESERVE", [585, 375], 32, 16, 0.12, 0.20, cols["LOTS"], mats["EMERGENCY"])
xz_box("HOSPITAL_TECHNICAL_LOADING_RESERVE", [585, 310], 32, 22, 0.12, 0.20, cols["LOTS"], mats["SERVICE"])
xz_box("HOSPITAL_HELIPAD_NON_OPERATIONAL_RESERVE", [540, 300], 26, 26, 0.18, 24.2,
       cols["BUILDINGS"], mats["HELIPAD"], {"operational": False, "clinical_or_aeronautic_compliance": False})
label("HELIPAD_H", "H", [540, 300], 13, 24.45, cols["BUILDINGS"], mats["WHITE"])
for phase in plan["hospitalPhases"]:
    col = bpy.data.collections.new(PREFIX + phase["id"].upper().replace("-", "_"))
    cols["INTERIORS"].children.link(col)
    col["status"] = "UNBUILT_SECTOR_RESERVATION"
    col["planned_sectors"] = "; ".join(phase["sectors"])
    col["interaction_families"] = "; ".join(phase["interactionFamilies"])
for index, family in enumerate(plan["hospitalPhases"][0]["interactionFamilies"]):
    empty = bpy.data.objects.new(PREFIX + "EDU_RESERVE_" + str(index), None)
    cols["EDUCATIONAL"].objects.link(empty)
    empty.location = (450 + index * 16, -330, 1.7)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = 0.4
    empty["interaction_family"] = family
    empty["implemented"] = False
    empty["runtime_enabled"] = False
gathering = bpy.data.objects.new(PREFIX + "MULTIPLAYER_RECEPCAO_RESERVE", None)
cols["MULTIPLAYER"].objects.link(gathering)
gathering.location = (500, -350, 0)
gathering.empty_display_type = "CIRCLE"
gathering.empty_display_size = 8
gathering["waiting_clearance_target_m"] = plan["humanScale"]["multiplayerWaitingClearance"]
gathering["capacity_tested"] = False

# Keep the legacy marker identifier while reflecting the revised land route.
label("COAST_UNRESOLVED", "RESERVA COSTEIRA\nvia recuada; 10 m livres entre faixa viária e água", [350, 1870], 24, 40, mat=mats["WHITE"])
label("WORLD_TITLE", "PREPARATÓRIO — PLANO MACRO 4 × 4 km\nCENA SEPARADA / PROTÓTIPO INATIVO", [0, -1860], 34, 40)
strip("SCALE_500m", [-1550, 1890], [-1050, 1890], 6, 0, 0.4, 0.15, mats["INK"], cols["NAVIGATION"])
label("SCALE_LABEL", "500 m", [-1300, 1850], 23, 35)


def camera(name, location, target, ortho_scale):
    data = bpy.data.cameras.new(PREFIX + name)
    obj = bpy.data.objects.new(PREFIX + name, data)
    cols["LIGHTING"].objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.type = "ORTHO"
    data.ortho_scale = ortho_scale
    data.clip_end = 20000
    return obj


scene.camera = camera("CAM_OVERVIEW", (0, 0, 5000), (0, 0, 0), 4750)
camera("CAM_OBLIQUE", (3500, -4200, 4200), (0, 0, 0), 6400)
camera("CAM_HOSPITAL", (720, -650, 210), (500, -325, 10), 325)
sun_data = bpy.data.lights.new(PREFIX + "SUN", "SUN")
sun_data.energy = 1.5
sun_data.use_shadow = False
sun = bpy.data.objects.new(PREFIX + "SUN", sun_data)
cols["LIGHTING"].objects.link(sun)
sun.rotation_euler = (0.55, -0.35, -0.4)
scene.world = bpy.data.worlds.new(PREFIX + "WORLD_LIGHT")
scene.world.use_nodes = True
background = next(node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND")
background.inputs[0].default_value = (0.55, 0.62, 0.7, 1)
background.inputs[1].default_value = 0.5
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 1400
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"

after_signature = existing_signature()
assert after_signature == original_signature, "An original object changed; do not save over any master."
assert all(item.name in bpy.data.scenes for item in original_scenes)
new_meshes = [obj for obj in scene.objects if obj.type == "MESH"]
scene_mesh_triangles = sum(sum(len(face.vertices) - 2 for face in obj.data.polygons) for obj in new_meshes)
report = json.loads(REPORT.read_text(encoding="utf-8-sig")) if REPORT.exists() else {}
report["blockoutExecution"] = {
    "scene": scene.name, "status": "generated-awaiting-visual-inspection-and-versioned-save",
    "runtimeEnabled": False, "metricScaleLength": scene.unit_settings.scale_length,
    "sourceConfigSha256": config_sha, "previousFilepath": bpy.data.filepath,
    "preservedSceneCount": len(original_scenes), "preservedObjectCount": len(original_objects),
    "originalObjectsFingerprintBefore": original_signature, "originalObjectsFingerprintAfter": after_signature,
    "newObjectCount": len(scene.objects), "newMeshCount": len(new_meshes),
    "meshTrianglesOnly": scene_mesh_triangles, "fontObjectsExcludedFromTriangleCount": True,
    "roadSegments": road_segment_count, "cycleBands": cycle_band_count,
    "prototypeLotCount": len(plan["lots"]), "prototypeDistrictCount": len(plan["districts"]),
    "originalScenesStillPresent": original_scene_names,
    "limitations": ["Not exported to runtime", "Not rendered by this script", "Not saved by this script",
                    "Coast remains a non-operating reserve", "Hospital interiors are sector reservations only"]}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
if bpy.context.window:
    bpy.context.window.scene = scene
print("PREP_MACRO_BLOCKOUT_READY " + json.dumps({"scene": scene.name, "objects": len(scene.objects),
      "roadSegments": road_segment_count, "cycleBands": cycle_band_count, "runtimeEnabled": False,
      "originalObjectsPreserved": original_signature == after_signature}, ensure_ascii=False))
