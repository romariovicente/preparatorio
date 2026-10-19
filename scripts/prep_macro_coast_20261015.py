"""Move the inactive macro roads onto land, without rebuilding any scene."""
import bpy
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from mathutils import Vector

ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261015.blend"
CONFIG = ROOT / "frontend/src/config/macroWorldPlan.json"
REPORT = ROOT / "reports/PLANO_MACRO_20261014.json"
old = json.loads((ROOT / "art/blender/checkpoints/MACRO_BEFORE_COAST_20261015.json").read_text(encoding="utf-8-sig"))
plan = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
assert Path(bpy.data.filepath).resolve() == MASTER.resolve()
scene = bpy.data.scenes["PREP_MACRO_BLOCKOUT_20261014"]
assert scene.get("runtime_enabled") is False and plan["runtimeEnabled"] is False
assert not scene.get("coast_land_route_revised"), "Already revised; inspect before repeating."
report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
original = sorted([o for o in bpy.data.objects if not o.name.startswith("MACRO14_")], key=lambda o:o.name)
def signature():
    data = [{"name": o.name,"type":o.type,"matrix":[list(row) for row in o.matrix_world],
             "parent":o.parent.name if o.parent else None,"data":o.data.name if o.data else None,
             "collections":sorted(c.name for c in o.users_collection),"hidden":[o.hide_viewport,o.hide_render],
             "action":o.animation_data.action.name if o.animation_data and o.animation_data.action else None} for o in original]
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
before = signature()
assert before == report["blockoutExecution"]["originalObjectsFingerprintBefore"]
def bands(profile):
    carriage = profile["drivableWidth"] + profile["medianWidth"]
    result = [("_ROW",profile["rightOfWayWidth"],0),("_ASPHALT",carriage,0)]
    if profile["medianWidth"]:
        result.append(("_MEDIAN",profile["medianWidth"],0))
    for side in (-1,1):
        offset = carriage / 2
        for kind,field in [("SHOULDER","shoulderWidthEachSide"),("CYCLE","cycleWidthEachSide"),("SIDEWALK","sidewalkWidthEachSide")]:
            width = profile[field]
            if width:
                result.append(("_"+kind+"_"+str(side),width,side*(offset+width/2)))
                offset += width
    return result
def placement(start,end,offset):
    a,b = Vector((start[0],-start[1])),Vector((end[0],-end[1]))
    delta = b-a
    normal = Vector((-delta.y,delta.x)).normalized()
    return (a+b)/2+normal*offset,delta.length,math.atan2(delta.y,delta.x)
changes = []
pending = []
old_by_id = {r["id"]:r for r in old["roads"]}
for road in plan["roads"]:
    prior = old_by_id[road["id"]]
    assert road["profile"] == prior["profile"] and len(road["points"]) == len(prior["points"])
    for index,(start,end) in enumerate(zip(road["points"],road["points"][1:])):
        old_start,old_end = prior["points"][index:index+2]
        if (start,end) == (old_start,old_end):
            continue
        assert road["id"] in ("peripheral-ring","west-spine","east-spine")
        for suffix,width,offset in bands(plan["roadProfiles"][road["profile"]]):
            name = "MACRO14_ROAD_"+road["id"]+"_"+str(index)+suffix
            obj = bpy.data.objects[name]
            old_center,old_length,old_angle = placement(old_start,old_end,offset)
            assert (Vector(obj.location[:2])-old_center).length < 0.01, "Preserve unexpected user positioning: "+name
            assert abs(obj.rotation_euler.z-old_angle) < 0.001
            assert max(abs(v-1) for v in obj.scale) < 0.0001
            assert abs(obj.dimensions.x-old_length) < 0.1 or abs(obj.dimensions.y-old_length) < 0.1
            center,length,angle = placement(start,end,offset)
            pending.append((obj,center,length,angle,start,end))
        changes.append({"road":road["id"],"segment":index,"oldFrom":old_start,"oldTo":old_end,"from":start,"to":end})
assert len(changes) == 5 and len(pending) == 27
for obj,center,length,angle,start,end in pending:
    obj.location.x,obj.location.y = center
    obj.rotation_euler.z = angle
    for vertex in obj.data.vertices:
        vertex.co.x = math.copysign(length/2,vertex.co.x)
    obj.data.update()
    if "from_xz" in obj:
        obj["from_xz"],obj["to_xz"] = start,end
scene["coast_land_route_revised"] = True
scene["source_config_sha256"] = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
scene["limitations"] = "Inactive conceptual scene: buildings and hospital sectors reserved; coast and airport not operational."
label = bpy.data.objects["MACRO14_COAST_UNRESOLVED"]
label.data.body = "RESERVA COSTEIRA\nvia recuada; 10 m livres entre faixa viária e água"
label["coastal_road_conflict_resolved"] = True
# Inspect the actual transformed road vertices, including sidewalks/cycle bands.
bpy.context.view_layer.update()
water = plan["world"]["coastalWater"]["bounds"]
intersections = []
nearest = float("inf")
road_meshes = [o for o in scene.objects if o.type == "MESH" and o.name.startswith("MACRO14_ROAD_")]
for obj in road_meshes:
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    min_x,max_x = min(p.x for p in points),max(p.x for p in points)
    min_z,max_z = min(-p.y for p in points),max(-p.y for p in points)
    if min_x <= water["maxX"] and max_x >= water["minX"]:
        if max_z >= water["minZ"] and min_z <= water["maxZ"]:
            intersections.append(obj.name)
        elif max_z < water["minZ"]:
            nearest = min(nearest,water["minZ"]-max_z)
assert not intersections and abs(nearest-10) < 0.05, (intersections,nearest)
assert signature() == before
renders = []
for suffix,camera in [("costa_visao_geral","MACRO14_CAM_OVERVIEW"),("costa_perspectiva","MACRO14_CAM_OBLIQUE")]:
    path = ROOT / ("reports/mapa_macro_"+suffix+"_20261015.png")
    assert not path.exists(), "Preserve the earlier render instead of overwriting it."
    scene.camera = bpy.data.objects[camera]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True,scene=scene.name)
    renders.append(str(path))
scene.camera = bpy.data.objects["MACRO14_CAM_OBLIQUE"]
for window in bpy.context.window_manager.windows:
    window.scene = scene
    for area in window.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
execution = report["blockoutExecution"]
execution.update({"sourceConfigSha256":scene["source_config_sha256"],"savedBytes":MASTER.stat().st_size,
                  "saveTimeLocal":datetime.now().isoformat(timespec="seconds"),"status":"saved-coastal-correction-awaiting-render-review",
                  "limitations":["Inactive scene; not exported to runtime","Conceptual building volumes; hospital interiors reserved only","No claim of traffic or CTB compliance"]})
result = {"changedSegments":changes,"updatedMeshes":len(pending),"roadMeshCountChecked":len(road_meshes),
          "waterIntersections":intersections,"nearestRightOfWayClearanceMeters":nearest,
          "legacyFingerprintBefore":before,"legacyFingerprintAfter":signature(),"previews":renders,
          "master":str(MASTER),"savedBytes":MASTER.stat().st_size,"timeLocal":execution["saveTimeLocal"]}
report["coastalCorrection20261015"] = result
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"reports/BLENDER_COAST_20261015.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("PREP_COAST_REVISED "+json.dumps(result,ensure_ascii=False))
