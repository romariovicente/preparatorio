"""Resume the station roundtrip without importing/exporting again.

Run only through the root agent's exclusive live Blender MCP session. This
script preserves the source, failed report, staging GLB, and all existing scene
objects. It corrects the *measurement*, not the geometry or its tolerance:
Blender bound_box can include loose vertices that glTF does not export.
Publication requires matching actual face-referenced world geometry bounds.
The root agent saves the master before and after this script.
"""
import bpy
import hashlib
import json
import math
import os
import runpy
import struct
import traceback
import uuid
from pathlib import Path
from mathutils import Vector

ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
HELPERS = runpy.run_path(str(ROOT / 'scripts/prep_station_import_20261016.py'), run_name='prep_station_repair_helpers')
OWNER = HELPERS['OWNER']
IDENT = HELPERS['IDENT']
SOURCE_SHA = HELPERS['SOURCE_SHA']
SOURCE = HELPERS['SOURCE'] / HELPERS['RELATIVE']
OUT = HELPERS['OUT']
FINAL = HELPERS['FINAL']
PREVIEW = HELPERS['PREVIEW']
QA_REPORT = HELPERS['QA_REPORT']
CATALOG_REPORT = HELPERS['REPORT']
REPAIR_REPORT = ROOT / 'reports/STATION_REPAIR_QA_20261016.json'
sha = HELPERS['sha']
write_json = HELPERS['write_json']


def preserve_copy(source, destination):
    """Exclusive creation, or exact-byte reuse; never replace an existing file."""
    assert source.is_file()
    digest = sha(source)
    if destination.exists():
        assert destination.is_file() and sha(destination) == digest, 'Existing file differs: ' + str(destination)
        return
    with source.open('rb') as src, destination.open('xb') as dst:
        while chunk := src.read(4 * 1024 * 1024):
            dst.write(chunk)
    assert sha(destination) == digest


def extrema(points):
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    count = 0
    for point in points:
        assert all(math.isfinite(float(c)) for c in point), 'Non-finite geometry point'
        for axis in range(3):
            lo[axis] = min(lo[axis], float(point[axis]))
            hi[axis] = max(hi[axis], float(point[axis]))
        count += 1
    assert count
    return {'boundsMin': lo, 'boundsMax': hi, 'dimensions': [hi[i] - lo[i] for i in range(3)]}


def geometry_stats(scene, objects):
    """Measure only vertices referenced by exported mesh faces, in world space."""
    HELPERS['scene_switch'](scene)
    bpy.context.view_layer.update()
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    geometry = HELPERS['meshes'](objects)
    assert geometry
    face_points = []
    all_points = []
    box_points = []
    vertices = used_vertices = triangles = 0
    per_mesh = []
    for obj in geometry:
        assert not obj.modifiers and not obj.constraints and not obj.animation_data, 'Expected static applied station mesh'
        assert not obj.hide_render and not obj.hide_viewport and not obj.hide_get(), 'Hidden geometry requires an explicit export-inclusion audit'
        evaluated = obj.evaluated_get(dependency_graph)
        mesh = evaluated.to_mesh()
        try:
            used = {index for polygon in mesh.polygons for index in polygon.vertices}
            assert used, 'Mesh has no face-referenced vertices'
            count = sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
            for vertex in mesh.vertices:
                point = evaluated.matrix_world @ vertex.co
                all_points.append(point)
                if vertex.index in used:
                    face_points.append(point)
            box_points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
            vertices += len(mesh.vertices)
            used_vertices += len(used)
            triangles += count
            per_mesh.append({'object': obj.name, 'vertices': len(mesh.vertices), 'faceReferencedVertices': len(used),
                             'looseVertices': len(mesh.vertices) - len(used), 'triangles': count})
        finally:
            evaluated.to_mesh_clear()
    result = extrema(face_points)
    assert min(result['dimensions']) > 1e-6
    result.update({'meshes': len(geometry), 'vertices': vertices, 'faceReferencedVertices': used_vertices,
                   'looseVertices': vertices - used_vertices, 'triangles': triangles,
                   'allVertexBounds': extrema(all_points), 'objectBoundingBoxes': extrema(box_points),
                   'perMesh': per_mesh, 'measurement': 'Evaluated world positions of polygon-referenced vertices; static visible included meshes only'})
    return result


def compare_bounds(expected, actual):
    # The original script used max(0.002 m, dimension * 1e-5). Keep precisely
    # that tolerance, now compare both extrema as well as the dimensions.
    tolerance = [max(.002, dimension * 1e-5) for dimension in expected['dimensions']]
    differences = {}
    for field in ('boundsMin', 'boundsMax', 'dimensions'):
        differences[field] = [abs(a - b) for a, b in zip(expected[field], actual[field])]
        assert all(delta <= tolerance[axis] for axis, delta in enumerate(differences[field])), (
            'Actual face geometry does not roundtrip: ' + field + ' ' + repr(differences[field]))
    return {'toleranceMetersXYZ': tolerance, 'absoluteDifferencesXYZ': differences,
            'toleranceUnchangedFromOriginalValidation': True}


def main():
    assert bpy.app.version >= (5, 2, 0)
    assert Path(bpy.data.filepath).resolve() == (ROOT / 'art/blender/PREPARATORIO_PROJETO_20261016.blend').resolve()
    assert sha(SOURCE) == SOURCE_SHA, 'Original source GLB differs from audited bytes'
    previous_report = json.loads(QA_REPORT.read_text(encoding='utf-8'))
    assert previous_report.get('prepOwner') == OWNER
    if previous_report.get('status') == 'validated':
        entries = json.loads(CATALOG_REPORT.read_text(encoding='utf-8'))
        assert len(entries) == 1 and entries[0]['id'] == IDENT and entries[0]['reimportValidated']
        assert sha(FINAL) == entries[0]['sha256'] and sha(PREVIEW) == entries[0]['previewSha256']
        print('PREP_STATION_REPAIR_20261016 ' + json.dumps({'status': 'reused-validated', 'id': IDENT, 'masterSaved': False}))
        return
    assert previous_report.get('status') == 'failed' and 'Reimport bounds mismatch' in previous_report.get('error', '')
    staging = Path(previous_report['stagingGLBPreserved'])
    assert staging.parent.resolve() == OUT.resolve() and staging.name.startswith('.' + IDENT + '.') and staging.name.endswith('.staging.glb')
    assert staging.is_file() and not FINAL.exists() and not PREVIEW.exists() and not CATALOG_REPORT.exists(), 'Inspect partial or existing publication first'
    source_scene = bpy.data.scenes.get('PREP_STATION_SOURCE_20261016')
    lod_scene = bpy.data.scenes.get('PREP_STATION_LOD_20261016')
    qa_scene = bpy.data.scenes.get('PREP_STATION_QA_20261016')
    assert all(scene and scene.get('prep_owner') == OWNER for scene in (source_scene, lod_scene, qa_scene)), 'Expected preserved source/LOD/QA scenes'
    qa_collections = [collection for collection in qa_scene.collection.children if collection.get('prep_owner') == OWNER]
    source_collections = [collection for collection in source_scene.collection.children if collection.get('prep_owner') == OWNER]
    lod_collections = [collection for collection in lod_scene.collection.children if collection.get('prep_owner') == OWNER]
    assert len(qa_collections) == len(source_collections) == len(lod_collections) == 1
    source_objects = tuple(source_scene.objects)
    lod_objects = tuple(lod_scene.objects)
    qa_objects = tuple(qa_scene.objects)
    assert len(HELPERS['meshes'](lod_objects)) <= 27 and len(HELPERS['meshes'](qa_objects)) <= 27
    assert all(obj.get('prep_owner') == OWNER for obj in source_objects + lod_objects + qa_objects)
    original_objects = tuple(bpy.data.objects)
    original_state = HELPERS['state'](original_objects)
    original_materials = HELPERS['source_material_snapshot'](source_objects)
    windows = [(window, window.scene) for window in bpy.context.window_manager.windows]
    failure_copy = QA_REPORT.with_name(QA_REPORT.stem + '.failed_' + sha(QA_REPORT)[:12] + '.json')
    preserve_copy(QA_REPORT, failure_copy)
    repair = {'prepOwner': OWNER, 'repairScript': Path(__file__).name, 'status': 'in-progress',
              'failedReportPreserved': str(failure_copy), 'stagingGLBPreserved': str(staging),
              'stagingSha256': sha(staging), 'masterSaved': False, 'runtimeManifestChanged': False}
    try:
        source_stats = geometry_stats(source_scene, source_objects)
        lod_stats = geometry_stats(lod_scene, lod_objects)
        qa_stats = geometry_stats(qa_scene, qa_objects)
        repair.update({'source': source_stats, 'derivative': lod_stats, 'reimport': qa_stats})
        comparisons = compare_bounds(lod_stats, qa_stats)
        document = HELPERS['doc_from_glb'](staging)
        expected = HELPERS['triangle_count'](document)
        assert source_stats['triangles'] == 1130377
        assert 0 < expected <= HELPERS['HARD_MAX']
        assert expected == lod_stats['triangles'] == qa_stats['triangles']
        assert lod_stats['meshes'] == qa_stats['meshes'] == len(document.get('meshes', [])) <= 27
        assert not document.get('skins') and not document.get('animations') and not document.get('extensionsRequired')
        assert all(abs(a - b) <= max(.1, a * .02) for a, b in zip(source_stats['dimensions'], lod_stats['dimensions'])), 'LOD changed source extent by more than original 2% limit'
        assert abs(lod_stats['boundsMin'][2]) <= .002, 'Actual visible LOD is not grounded to original validation tolerance'
        assert all(abs((lod_stats['boundsMin'][axis] + lod_stats['boundsMax'][axis]) / 2) <= max(.002, lod_stats['dimensions'][axis] * 1e-5) for axis in (0, 1)), 'Actual face geometry is not centered in XY'
        HELPERS['scene_switch'](qa_scene)
        qa_images = HELPERS['used_images'](qa_objects)
        assert qa_images and all(0 < min(image.size) and max(image.size) <= HELPERS['TEXTURE_CAP'] for image in qa_images)
        lod_images = HELPERS['used_images'](lod_objects)
        source_images = HELPERS['used_images'](source_objects)
        assert all(image not in source_images for image in lod_images), 'LOD shares a resized source image'
        texture_details = [{'copiedName': image.name, 'lodDimensions': list(image.size),
                            'sourceName': next((original.name for original in source_images if image.name == 'ST16_LOD_' + original.name), None),
                            'inspection': 'Read from preserved LOD image datablock during repair; source image bytes unchanged during repair'} for image in lod_images]
        differing_bounds = any(abs(a - b) > comparisons['toleranceMetersXYZ'][axis] for axis, (a, b) in enumerate(zip(lod_stats['objectBoundingBoxes']['dimensions'], lod_stats['dimensions'])))
        loose_extrema = any(abs(a - b) > comparisons['toleranceMetersXYZ'][axis] for axis, (a, b) in enumerate(zip(lod_stats['allVertexBounds']['dimensions'], lod_stats['dimensions'])))
        diagnosis = ('Blender object bounding boxes included loose vertices not referenced by faces; glTF exported the actual faces correctly.' if loose_extrema else
                     'Blender object bounding-box cache differed from evaluated face geometry; GLB roundtrip actual faces match.' if differing_bounds else
                     'The earlier bound-box-based measurement failed; current evaluated face geometry, triangles and world extrema agree without changing tolerance or bytes.')
        staging_preview = OUT / ('.' + IDENT + '.repair_' + uuid.uuid4().hex[:10] + '.preview.png')
        HELPERS['render_preview'](qa_scene, qa_collections[0], staging_preview, qa_stats)
        assert HELPERS['state'](original_objects) == original_state, 'Existing object channels changed during repair'
        assert HELPERS['source_material_snapshot'](source_objects) == original_materials, 'Source/shared material or image changed during repair'
        assert sha(SOURCE) == SOURCE_SHA and sha(staging) == repair['stagingSha256']
        # Publication copies the verified bytes. The original failed staging GLB
        # remains available as evidence and is neither renamed nor re-exported.
        preserve_copy(staging, FINAL)
        preserve_copy(staging_preview, PREVIEW)
        source_doc = HELPERS['doc_from_glb'](SOURCE)
        batching = {'inputSourceMeshes': source_stats['meshes'], 'outputMaterialBatches': lod_stats['meshes'],
                    'trianglesAfter': expected, 'audit': 'Read from preserved LOD and source scenes; no geometry operation performed by repair'}
        record = {'id': IDENT, 'name': 'Estação Central de Amsterdam · LOD1', 'category': 'Trens',
                  'sourceRelative': HELPERS['RELATIVE'], 'sourceSha256': SOURCE_SHA,
                  'sourceFiles': [{'file': HELPERS['RELATIVE'], 'sha256': SOURCE_SHA, 'bytes': SOURCE.stat().st_size}],
                  'credits': source_doc.get('asset', {}).get('extras', {}), 'licenseStatus': 'attribution',
                  'originalTriangles': source_stats['triangles'], 'status': 'validated', 'reimportValidated': True,
                  'originalRig': False, 'rigged': False, 'animated': False, 'animations': [], 'skins': 0,
                  'url': '/assets/additions20261016/' + FINAL.name, 'bytes': FINAL.stat().st_size,
                  'sha256': sha(FINAL), 'triangles': expected, 'preparedTriangles': lod_stats['triangles'],
                  'meshPrimitiveTriangles': expected, 'meshes': qa_stats['meshes'], 'dimensions': qa_stats['dimensions'],
                  'dimensionsConvention': 'Blender XYZ meters; GLB exports Y up',
                  'sourceDimensionsGLTF_XYZ': [source_stats['dimensions'][0], source_stats['dimensions'][2], source_stats['dimensions'][1]],
                  'sourceDimensionsBlenderXYZ': source_stats['dimensions'], 'sourceUnits': 'meters, glTF convention',
                  'sourceScaleRetained': 1, 'normalization': 'Translation only; centered XY and grounded Z; not fitted to city',
                  'geometryModified': True, 'lod': {'level': 1, 'targetTriangles': HELPERS['TARGET'],
                      'maxTriangles': HELPERS['HARD_MAX'], 'actualTriangles': expected,
                      'method': 'Original preparation: per-mesh collapse on copied meshes; static world matrices baked into copies, batched by material. Repair measured and reused those bytes only.'},
                  'originalPreserved': True, 'originalSourceScene': source_scene.name,
                  'derivativeScene': lod_scene.name, 'qaScene': qa_scene.name,
                  'sourceCollection': source_collections[0].name, 'collection': lod_collections[0].name,
                  'hierarchyPreserved': False, 'sourceHierarchyPreserved': True,
                  'derivativeMaterialBatches': lod_stats['meshes'], 'materialBatching': batching,
                  'textureCapPixels': HELPERS['TEXTURE_CAP'], 'textures': texture_details,
                  'materialRecovery': 'Original supplied PBR copied into owned materials and images by preparation; original shared datablocks preserved during repair',
                  'modifications': 'Static copied LOD; <=27 material batches; owned textures <=1024px; original meter scale retained; source hierarchy kept in SOURCE scene. Repair did not re-export or alter geometry.',
                  'validation': 'Existing GLB reimport: equal triangles and face-referenced world extrema with original tolerance, finite vertices, visible meshes, delivered textures <=1024px, actual delivered GLB rendered at 512px. Existing source and project objects unchanged during repair.',
                  'preview': '/assets/additions20261016/' + PREVIEW.name, 'previewSha256': sha(PREVIEW),
                  'previewSize': [512, 512], 'previewEvidence': 'Actual delivered GLB reimport rendered in Blender EEVEE',
                  'repairDiagnosis': diagnosis, 'prepOwner': OWNER}
        repair.update({'status': 'validated', 'diagnosis': diagnosis, 'comparison': comparisons,
                       'stagingPreviewPreserved': str(staging_preview), 'publishedGLB': str(FINAL),
                       'publishedPreview': str(PREVIEW), 'sha256': sha(FINAL), 'previewSha256': sha(PREVIEW),
                       'sourceScene': source_scene.name, 'derivativeScene': lod_scene.name, 'qaScene': qa_scene.name,
                       'previousObjectsPreservedDuringRepair': len(original_objects),
                       'sourceAndSharedMaterialsUnchangedDuringRepair': True, 'originalDiskSha256Unchanged': True,
                       'deliveredTextureDimensions': [list(image.size) for image in qa_images],
                       'geometryAlteredByRepair': False, 'reexportPerformedByRepair': False,
                       'blenderVersion': bpy.app.version_string})
        write_json(CATALOG_REPORT, [record])
        write_json(REPAIR_REPORT, repair)
        write_json(QA_REPORT, repair)
        print('PREP_STATION_REPAIR_20261016 ' + json.dumps({'status': 'validated', 'id': IDENT,
              'triangles': expected, 'meshes': qa_stats['meshes'], 'dimensions': qa_stats['dimensions'],
              'diagnosis': diagnosis, 'masterSaved': False}))
    except Exception:
        repair.update({'status': 'failed', 'error': traceback.format_exc()})
        write_json(REPAIR_REPORT, repair)
        raise
    finally:
        for window, scene in windows:
            window.scene = scene


if __name__ == '__main__':
    main()
