"""Integrate the supplied multipart rail assets without changing earlier objects.

Run inside the resumed Blender master with exec(compile(Path(...).read_text(),
path, 'exec')). This script never opens/saves a .blend and never edits the runtime
manifest. ROOT must save the master after reviewing the two actual QA renders.

Original OBJ files, imported source meshes and all 30/2 parts are preserved.
Only independent static copies receive one assembly-wide origin normalization.
There is no reduction, welding, geometry deduplication, rig or invented motion.
Public files are published exclusively after roundtrip QA, without overwriting
existing files of unknown provenance. Owned complete stages can be resumed;
an interrupted/unrecorded file or object is left for inspection, never deleted.
"""

import bpy
import contextlib
import hashlib
import io
import json
import math
import os
import re
import struct
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mathutils import Matrix, Vector


ROOT = Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
OWNER = "prep_train_import_20261016_v1"
MAIN_SCENE = "PREP_RAIL_ASSETS_20261016"
AUDIT = ROOT / "reports/SUPPLIED_ASSET_AUDIT_20261016.json"
REPORT_DIR = ROOT / "reports/rail_assets_20261016"
PUBLIC = ROOT / "frontend/public/assets/supplied"
CATALOG = ROOT / "reports/train_catalog_entries_20261016.json"
SUMMARY = ROOT / "reports/TRAIN_IMPORT_20261016.json"
SPECS = (
    dict(id="SUP_trem_composicao_obj_20261016", folder="Trem", count=30,
         name="Trem — composição fornecida", category="Trens", short="TRAIN",
         description="Composição estática com 30 partes preservadas; materiais PBR provisórios. A unidade original não foi informada."),
    dict(id="SUP_trilhos_obj_20261016", folder="Trilhos do Trem andar em Cima", count=2,
         name="Trilhos — conjunto fornecido", category="Trens", short="TRACK",
         description="Conjunto estático com os dois OBJ em suas coordenadas compartilhadas. Sem sistema de percurso ou dirigibilidade."),
)
PALETTE = ((0.12, 0.23, 0.29, 1), (0.34, 0.40, 0.44, 1),
           (0.48, 0.17, 0.12, 1), (0.60, 0.62, 0.59, 1),
           (0.17, 0.19, 0.21, 1), (0.35, 0.31, 0.24, 1))


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_owned(path, payload):
    """Only caller-owned reports may be replaced, atomically."""
    path = Path(path)
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        assert old.get("owner") == OWNER, "Unowned report: " + str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)


def load_record(spec, fingerprint):
    path = REPORT_DIR / (spec["id"] + ".json")
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record.get("owner") == OWNER and record.get("id") == spec["id"]
        assert record.get("sourceFingerprint") == fingerprint, "Source set changed; inspect before continuing"
    else:
        record = dict(owner=OWNER, id=spec["id"], status="preflight", parts={},
                      sourceFingerprint=fingerprint, createdAt=now())
    return record, path


def checkpoint(record, path, stage):
    record.update(status=stage, updatedAt=now())
    write_owned(path, record)


def source_metadata(path):
    low, high = [math.inf] * 3, [-math.inf] * 3
    vertices = triangles = uv = normals = 0
    normal_abs = [0.0] * 3
    materials, names = set(), set()
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("v "):
                point = list(map(float, line.split()[1:4]))
                assert len(point) == 3 and all(map(math.isfinite, point)), str(path)
                vertices += 1
                for axis in range(3):
                    low[axis] = min(low[axis], point[axis])
                    high[axis] = max(high[axis], point[axis])
            elif line.startswith("f "):
                triangles += max(0, len(line.split()) - 3)
            elif line.startswith("vt "):
                uv += 1
            elif line.startswith("vn "):
                normal = list(map(float, line.split()[1:4]))
                assert all(map(math.isfinite, normal))
                normals += 1
                for axis in range(3):
                    normal_abs[axis] += abs(normal[axis])
            elif line.startswith("usemtl "):
                materials.add(line[7:].strip())
            elif line.startswith(("o ", "g ")):
                names.add(line[2:].strip())
    assert vertices and triangles and all(map(math.isfinite, low + high))
    return dict(vertices=vertices, triangles=triangles, uvCoordinates=uv,
                normals=normals, normalAbsSum=normal_abs,
                materialNames=sorted(materials), objectGroupNames=sorted(names),
                boundsMin=low, boundsMax=high,
                dimensions=[high[i] - low[i] for i in range(3)])


def close_vectors(a, b, tolerance=0.002):
    assert len(a) == len(b) == 3
    assert max(abs(a[i] - b[i]) for i in range(3)) <= tolerance, (a, b)


def bounds(objects):
    low, high = [math.inf] * 3, [-math.inf] * 3
    vertices = triangles = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        assert not obj.modifiers, "Unexpected geometry modifier: " + obj.name
        triangles += sum(len(face.vertices) - 2 for face in obj.data.polygons)
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            assert all(math.isfinite(v) for v in point), obj.name
            vertices += 1
            for axis in range(3):
                low[axis] = min(low[axis], point[axis])
                high[axis] = max(high[axis], point[axis])
    assert vertices and triangles and all(map(math.isfinite, low + high))
    return dict(vertices=vertices, triangles=triangles,
                meshes=sum(obj.type == "MESH" for obj in objects),
                boundsMin=low, boundsMax=high,
                dimensions=[high[i] - low[i] for i in range(3)])


def owned_scene(name, purpose):
    scene = bpy.data.scenes.get(name)
    if scene:
        assert scene.get("rail_owner") == OWNER, "Unowned scene collision: " + name
    else:
        scene = bpy.data.scenes.new(name)
        scene["rail_owner"] = OWNER
        scene["purpose"] = purpose
        scene.unit_settings.system = "NONE"  # Source OBJ unit was not supplied.
        scene.unit_settings.scale_length = 1
    return scene


def owned_collection(scene, name):
    collection = bpy.data.collections.get(name)
    if collection:
        assert collection.get("rail_owner") == OWNER, "Unowned collection collision: " + name
    else:
        collection = bpy.data.collections.new(name)
        collection["rail_owner"] = OWNER
    if collection.name not in scene.collection.children:
        scene.collection.children.link(collection)
    return collection


def activate(scene):
    assert bpy.context.window, "A Blender window/context is required for this master integration"
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()


def call_operator(operator, arguments, log_path):
    properties = set(operator.get_rna_type().properties.keys())
    required = {"filepath"}
    assert required <= properties
    supported = {key: value for key, value in arguments.items() if key in properties}
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = operator(**supported)
        assert "FINISHED" in result, result
    finally:
        # An append-only log records retries without replacing an unchecked log.
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write("\n" + now() + " " + str(supported) + "\n" + output.getvalue())
    return supported


def import_parts(scene, collection, spec, files, record, record_path):
    activate(scene)
    selected = []
    for file in files:
        relative = file["relative"]
        old_part = record["parts"].get(relative)
        existing = [obj for obj in scene.objects if obj.get("rail_owner") == OWNER
                    and obj.get("rail_stage") == "source" and obj.get("rail_source_relative") == relative]
        if old_part:
            assert existing and sorted(obj.name for obj in existing) == sorted(old_part["objects"]), "Recorded part missing from open master: " + relative
            assert all(obj.get("rail_source_sha256") == file["sha256"] for obj in existing)
            close_vectors(bounds(existing)["boundsMin"], file["source"]["boundsMin"])
            close_vectors(bounds(existing)["boundsMax"], file["source"]["boundsMax"])
            selected.extend(existing)
            continue
        assert not existing, "Partial unrecorded import; inspect before resuming: " + relative
        before = set(bpy.data.objects)
        try:
            properties = set(bpy.ops.wm.obj_import.get_rna_type().properties.keys())
            assert {"forward_axis", "up_axis"} <= properties
            call_operator(bpy.ops.wm.obj_import, dict(filepath=file["path"],
                forward_axis="Y", up_axis="Z", global_scale=1.0,
                clamp_size=0.0, use_split_objects=False, use_split_groups=False),
                REPORT_DIR / (spec["short"].lower() + "_obj_import.log"))
        finally:
            new_objects = list(set(bpy.data.objects) - before)
            for index, obj in enumerate(sorted(new_objects, key=lambda value: value.name)):
                obj["rail_owner"] = OWNER
                obj["rail_stage"] = "source"
                obj["rail_source_relative"] = relative
                obj["rail_source_sha256"] = file["sha256"]
                obj.name = "RAIL16_" + spec["short"] + "_SRC_" + Path(relative).stem + "_" + str(index)
                for old_collection in list(obj.users_collection):
                    old_collection.objects.unlink(obj)
                collection.objects.link(obj)
        assert new_objects and all(obj.type == "MESH" for obj in new_objects)
        assert all(not obj.parent and not obj.animation_data and not obj.constraints and not obj.data.shape_keys for obj in new_objects)
        bpy.context.view_layer.update()
        stats = bounds(new_objects)
        close_vectors(stats["boundsMin"], file["source"]["boundsMin"])
        close_vectors(stats["boundsMax"], file["source"]["boundsMax"])
        record["parts"][relative] = dict(objects=[obj.name for obj in new_objects], stats=stats,
                                        sourceSha256=file["sha256"], source=file["source"])
        checkpoint(record, record_path, "importing_source_parts")
        selected.extend(new_objects)
    assert {obj["rail_source_relative"] for obj in selected} == {f["relative"] for f in files}
    collection.hide_render = True
    return selected


def repaired_material(obj, file, spec, index, record):
    name = "RAIL16_" + spec["short"] + "_PBR_" + str(index).zfill(2)
    material = bpy.data.materials.get(name)
    if material:
        assert material.get("rail_owner") == OWNER
    else:
        material = bpy.data.materials.new(name)
        material["rail_owner"] = OWNER
        material.use_nodes = True
        color = PALETTE[index % len(PALETTE)]
        material.diffuse_color = color
        principled = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = 0.25
        principled.inputs["Roughness"].default_value = 0.55
        # UV alone is insufficient: require a material name explicitly matching
        # a local image stem. The current audited OBJ parts have no usemtl names.
        tokens = {re.sub(r"[^a-z0-9]", "", value.lower()) for value in file["source"]["materialNames"]}
        matches = [image for image in Path(file["path"]).parent.glob("*.png")
                   if re.sub(r"[^a-z0-9]", "", image.stem.lower()) in tokens]
        if file["source"]["uvCoordinates"] and obj.data.uv_layers and len(matches) == 1:
            image = bpy.data.images.load(str(matches[0]), check_existing=False)
            image["rail_owner"] = OWNER
            image.pack()
            node = material.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = image
            material.node_tree.links.new(node.outputs["Color"], principled.inputs["Base Color"])
            record.setdefault("textureAssignments", []).append(dict(part=file["relative"], image=str(matches[0]), reason="Existing UV and explicit source material-name match"))
    return material


def prepare_derived(spec, source, files, record, record_path):
    scene = owned_scene("PREP_RAIL_DERIVED_" + spec["short"] + "_20261016", "Normalized static copies; sources remain in " + MAIN_SCENE)
    collection = owned_collection(scene, "RAIL16_" + spec["short"] + "_DERIVED")
    activate(scene)
    sources_by_name = {obj.name: obj for obj in source}
    existing = [obj for obj in scene.objects if obj.type == "MESH"]
    if existing:
        assert all(obj.get("rail_owner") == OWNER and obj.get("rail_stage") == "derived" for obj in existing)
        assert record.get("derivedReady"), "Partial derived stage; inspect before resuming"
        assert {obj.get("rail_source_object") for obj in existing} == set(sources_by_name)
        close_vectors(bounds(existing)["dimensions"], record["sourceImported"]["dimensions"])
        return scene, existing
    source_bounds = record["sourceImported"]
    low, high = source_bounds["boundsMin"], source_bounds["boundsMax"]
    translation = [-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]]
    common = Matrix.Translation(Vector(translation))
    file_map = {file["relative"]: file for file in files}
    derived = []
    for index, obj in enumerate(sorted(source, key=lambda value: value.name)):
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.animation_data_clear()
        copy.name = "RAIL16_" + spec["short"] + "_DERIVED_" + str(index).zfill(2)
        copy["rail_stage"] = "derived"
        copy["rail_source_object"] = obj.name
        copy["source_part_name"] = obj["rail_source_relative"]
        # This changes only the copied mesh data, once for the entire assembly.
        copy.data.transform(common @ obj.matrix_world)
        copy.matrix_world = Matrix.Identity(4)
        copy.data.materials.clear()
        copy.data.materials.append(repaired_material(copy, file_map[obj["rail_source_relative"]], spec, index, record))
        for polygon in copy.data.polygons:
            polygon.material_index = 0
        collection.objects.link(copy)
        derived.append(copy)
    bpy.context.view_layer.update()
    stats = bounds(derived)
    close_vectors(stats["dimensions"], source_bounds["dimensions"])
    close_vectors(stats["boundsMin"], [-stats["dimensions"][0] / 2, -stats["dimensions"][1] / 2, 0])
    assert stats["triangles"] == source_bounds["triangles"]
    record.update(derivedReady=True, derivedScene=scene.name, derivedStats=stats,
                  normalization=dict(translationBlenderXYZ=translation, scale=1,
                                     orientation="Source Z-up retained; glTF export performs standard Y-up conversion",
                                     units="unspecified source OBJ units; no forced wagon length or metric assertion"))
    checkpoint(record, record_path, "derived_ready")
    return scene, derived


def glb_metadata(path):
    with path.open("rb") as stream:
        header = stream.read(20)
        assert header[:4] == b"glTF" and struct.unpack_from("<I", header, 4)[0] == 2
        assert struct.unpack_from("<I", header, 8)[0] == path.stat().st_size
        length, kind = struct.unpack_from("<II", header, 12)
        assert kind == 0x4E4F534A
        doc = json.loads(stream.read(length))
    assert not doc.get("skins") and not doc.get("animations")
    assert all(not item.get("uri") for item in doc.get("buffers", []) + doc.get("images", []))
    accessors = doc["accessors"]
    mesh_triangles = []
    for mesh in doc["meshes"]:
        count = 0
        for primitive in mesh["primitives"]:
            assert primitive.get("mode", 4) == 4
            amount = accessors[primitive["indices"]]["count"] if "indices" in primitive else accessors[primitive["attributes"]["POSITION"]]["count"]
            assert amount % 3 == 0
            count += amount // 3
        mesh_triangles.append(count)
    def count_node(index):
        node = doc["nodes"][index]
        return (mesh_triangles[node["mesh"]] if "mesh" in node else 0) + sum(count_node(i) for i in node.get("children", []))
    triangles = sum(count_node(i) for i in doc["scenes"][doc.get("scene", 0)]["nodes"])
    source_parts = sorted({node.get("extras", {}).get("rail_source_relative") for node in doc["nodes"] if "mesh" in node})
    return dict(triangles=triangles, meshPrimitiveTriangles=sum(mesh_triangles),
                meshes=len(doc["meshes"]), nodes=len(doc["nodes"]), sourceParts=source_parts,
                materials=len(doc.get("materials", [])), images=len(doc.get("images", [])),
                bytes=path.stat().st_size, sha256=sha(path))


def export_or_resume(spec, scene, objects, record, record_path):
    pending = REPORT_DIR / (spec["id"] + ".pending.glb")
    public = PUBLIC / (spec["id"] + ".glb")
    if public.exists():
        expected = record.get("export", {}).get("sha256")
        assert expected and sha(public) == expected, "Unchecked public file; refusing overwrite: " + str(public)
        return public, glb_metadata(public)
    if pending.exists():
        expected = record.get("export", {}).get("sha256")
        assert expected and sha(pending) == expected, "Unrecorded/partial pending export; inspect: " + str(pending)
        return pending, glb_metadata(pending)
    activate(scene)
    for obj in scene.objects:
        obj.select_set(False)
    for obj in objects:
        assert obj.get("rail_stage") == "derived" and not obj.parent and not obj.modifiers
        assert not obj.animation_data and not obj.constraints and not obj.data.shape_keys
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    checkpoint(record, record_path, "exporting_static_derivative")
    properties = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    assert {"export_apply", "use_selection", "use_active_scene"} <= properties
    record["exportOperatorArguments"] = call_operator(bpy.ops.export_scene.gltf,
        dict(filepath=str(pending), export_format="GLB", use_selection=True, use_active_scene=True,
             export_yup=True, export_apply=True, export_animations=False, export_skins=False,
             export_cameras=False, export_lights=False, export_extras=True,
             export_materials="EXPORT", export_texcoords=True, export_normals=True),
        REPORT_DIR / (spec["short"].lower() + "_glb_export.log"))
    metadata = glb_metadata(pending)
    assert set(metadata["sourceParts"]) == set(record["parts"]), "An assembly part was not exported"
    assert 0 < metadata["triangles"] <= record["derivedStats"]["triangles"]
    record["export"] = metadata
    checkpoint(record, record_path, "exported_pending_qa")
    return pending, metadata


def roundtrip(spec, path, metadata, record, record_path):
    scene = owned_scene("PREP_RAIL_QA_" + spec["short"] + "_20261016", "QA of exact delivered static rail GLB")
    activate(scene)
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    if meshes:
        assert scene.get("rail_qa_sha256") == metadata["sha256"], "Unrecorded/changed QA scene; inspect"
        assert all(obj.get("rail_owner") == OWNER and obj.get("rail_stage") == "qa" for obj in meshes)
    else:
        assert not scene.get("rail_qa_sha256"), "Recorded QA geometry missing from scene"
        before = set(bpy.data.objects)
        call_operator(bpy.ops.import_scene.gltf, dict(filepath=str(path)),
                      REPORT_DIR / (spec["short"].lower() + "_glb_reimport.log"))
        imported = list(set(bpy.data.objects) - before)
        assert imported
        for index, obj in enumerate(sorted(imported, key=lambda value: value.name)):
            obj["rail_owner"] = OWNER
            obj["rail_stage"] = "qa"
            obj["roundtrip_source_node"] = obj.name
            obj.name = "RAIL16_" + spec["short"] + "_QA_" + str(index).zfill(2)
        meshes = [obj for obj in imported if obj.type == "MESH"]
    bpy.context.view_layer.update()
    stats = bounds(meshes)
    assert stats["triangles"] == metadata["triangles"], (stats, metadata)
    close_vectors(stats["boundsMin"], record["derivedStats"]["boundsMin"])
    close_vectors(stats["boundsMax"], record["derivedStats"]["boundsMax"])
    scene["rail_qa_sha256"] = metadata["sha256"]
    record["roundtrip"] = dict(passed=True, scene=scene.name, stats=stats,
                                triangleDeltaFromPrepared=metadata["triangles"] - record["derivedStats"]["triangles"],
                                boundsTolerance=0.002)
    checkpoint(record, record_path, "roundtrip_passed")
    return scene, meshes


def preview(spec, scene, meshes, record, record_path):
    pending = REPORT_DIR / (spec["id"] + ".pending.jpg")
    public = PUBLIC / (spec["id"] + ".jpg")
    if public.exists():
        assert record.get("previewSha256") and sha(public) == record["previewSha256"], "Unchecked preview exists: " + str(public)
        return public
    if pending.exists():
        assert record.get("previewSha256") and sha(pending) == record["previewSha256"], "Unrecorded/partial preview: " + str(pending)
        return pending
    activate(scene)
    stats = bounds(meshes)
    low, high = Vector(stats["boundsMin"]), Vector(stats["boundsMax"])
    center, span = (low + high) / 2, max(stats["dimensions"])
    camera = next((obj for obj in scene.objects if obj.get("rail_preview_role") == "camera"), None)
    if not camera:
        data = bpy.data.cameras.new("RAIL16_" + spec["short"] + "_PREVIEW_CAMERA")
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        camera["rail_owner"] = OWNER
        camera["rail_preview_role"] = "camera"
    camera.location = center + Vector((0.38, -1.0, 0.7)).normalized() * span * 2
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.clip_start = max(0.001, span / 10000)
    camera.data.clip_end = max(1000, span * 20)
    scene.camera = camera
    bpy.context.view_layer.update()
    inverse = camera.matrix_world.inverted()
    points = [inverse @ Vector((x, y, z)) for x in (low.x, high.x) for y in (low.y, high.y) for z in (low.z, high.z)]
    width = max(p.x for p in points) - min(p.x for p in points)
    height = max(p.y for p in points) - min(p.y for p in points)
    scene.render.resolution_x = 960
    scene.render.resolution_y = 420
    scene.render.resolution_percentage = 100
    camera.data.ortho_scale = max(width, height * (960 / 420)) * 1.15
    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = next((engine for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES") if engine in engines), "CYCLES")
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 8
    if not scene.world:
        world = bpy.data.worlds.new("RAIL16_" + spec["short"] + "_WORLD")
        world["rail_owner"] = OWNER
        world.use_nodes = True
        next(node for node in world.node_tree.nodes if node.type == "BACKGROUND").inputs[0].default_value = (0.12, 0.16, 0.20, 1)
        next(node for node in world.node_tree.nodes if node.type == "BACKGROUND").inputs[1].default_value = 0.8
        scene.world = world
    if not any(obj.get("rail_preview_role") == "sun" for obj in scene.objects):
        data = bpy.data.lights.new("RAIL16_" + spec["short"] + "_SUN", "SUN")
        data.energy = 2.5
        data.angle = math.radians(15)
        light = bpy.data.objects.new(data.name, data)
        light["rail_owner"] = OWNER
        light["rail_preview_role"] = "sun"
        scene.collection.objects.link(light)
        light.rotation_euler = (math.radians(25), math.radians(-20), math.radians(-35))
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    scene.render.filepath = str(pending)
    checkpoint(record, record_path, "rendering_actual_reimport_preview")
    bpy.ops.render.render(write_still=True)
    assert pending.is_file() and pending.stat().st_size > 1000
    record.update(previewSha256=sha(pending), previewRender=dict(scene=scene.name,
                  engine=scene.render.engine, resolution=[960, 420], actualReimport=True,
                  visualReview="pending human inspection"))
    checkpoint(record, record_path, "preview_rendered")
    return pending


def publish_exclusive(source, destination, expected_sha):
    assert sha(source) == expected_sha
    if destination.exists():
        assert sha(destination) == expected_sha, "Refusing unchecked overwrite: " + str(destination)
        return
    # Same-workspace NTFS hard link is atomic and refuses an existing target.
    # Both paths remain immutable: reruns reuse/check hashes, never re-export over them.
    os.link(source, destination)
    assert sha(destination) == expected_sha


def catalog_entry(spec, record):
    exported = record["export"]
    return dict(id=spec["id"], name=spec["name"], category=spec["category"],
        sourceRelative=spec["folder"], sourceFiles=sorted(record["parts"]),
        sourceSha256=record["sourceFingerprint"], sourceHashType="ordered multipart relative-path and SHA-256 fingerprint",
        sourceFileHashes={part: data["sourceSha256"] for part, data in record["parts"].items()},
        status="validated", url="/assets/supplied/" + spec["id"] + ".glb",
        preview="/assets/supplied/" + spec["id"] + ".jpg", sha256=exported["sha256"],
        bytes=exported["bytes"], triangles=exported["triangles"], meshes=exported["meshes"],
        originalTriangles=sum(data["source"]["triangles"] for data in record["parts"].values()),
        preparedTriangles=record["derivedStats"]["triangles"], meshPrimitiveTriangles=exported["meshPrimitiveTriangles"],
        dimensions=record["roundtrip"]["stats"]["dimensions"],
        dimensionsAxisOrder="Blender XYZ; GLB uses standard Y-up", animated=False,
        reimportValidated=True, sourceCategory="rail_train" if spec["short"] == "TRAIN" else "rail_track",
        animations=[], originalRig=False, rigged=False, playable=False, drivable=False,
        heavyAsset=exported["bytes"] > 30 * 1024 * 1024,
        description=spec["description"], licenseStatus="unknown", credits={},
        tags=["rail", "multipart", "static", "supplied", "20261016"],
        modifications="One shared-origin translation on independent static copies; scale retained; no geometry deduplication, welding or reduction. Missing MTL replaced by a provisional PBR palette; local images require existing UV plus an explicit material-name match.",
        validation="Blender GLB reimport; all source parts represented; finite vertices; exact exported/reimported triangle count; bounds within 0.002 source units; preview rendered from reimported geometry.")


def main():
    assert bpy.context.window, "Run in the resumed master Blender session"
    original_scene = bpy.context.window.scene
    previous_objects = [obj for obj in bpy.data.objects if obj.get("rail_owner") != OWNER]
    sys.path.insert(0, str(ROOT / "scripts"))
    from prep_object_state_20261015 import object_state, state_hash
    baseline = state_hash(object_state(previous_objects))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    source_root = Path(audit["source_root"])
    planned = []
    for spec in SPECS:
        files = sorted((dict(item) for item in audit["models"]
            if item["relative"].replace("\\", "/").startswith(spec["folder"] + "/")
            and item.get("extension") == ".obj"), key=lambda item: int(Path(item["relative"]).stem.split("_")[-1]))
        assert len(files) == spec["count"], (spec, len(files))
        actual_files = {path.resolve() for path in (source_root / spec["folder"]).glob("*.obj")}
        assert actual_files == {Path(item["path"]).resolve() for item in files}, "Audit/source OBJ set mismatch"
        for file in files:
            path = Path(file["path"])
            assert path.is_relative_to(source_root) and path.is_file()
            assert sha(path) == file["sha256"], "Original source changed: " + str(path)
            file["source"] = source_metadata(path)
            assert file["source"]["vertices"] == file["metadata"]["vertices"], "Source vertex count differs from audit"
            assert file["source"]["triangles"] == file["metadata"]["triangles_fan_equivalent"], "Source triangle count differs from audit"
            close_vectors(file["source"]["boundsMin"], file["metadata"]["bounds_min"])
            close_vectors(file["source"]["boundsMax"], file["metadata"]["bounds_max"])
        fingerprint = hashlib.sha256(json.dumps([[f["relative"], f["sha256"]] for f in files], ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        if spec["short"] == "TRAIN":
            base = next(file["source"] for file in files if Path(file["relative"]).stem == "model_0")
            assert base["dimensions"][0] > base["dimensions"][1] * 30
            assert base["dimensions"][2] < base["dimensions"][1]
            assert base["normalAbsSum"][2] > max(base["normalAbsSum"][:2]) * 2, "Z-up evidence changed; inspect the source basis"
        planned.append((spec, files, fingerprint))
    main_scene = owned_scene(MAIN_SCENE, "Preserved supplied train/track source assemblies; no invented motion")
    entries, summaries = [], []
    try:
        for spec, files, fingerprint in planned:
            record, record_path = load_record(spec, fingerprint)
            try:
                collection = owned_collection(main_scene, "RAIL16_" + spec["short"] + "_SOURCE")
                source = import_parts(main_scene, collection, spec, files, record, record_path)
                record["sourceImported"] = bounds(source)
                record["orientationEvidence"] = dict(sourceUp="Z", sourceLongAxis="X",
                    importAxes=dict(forward="Y", up="Z"),
                    rationale="Bounds are checked against every source vertex before/after import. Train base model_0 spans 227.59 X and 5.02 Y with only 0.86 Z; its normal sum is dominated by Z. The separate track set retains its existing grade/elevation, not flattened.",
                    sourceUnit="unspecified", scale=1)
                record["limitations"] = ["Source OBJ units and source license/author are not supplied.",
                    "All parts are retained, including repeated/overlapping pieces; no blind deduplication.",
                    "Missing MTL prevents faithful original material recovery. PBR colors are provisional.",
                    "UV presence does not prove a PNG association; unmatched images are intentionally unused.",
                    "No skeletal rig, animation, rail movement, collision path or driving controls are supplied by OBJ.",
                    "The full train composition may be heavy for mobile hardware; no geometry reduction was performed."]
                record["localImages"] = [dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path), association="unresolved unless explicit source material-name and UV match") for path in sorted((source_root / spec["folder"]).glob("*.png"))]
                checkpoint(record, record_path, "source_imported")
                scene, derived = prepare_derived(spec, source, files, record, record_path)
                pending, metadata = export_or_resume(spec, scene, derived, record, record_path)
                record["export"] = metadata
                qa_scene, qa_meshes = roundtrip(spec, pending, metadata, record, record_path)
                image = preview(spec, qa_scene, qa_meshes, record, record_path)
                publish_exclusive(pending, PUBLIC / (spec["id"] + ".glb"), metadata["sha256"])
                publish_exclusive(image, PUBLIC / (spec["id"] + ".jpg"), record["previewSha256"])
                record["catalogEntry"] = catalog_entry(spec, record)
                checkpoint(record, record_path, "validated")
                entries.append(record["catalogEntry"])
                summaries.append(dict(id=spec["id"], status="validated", report=str(record_path),
                                      sha256=metadata["sha256"], triangles=metadata["triangles"]))
            except Exception:
                record.update(status="failed_requires_inspection", error=traceback.format_exc(), updatedAt=now())
                write_owned(record_path, record)
                raise
        assert state_hash(object_state(previous_objects)) == baseline, "An earlier object channel changed"
        result = dict(owner=OWNER, status="validated", generatedAt=now(), entries=entries,
                      manifestEdited=False, masterSaved=False,
                      note="Root must review actual renders, merge these entries into its owned additions manifest and save the master.")
        write_owned(CATALOG, result)
        write_owned(SUMMARY, dict(owner=OWNER, status="validated", generatedAt=now(),
                    sourceScene=main_scene.name, results=summaries,
                    earlierObjectCount=len(previous_objects), earlierObjectStateHash=baseline,
                    earlierObjectsUnchanged=True, masterSaved=False, manifestEdited=False,
                    sceneCount=len(bpy.data.scenes), objectCount=len(bpy.data.objects)))
        print("PREP_RAIL_ASSETS_20261016 " + json.dumps(result, ensure_ascii=False))
    finally:
        bpy.context.window.scene = original_scene
        assert state_hash(object_state(previous_objects)) == baseline, "An earlier object channel changed"


main()
