"""Read-only independent reopening QA of the final Oct16 Blender master.

PREPARED ONLY: execute after the root confirms DELIVERY_SAVED and its snapshot.
Launch a separate Blender 5.2 process (never the live MCP session):
  blender --background --disable-autoexec MASTER --python-exit-code 1 --python SCRIPT

No scene switching, frame evaluation, imports, rendering, repairs or .blend saves.
Stored channels use the existing prep_object_state_20261015 helper EXACTLY.
Mismatch names/channels and expected/actual values are retained in the JSON.
"""

import bpy
import hashlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER = ROOT / "art/blender/PREPARATORIO_PROJETO_20261016.blend"
SAVED = ROOT / "reports/DELIVERY_SAVED_20261016.json"
SNAPSHOT = ROOT / "art/blender/checkpoints/DELIVERY_SAVED_STATE_20261016.json"
REPORT = ROOT / "reports/DELIVERY_READBACK_20261016.json"
LOG = ROOT / "reports/DELIVERY_READBACK_20261016.log"
OWNER = "prep_delivery_readback_20261016_v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def log(message):
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(now() + " " + message + "\n")


def entries(path):
    value = read_json(path)
    result = value if isinstance(value, list) else value["entries"]
    assert isinstance(result, list), str(path)
    return result


def channel_differences(expected, actual, prefix=""):
    """Exact recursive diff; there is deliberately no numeric tolerance."""
    differences = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            field = prefix + "." + key if prefix else key
            if key not in expected:
                differences.append(dict(channel=field, kind="unexpected", actual=actual[key]))
            elif key not in actual:
                differences.append(dict(channel=field, kind="missing", expected=expected[key]))
            else:
                differences.extend(channel_differences(expected[key], actual[key], field))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            differences.append(dict(channel=prefix + ".length", expected=len(expected), actual=len(actual)))
        for index in range(min(len(expected), len(actual))):
            differences.extend(channel_differences(expected[index], actual[index], prefix + "[" + str(index) + "]"))
    elif type(expected) is not type(actual) or expected != actual:
        differences.append(dict(channel=prefix, expected=expected, actual=actual,
                                expectedType=type(expected).__name__, actualType=type(actual).__name__))
    return differences


def state_differences(expected, actual):
    common = sorted(set(expected) & set(actual))
    changed = []
    for name in common:
        channels = channel_differences(expected[name], actual[name])
        if channels:
            changed.append(dict(object=name, channels=channels))
    return dict(missingObjects=sorted(set(expected) - set(actual)),
                unexpectedObjects=sorted(set(actual) - set(expected)),
                changedObjects=changed,
                changedObjectCount=len(changed),
                changedChannelCount=sum(len(item["channels"]) for item in changed))


def mesh_counts(scene):
    meshes = [obj for obj in scene.objects if obj.type == "MESH"
              and not any(collection.name.startswith("glTF_not_exported") for collection in obj.users_collection)]
    return dict(meshes=len(meshes), vertices=sum(len(obj.data.vertices) for obj in meshes),
                triangles=sum(len(face.vertices) - 2 for obj in meshes for face in obj.data.polygons))


def public_file(url):
    root = (ROOT / "frontend/public").resolve()
    target = (root / url.lstrip("/")).resolve()
    assert target.is_relative_to(root), "Asset path escaped public folder: " + url
    return target


def run():
    report = dict(owner=OWNER, startedAt=now(), status="running", passed=False,
        master=str(MASTER), blenderVersion=bpy.app.version_string,
        background=bool(bpy.app.background), autoexecDisabledByCLI=False,
        checks=[], failures=[], masterModifiedByReadback=False,
        noRendering=True, noFrameEvaluation=True, noMovementRetest=True)

    def check(label, condition, expected=None, actual=None, details=None):
        result = dict(name=label, passed=bool(condition))
        if expected is not None:
            result["expected"] = expected
        if actual is not None:
            result["actual"] = actual
        if details is not None:
            result["details"] = details
        report["checks"].append(result)
        if not condition:
            report["failures"].append(result)
        log(("PASS " if condition else "FAIL ") + label +
            (" " + json.dumps({"expected": expected, "actual": actual}, ensure_ascii=False) if not condition else ""))
        return bool(condition)

    def stage(label, function):
        try:
            return function()
        except Exception:
            error = traceback.format_exc()
            check(label, False, details=error)
            return None

    def scene(name, label):
        found = bpy.data.scenes.get(name)
        check(label + ".scene_exists", found is not None, expected=name,
              actual=found.name if found else None)
        return found

    def verify_stats(target_scene, expected, label):
        actual = mesh_counts(target_scene)
        for key in ("meshes", "vertices", "triangles"):
            if key in expected:
                check(label + "." + key, actual[key] == expected[key], expected[key], actual[key])
        return actual

    # Refuse execution in the live Blender/MCP process or under an unexpected
    # executable/file. Only the separate background reopen is authorized.
    assert bpy.app.background, "Background-only readback; never execute in the live MCP session"
    assert bpy.app.version[:2] == (5, 2), "Expected Blender 5.2, got " + bpy.app.version_string
    assert Path(bpy.data.filepath).resolve() == MASTER.resolve(), "Unexpected opened .blend"
    assert "--disable-autoexec" in sys.argv or "-Y" in sys.argv, "Explicit --disable-autoexec is required"
    assert "--python-exit-code" in sys.argv and sys.argv[sys.argv.index("--python-exit-code") + 1] == "1", "Launch with --python-exit-code 1"
    report["autoexecDisabledByCLI"] = True
    initial_stat = MASTER.stat()
    report["masterSha256Before"] = sha(MASTER)
    report["masterBytesBefore"] = initial_stat.st_size
    log("RUN START independent background master readback; autoexec disabled; no mutation")
    saved, snapshot = read_json(SAVED), read_json(SNAPSHOT)
    check("saved_report.master_path", Path(saved["master"]).resolve() == MASTER.resolve(), str(MASTER), saved["master"])
    for key, actual in (("scenes", len(bpy.data.scenes)), ("objects", len(bpy.data.objects)),
                        ("materials", len(bpy.data.materials)), ("collections", len(bpy.data.collections))):
        check("saved_counts." + key, actual == saved[key], saved[key], actual)
    check("saved_master.bytes", initial_stat.st_size == saved["masterBytes"], saved["masterBytes"], initial_stat.st_size)
    report["counts"] = {key: len(getattr(bpy.data, key)) for key in ("scenes", "objects", "materials", "collections")}
    report["sceneNames"] = sorted(item.name for item in bpy.data.scenes)
    report["activeScene"] = bpy.context.scene.name if bpy.context.scene else None

    sys.path.insert(0, str(ROOT / "scripts"))
    from prep_object_state_20261015 import object_state, state_hash
    expected_state, actual_state = snapshot["state"], object_state(list(bpy.data.objects))
    expected_hash, actual_hash = state_hash(expected_state), state_hash(actual_state)
    check("snapshot.self_hash", expected_hash == snapshot["hash"], snapshot["hash"], expected_hash)
    check("snapshot.object_count", len(expected_state) == saved["objects"], saved["objects"], len(expected_state))
    difference = state_differences(expected_state, actual_state)
    report["storedObjectState"] = dict(expectedHash=snapshot["hash"], actualHash=actual_hash,
        exactMatch=actual_hash == snapshot["hash"], **difference)
    check("stored_object_channels.exact_hash", actual_hash == snapshot["hash"], snapshot["hash"], actual_hash,
          details={key: value for key, value in difference.items() if key != "changedObjects"})
    if difference["changedObjects"]:
        log("EXACT CHANNEL DIFFERENCES " + json.dumps(difference, ensure_ascii=False))

    deliveries = saved["deliveries"]
    check("deliveries.count", len(deliveries) == 13, 13, len(deliveries))
    check("deliveries.unique_ids", len({item["id"] for item in deliveries}) == len(deliveries))
    report["deliveries"] = []
    for delivery in deliveries:
        def verify_delivery(item=delivery):
            file = public_file(item["url"])
            size, digest = file.stat().st_size, sha(file)
            passed = check("file." + item["id"] + ".bytes", size == item["bytes"], item["bytes"], size)
            passed = check("file." + item["id"] + ".sha256", digest == item["sha256"], item["sha256"], digest) and passed
            report["deliveries"].append(dict(id=item["id"], url=item["url"], bytes=size, sha256=digest, passed=passed))
        stage("file." + delivery["id"], verify_delivery)

    fauna = stage("fauna.report", lambda: entries(ROOT / "reports/fauna_catalog_entries_20261016.json"))
    anatomy = stage("anatomy.report", lambda: entries(ROOT / "reports/anatomy_catalog_entries_20261016.json"))
    rail = stage("rail.report", lambda: entries(ROOT / "reports/train_catalog_entries_20261016.json"))
    station = stage("station.report", lambda: entries(ROOT / "reports/station_catalog_entries_20261016.json"))
    groups = (("fauna", fauna, 6), ("anatomy", anatomy, 4), ("rail", rail, 2), ("station", station, 1))
    combined = []
    for label, group, count in groups:
        if group is not None:
            check(label + ".entry_count", len(group) == count, count, len(group))
            combined.extend(group)
    check("catalog_reports.delivery_ids", sorted(item["id"] for item in combined) == sorted(item["id"] for item in deliveries),
          sorted(item["id"] for item in deliveries), sorted(item["id"] for item in combined))
    delivery_by_id = {item["id"]: item for item in deliveries}
    for item in combined:
        target = delivery_by_id.get(item["id"])
        check("catalog_reports." + item["id"] + ".matches_saved_delivery",
              target is not None and all(item.get(key) == target.get(key) for key in ("url", "bytes", "sha256")))

    report["faunaScenes"] = []
    for item in fauna or []:
        def verify_fauna(entry=item):
            expected = sorted(entry["boneCounts"])
            results = []
            for key in ("blenderScene", "qaScene"):
                target = scene(entry[key], entry["id"] + "." + key)
                if target:
                    armatures = [obj for obj in target.objects if obj.type == "ARMATURE"]
                    actual = sorted(len(obj.data.bones) for obj in armatures)
                    check(entry["id"] + "." + key + ".bone_counts", actual == expected, expected, actual)
                    results.append(dict(scene=target.name, armatures=[dict(name=obj.name, bones=len(obj.data.bones)) for obj in armatures]))
            report["faunaScenes"].append(dict(id=entry["id"], scenes=results))
        stage("fauna." + item["id"], verify_fauna)

    def prior_fauna_qa():
        previous = read_json(ROOT / "reports/fauna_three_20261016.json")
        check("prior_fauna_three.complete_pass", previous.get("status") == "passed" and previous.get("passedAssets") == 6,
              dict(status="passed", passedAssets=6), dict(status=previous.get("status"), passedAssets=previous.get("passedAssets")))
        report["faunaMovementEvidence"] = dict(report="reports/fauna_three_20261016.json", status=previous.get("status"),
            passedAssets=previous.get("passedAssets"), clips=sum(len(item.get("clips", [])) for item in previous.get("results", [])),
            rerun=False, reason="Prior Blender and Three movement checks passed; reopen checks stored armatures/bone counts and exact delivered bytes.")
    stage("prior_fauna_three.report", prior_fauna_qa)

    def verify_anatomy():
        qa = read_json(ROOT / "reports/ANATOMY_IMPORT_QA_20261016.json")
        check("anatomy.qa_status", qa.get("status") == "validated", "validated", qa.get("status"))
        scene(qa["scene"], "anatomy.source")
        expected = {item["id"]: item for item in qa["assets"]}
        for item in anatomy or []:
            target = scene(item["qaScene"], item["id"] + ".qa")
            if target:
                verify_stats(target, expected[item["id"]]["reimport"], item["id"] + ".saved_qa_geometry_counts")
    stage("anatomy.saved_scenes", verify_anatomy)

    def verify_rail():
        scene("PREP_RAIL_ASSETS_20261016", "rail.source")
        for item in rail or []:
            record = read_json(ROOT / "reports/rail_assets_20261016" / (item["id"] + ".json"))
            check(item["id"] + ".qa_passed", record.get("status") == "validated" and record["roundtrip"].get("passed") is True)
            scene(record["derivedScene"], item["id"] + ".derived")
            target = scene(record["roundtrip"]["scene"], item["id"] + ".qa")
            if target:
                verify_stats(target, record["roundtrip"]["stats"], item["id"] + ".saved_qa_geometry_counts")
    stage("rail.saved_scenes", verify_rail)

    def verify_station():
        qa = read_json(ROOT / "reports/STATION_IMPORT_QA_20261016.json")
        check("station.qa_status", qa.get("status") == "validated", "validated", qa.get("status"))
        for key, stats_key in (("sourceScene", "source"), ("derivativeScene", "derivative"), ("qaScene", "reimport")):
            target = scene(qa[key], "station." + key)
            if target:
                verify_stats(target, qa[stats_key], "station." + key + ".saved_geometry_counts")
    stage("station.saved_scenes", verify_station)

    def preserved_hospital():
        old = read_json(ROOT / "reports/HOSPITAL_RECEPTION_20261015.json")
        for name, count, label in ((old["scene"], old["sceneObjects"], "hospital.source"),
                                   (old["roundtrip"]["scene"], old["roundtrip"]["objects"], "hospital.qa")):
            target = scene(name, label)
            if target:
                check(label + ".objects", len(target.objects) == count, count, len(target.objects))
        file = Path(old["glb"])
        check("hospital.glb_bytes", file.stat().st_size == old["glbBytes"], old["glbBytes"], file.stat().st_size)
        digest = sha(file)
        check("hospital.glb_sha256", digest == old["glbSha256"], old["glbSha256"], digest)
    stage("preserved_hospital", preserved_hospital)

    def preserved_coat_and_scenes():
        old = read_json(ROOT / "reports/BLENDER_ENTREGA_20261015.json")
        missing = sorted(set(old["liveSceneNames"]) - {item.name for item in bpy.data.scenes})
        check("preserved_prior_scenes.present", not missing, [], missing)
        target = scene("PREP_JALECO_QA_20261014", "coat")
        if target:
            check("coat.objects", len(target.objects) == old["coatScene"]["objects"], old["coatScene"]["objects"], len(target.objects))
            for item in old["coatScene"]["rigs"]:
                rig = target.objects.get(item["name"])
                check("coat." + item["name"] + ".armature_exists", rig is not None and rig.type == "ARMATURE")
                if rig is not None and rig.type == "ARMATURE":
                    check("coat." + item["name"] + ".bones", len(rig.data.bones) == item["bones"], item["bones"], len(rig.data.bones))
        report["preservationScope"] = dict(priorSceneListCount=len(old["liveSceneNames"]),
            priorSceneNamesPresent=not missing, hospitalExpectedObjects=[366, 313], coatExpectedObjects=73,
            coatExpectedBoneCounts=[55, 55],
            note="Snapshot equality proves the stored channels represented by object_state, not a new render or a complete geometry/material/action-curve fingerprint.")
    stage("preserved_coat_and_prior_scenes", preserved_coat_and_scenes)

    # Ensure this audit did not change the in-memory stored channels either.
    final_hash = state_hash(object_state(list(bpy.data.objects)))
    check("audit.stored_channels_unchanged", final_hash == actual_hash, actual_hash, final_hash)
    final_stat = MASTER.stat()
    final_digest = sha(MASTER)
    check("audit.master_bytes_unchanged", final_stat.st_size == initial_stat.st_size, initial_stat.st_size, final_stat.st_size)
    check("audit.master_mtime_unchanged", final_stat.st_mtime_ns == initial_stat.st_mtime_ns, initial_stat.st_mtime_ns, final_stat.st_mtime_ns)
    check("audit.master_sha256_unchanged", final_digest == report["masterSha256Before"], report["masterSha256Before"], final_digest)
    report.update(masterSha256After=final_digest, masterBytesAfter=final_stat.st_size,
                  masterModifiedByReadback=final_digest != report["masterSha256Before"] or final_stat.st_mtime_ns != initial_stat.st_mtime_ns,
                  finishedAt=now(), passed=not report["failures"], status="passed" if not report["failures"] else "failed")
    return report


try:
    result = run()
except Exception:
    result = dict(owner=OWNER, status="failed", passed=False, finishedAt=now(),
                  master=str(MASTER), blenderVersion=bpy.app.version_string,
                  error=traceback.format_exc(), masterModifiedByReadback=None, masterWriteAttempted=False,
                  note="Readback stopped; no repair, render, import, frame switch or .blend save was attempted.")
    log(result["error"])

REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
summary = dict(status=result["status"], passed=result["passed"], failures=len(result.get("failures", [])) + bool(result.get("error")),
               report=str(REPORT), log=str(LOG), masterModifiedByReadback=result.get("masterModifiedByReadback"))
log("RUN END " + json.dumps(summary, ensure_ascii=False))
print("PREP_DELIVERY_READBACK " + json.dumps(summary))
if not result["passed"]:
    sys.exit(1)
