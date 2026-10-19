"""Additive PREP costumes and a real, local Mixamo upload staging mesh.

Outside Blender: python prep_costumes_mixamo.py --stage-obj
The staging copy contains the supplied mesh's rest vertices, not a fabricated rig
or downloaded Mixamo animation. Originals and previously generated files remain
untouched. Run the costume entry point inside Blender after the city builder.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_glb(path):
    raw = Path(path).read_bytes()
    magic, version, total = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or total != len(raw):
        raise ValueError('Expected a complete glTF 2.0 binary')
    doc, binary, offset = None, None, 12
    while offset < len(raw):
        length, kind = struct.unpack_from('<II', raw, offset)
        payload = raw[offset + 8:offset + 8 + length]
        if kind == 0x4E4F534A:
            doc = json.loads(payload)
        elif kind == 0x004E4942:
            binary = payload
        offset += 8 + length
    if doc is None or binary is None:
        raise ValueError('Embedded JSON and binary chunks are required')
    return doc, binary


def accessor_array(doc, binary, index):
    """Read actual glTF offsets/strides, including sparse accessors."""
    import numpy as np
    acc = doc['accessors'][index]
    types = {5120: '<i1', 5121: '<u1', 5122: '<i2', 5123: '<u2',
             5125: '<u4', 5126: '<f4'}
    widths = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4,
              'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
    width, dtype = widths[acc['type']], np.dtype(types[acc['componentType']])
    if 'bufferView' in acc:
        view = doc['bufferViews'][acc['bufferView']]
        if view.get('buffer', 0) != 0:
            raise ValueError('External buffers are not supported by this stage')
        offset = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
        stride = view.get('byteStride', dtype.itemsize * width)
        out = np.ndarray((acc['count'], width), dtype=dtype, buffer=binary,
                         offset=offset, strides=(stride, dtype.itemsize)).copy()
    else:
        out = np.zeros((acc['count'], width), dtype=dtype)
    sparse = acc.get('sparse')
    if sparse:
        iv = doc['bufferViews'][sparse['indices']['bufferView']]
        vd = doc['bufferViews'][sparse['values']['bufferView']]
        indices = np.frombuffer(binary, dtype=types[sparse['indices']['componentType']],
                                count=sparse['count'], offset=iv.get('byteOffset', 0)
                                + sparse['indices'].get('byteOffset', 0))
        values = np.frombuffer(binary, dtype=dtype, count=sparse['count'] * width,
                               offset=vd.get('byteOffset', 0)
                               + sparse['values'].get('byteOffset', 0)).reshape(-1, width)
        out[indices] = values
    if acc.get('normalized') and acc['componentType'] != 5126:
        maximum = np.iinfo(dtype).max
        out = np.maximum(out.astype(float) / maximum, -1)
    return out


def node_matrix(node):
    import numpy as np
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=float).reshape(4, 4, order='F')
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    rotation = np.array([
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)]])
    out = np.eye(4)
    out[:3, :3] = rotation @ np.diag(node.get('scale', [1, 1, 1]))
    out[:3, 3] = node.get('translation', [0, 0, 0])
    return out


def mesh_primitives(doc, binary):
    import numpy as np
    scene = doc['scenes'][doc.get('scene', 0)]
    rows = []

    def visit(index, parent, ancestry):
        if index in ancestry:
            raise ValueError('Cyclic glTF hierarchy')
        node = doc['nodes'][index]
        world = parent @ node_matrix(node)
        if 'mesh' in node:
            if 'skin' in node:
                raise ValueError('Upload staging requires a supplied static rest mesh')
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode', 4) != 4:
                    raise ValueError('Upload staging requires triangle primitives')
                attrs = primitive['attributes']
                pos = accessor_array(doc, binary, attrs['POSITION']).astype(float)
                pos = (np.column_stack((pos, np.ones(len(pos)))) @ world.T)[:, :3]
                normal = None
                if 'NORMAL' in attrs:
                    normal = accessor_array(doc, binary, attrs['NORMAL']).astype(float)
                    normal = normal @ np.linalg.inv(world[:3, :3])
                    normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], 1e-12)
                uv = accessor_array(doc, binary, attrs['TEXCOORD_0']).astype(float) if 'TEXCOORD_0' in attrs else None
                indices = accessor_array(doc, binary, primitive['indices']).ravel() if 'indices' in primitive else np.arange(len(pos))
                if len(indices) % 3 or len(indices) == 0 or indices.max() >= len(pos):
                    raise ValueError('Invalid triangle indices')
                faces = indices.reshape(-1, 3).astype(int)
                if np.linalg.det(world[:3, :3]) < 0:
                    faces = faces[:, [0, 2, 1]]
                if not np.isfinite(pos).all():
                    raise ValueError('Nonfinite vertex position')
                rows.append({'name': node.get('name', f'node_{index}'), 'positions': pos,
                             'normals': normal, 'uv': uv, 'faces': faces,
                             'material': primitive.get('material', -1)})
        for child in node.get('children', []):
            visit(child, world, ancestry | {index})
    for root in scene['nodes']:
        visit(root, np.eye(4), set())
    if not rows:
        raise ValueError('No source geometry')
    return rows


def stage_obj(source=None, output_dir=None, height=1.8):
    import numpy as np
    source = Path(source or ROOT / 'frontend/public/assets/supplied/SUP_jumpsuit_low_poly.glb')
    output_dir = Path(output_dir or ROOT / 'art/mixamo_stage/Jumpsuit_20261005')
    name = 'PREP_Jumpsuit_Upload_20261005'
    report_path = ROOT / 'reports/mixamo_stage_20261005.json'
    obj_path, mtl_path = output_dir / (name + '.obj'), output_dir / (name + '.mtl')
    if obj_path.exists() or mtl_path.exists():
        raise FileExistsError('Upload stage already exists; choose a new output directory')
    source_hash = sha256(source)
    doc, binary = read_glb(source)
    rows = mesh_primitives(doc, binary)
    all_pos = np.concatenate([row['positions'] for row in rows])
    lo, hi = all_pos.min(axis=0), all_pos.max(axis=0)
    if height <= 0 or hi[1] - lo[1] <= 0:
        raise ValueError('Expected upright Y-up humanoid')
    scale = height / (hi[1] - lo[1])
    origin = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    output_dir.mkdir(parents=True, exist_ok=True)
    textures = []
    material_lines = ['# Author base colors from supplied GLB; no rebaking.']
    for i, mat in enumerate(doc.get('materials', [])):
        pbr = mat.get('pbrMetallicRoughness', {})
        color = pbr.get('baseColorFactor', [1, 1, 1, 1])
        material_lines += [f'newmtl PREP_Material_{i}', 'Ka 0 0 0',
                           'Kd ' + ' '.join(map(str, color[:3])), 'Ks 0.04 0.04 0.04',
                           f'd {color[3]}', 'Ns 10', 'illum 2']
        if 'baseColorTexture' in pbr:
            tex = doc['textures'][pbr['baseColorTexture']['index']]
            img = doc['images'][tex['source']]
            if 'bufferView' not in img:
                raise ValueError('Embedded author image expected')
            view = doc['bufferViews'][img['bufferView']]
            image_bytes = binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
            extension = '.png' if img['mimeType'] == 'image/png' else '.jpg'
            filename = f'{name}_color_{i}{extension}'
            image_path = output_dir / filename
            image_path.write_bytes(image_bytes)
            textures.append({'path': str(image_path), 'sha256': sha256(image_path),
                             'sourceImage': tex['source'], 'bytes': len(image_bytes)})
            material_lines += ['map_Kd ' + filename]
        material_lines += ['']
    mtl_path.write_text('\n'.join(material_lines), encoding='utf-8')
    vertex_offset, uv_offset, normal_offset, face_count = 0, 0, 0, 0
    with obj_path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write('# PREP supplied rest-mesh stage. Y-up, +Z front; 1 unit = 1 meter.\n')
        handle.write('# Source pose preserved: arms down and separate; not a T pose.\n')
        handle.write('mtllib ' + mtl_path.name + '\n')
        for i, row in enumerate(rows):
            handle.write(f'o PREP_Jumpsuit_{i}\n')
            positions = (row['positions'] - origin) * scale
            for value in positions:
                handle.write('v ' + ' '.join(f'{x:.9g}' for x in value) + '\n')
            if row['uv'] is not None:
                for u, v in row['uv']:
                    handle.write(f'vt {u:.9g} {1-v:.9g}\n')
            if row['normals'] is not None:
                for value in row['normals']:
                    handle.write('vn ' + ' '.join(f'{x:.9g}' for x in value) + '\n')
            if row['material'] >= 0:
                handle.write(f'usemtl PREP_Material_{row["material"]}\n')
            for face in row['faces']:
                refs = []
                for index in face:
                    v = int(index) + vertex_offset + 1
                    uv = str(int(index) + uv_offset + 1) if row['uv'] is not None else ''
                    normal = str(int(index) + normal_offset + 1) if row['normals'] is not None else ''
                    refs.append(f'{v}/{uv}/{normal}' if normal else f'{v}/{uv}' if uv else str(v))
                handle.write('f ' + ' '.join(refs) + '\n')
            vertex_offset += len(positions)
            uv_offset += len(row['uv']) if row['uv'] is not None else 0
            normal_offset += len(row['normals']) if row['normals'] is not None else 0
            face_count += len(row['faces'])
    zip_path = output_dir / (name + '.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in [obj_path, mtl_path, *[Path(t['path']) for t in textures]]:
            archive.write(file, file.name)
    # Read the written OBJ back: every face index must refer to a real record.
    counts = {'v': 0, 'vt': 0, 'vn': 0, 'f': 0}
    for line in obj_path.read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts or parts[0] not in counts:
            continue
        counts[parts[0]] += 1
        if parts[0] == 'v' and not all(math.isfinite(float(x)) for x in parts[1:]):
            raise ValueError('Written OBJ has a nonfinite vertex')
        if parts[0] == 'f':
            for ref in parts[1:]:
                for key, value in zip(['v', 'vt', 'vn'], ref.split('/')):
                    if value and not 1 <= int(value) <= counts[key]:
                        raise ValueError('Written OBJ has an invalid face index')
    assert counts['v'] == vertex_offset and counts['f'] == face_count
    assert sha256(source) == source_hash, 'Source changed during staging'
    report = {'version': 1, 'source': str(source), 'sourceSha256': source_hash,
              'sourceUnchanged': True, 'obj': str(obj_path), 'mtl': str(mtl_path),
              'bundle': str(zip_path), 'objSha256': sha256(obj_path),
              'counts': counts, 'materials': len(doc.get('materials', [])),
              'authorTextures': textures, 'axes': 'Y up; +Z front (source convention)',
              'restPose': 'Source arms down, separated; no T-pose conversion',
              'heightMeters': height, 'sourceBounds': [lo.tolist(), hi.tolist()],
              'stageBounds': [((lo-origin)*scale).tolist(), ((hi-origin)*scale).tolist()],
              'sourceSkins': len(doc.get('skins', [])), 'sourceAnimations': len(doc.get('animations', [])),
              'uploadedToMixamo': False, 'autoRiggedByMixamo': False}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return report


def build_costumes(export=True, render=True, save=True):
    """Run only inside Blender; add garments to the already created city NPCs.

    Each garment vertex has one normalized influence on an existing bone. All
    source meshes, pivots, hierarchies, skin weights and rest bones are untouched.
    Animation sampling temporarily selects a real existing Walk strip, then
    restores the original action, slot, track mutes, frame and scene.
    """
    import bpy
    import numpy as np
    from mathutils import Matrix, Vector

    scene = bpy.data.scenes.get('00_ARAPIRACA_CYBER_20261005')
    if scene is None:
        raise RuntimeError('Run the Arapiraca city builder first')
    roots = [o for o in scene.objects if o.name.startswith('NPC_ARAP_') and o.type == 'EMPTY']
    roots = [o for o in roots if any(key in o.name for key in
             ('doctor_horror_hospital', 'jumpsuit_low_poly', 'school_girl_v21'))]
    if not roots:
        raise RuntimeError('No NPC_ARAP humanoid roots found; check catalog SUP_ IDs')
    out = ROOT / 'frontend/public/assets/cyber'
    reports = ROOT / 'reports/costumes'
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    final_blend = ROOT / 'art/blender/PREPARATORIO_PROJETO_COSTUMES_20261005.blend'
    if save and final_blend.exists():
        raise FileExistsError('Costume checkpoint already exists; preserve it')
    selected_before = list(bpy.context.selected_objects)
    active_before = bpy.context.view_layer.objects.active
    scene_before = bpy.context.window.scene
    bpy.context.window.scene = scene

    def descendants(root):
        result = [root]
        for child in root.children:
            result.extend(descendants(child))
        return result

    def fingerprint(objects):
        """Record all authored data whose accidental mutation would matter."""
        rows = []
        for obj in objects:
            row = {'name': obj.name, 'parent': obj.parent.name if obj.parent else None,
                   'parentType': obj.parent_type, 'parentBone': obj.parent_bone,
                   'basis': [float(x) for line in obj.matrix_basis for x in line],
                   'parentInverse': [float(x) for line in obj.matrix_parent_inverse for x in line]}
            if obj.type == 'MESH':
                coords = np.array([tuple(v.co) for v in obj.data.vertices], dtype='<f8')
                weights = [(v.index, [(g.group, float(g.weight)) for g in v.groups]) for v in obj.data.vertices]
                row.update(geometryHash=hashlib.sha256(coords.tobytes()).hexdigest(),
                           weightsHash=hashlib.sha256(json.dumps(weights).encode()).hexdigest(),
                           materials=[m.name if m else None for m in obj.data.materials],
                           modifiers=[(m.name, m.type, getattr(getattr(m, 'object', None), 'name', None)) for m in obj.modifiers])
            elif obj.type == 'ARMATURE':
                row['bones'] = [(b.name, tuple(b.head_local), tuple(b.tail_local),
                                 tuple(float(x) for line in b.matrix_local for x in line),
                                 b.parent.name if b.parent else None) for b in obj.data.bones]
            rows.append(row)
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def pbr(name, rgba, roughness=.65):
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
            mat.diffuse_color = rgba
            principled = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            principled.inputs['Base Color'].default_value = rgba
            principled.inputs['Roughness'].default_value = roughness
            principled.inputs['Metallic'].default_value = 0
        return mat

    mats = {'scrub': pbr('MAT_COSTUME_Scrub_Teal_20261005', (.015, .31, .32, 1)),
            'coat': pbr('MAT_COSTUME_Coat_White_20261005', (.92, .95, .94, 1)),
            'trim': pbr('MAT_COSTUME_Trim_Navy_20261005', (.015, .045, .08, 1)),
            'badge': pbr('MAT_COSTUME_Badge_Cyan_20261005', (.02, .55, .72, 1))}
    collection = bpy.data.collections.get('ARAP_COSTUMES_20261005')
    if collection is None:
        collection = bpy.data.collections.new('ARAP_COSTUMES_20261005')
        scene.collection.children.link(collection)
    records = []
    try:
        for root in roots:
            source_objects = descendants(root)
            if any(o.get('prep_costume_owner') == root.name for o in source_objects):
                raise RuntimeError('Costume already attached to ' + root.name)
            arm = next((o for o in source_objects if o.type == 'ARMATURE'), None)
            if arm is None:
                raise RuntimeError('Missing rig for ' + root.name)
            required = ['hips', 'chest', 'neck', 'L_upper_arm', 'R_upper_arm',
                        'L_forearm', 'R_forearm', 'L_thigh', 'R_thigh', 'L_shin', 'R_shin']
            if any(n not in arm.data.bones for n in required):
                raise RuntimeError('Rig lacks fitted humanoid bones: ' + root.name)
            key = root.name.removeprefix('NPC_ARAP_').removeprefix('SUP_')
            export_name = 'CHR_PREP_Nurse_Coat_20261005.glb' if key == 'doctor_horror_hospital' else f'CHR_PREP_{key}_Coat_20261005.glb'
            export_path = out / export_name
            if export and export_path.exists():
                raise FileExistsError(str(export_path))
            original_hash = fingerprint(source_objects)
            bones = arm.data.bones
            hips, neck = bones['hips'].head_local.copy(), bones['neck'].head_local.copy()
            left, right_head = bones['L_upper_arm'].head_local.copy(), bones['R_upper_arm'].head_local.copy()
            up = (neck - hips).normalized()
            right_axis = (left - right_head).normalized()
            right_axis = (right_axis - up * right_axis.dot(up)).normalized()
            front = right_axis.cross(up).normalized()
            # Positive width points toward the character's left; front is -Y
            # in the original Blender convention. Imported transforms preserve
            # that frame without applying a rotation to any existing object.
            shoulder_span = (left - right_head).length
            center = (left + right_head) * .5
            waist = hips + up * .02
            arm_inverse = arm.matrix_world.inverted()
            source_meshes = [o for o in source_objects if o.type == 'MESH']
            body_points = [arm_inverse @ o.matrix_world @ v.co for o in source_meshes for v in o.data.vertices]

            def percentile(values, quantile, fallback):
                return float(np.percentile(values, quantile)) if len(values) else fallback

            projected = [(p - hips).dot(up) for p in body_points]
            torso_height = (neck - hips).length
            torso_points = [p for p, h in zip(body_points, projected)
                            if .08 < h < torso_height * .90 and abs((p - hips).dot(right_axis)) < shoulder_span * .55]
            width = max(shoulder_span * .54, percentile([abs((p - hips).dot(right_axis)) for p in torso_points], 96, shoulder_span * .5) + .018)
            depth_front = max(shoulder_span * .22, percentile([(p - hips).dot(front) for p in torso_points], 97, .10) + .025)
            depth_back = max(shoulder_span * .20, percentile([-(p - hips).dot(front) for p in torso_points], 97, .09) + .025)
            generated = []

            def garment(name, vertices, faces, material, bone):
                mesh = bpy.data.meshes.new(name + '_Mesh')
                mesh.from_pydata([tuple(v) for v in vertices], [], faces)
                mesh.update()
                obj = bpy.data.objects.new(name, mesh)
                collection.objects.link(obj)
                obj.parent = arm
                obj.matrix_parent_inverse = Matrix.Identity(4)
                obj.matrix_basis = Matrix.Identity(4)
                obj.data.materials.append(mats[material])
                group = obj.vertex_groups.new(name=bone)
                group.add(list(range(len(vertices))), 1.0, 'REPLACE')
                mod = obj.modifiers.new('PREP_Costume_Skin', 'ARMATURE')
                mod.object = arm
                obj['prep_costume_owner'] = root.name
                obj['prep_costume_bone'] = bone
                obj['prep_costume_source_preserved'] = True
                generated.append(obj)
                return obj

            def box(name, c, half, material, bone, axes=None):
                a, b, d = axes or (right_axis, front, up)
                verts = [c + a * x * half[0] + b * y * half[1] + d * z * half[2]
                         for x, y, z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                         (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
                faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),
                         (1,2,6,5),(2,3,7,6),(3,0,4,7)]
                if a.cross(b).dot(d) < 0:
                    faces = [tuple(reversed(face)) for face in faces]
                return garment(name, verts, faces, material, bone)

            def ring_body(name, rings, material, bone):
                verts = []
                sides = 12
                for c, w, df, db in rings:
                    for j in range(sides):
                        t = j * math.tau / sides
                        depth = df if math.sin(t) >= 0 else db
                        verts.append(c + right_axis * math.cos(t) * w + front * math.sin(t) * depth)
                faces = [(k*sides+j, k*sides+(j+1)%sides, (k+1)*sides+(j+1)%sides, (k+1)*sides+j)
                         for k in range(len(rings)-1) for j in range(sides)]
                if right_axis.cross(front).dot(up) < 0:
                    faces = [tuple(reversed(face)) for face in faces]
                return garment(name, verts, faces, material, bone)

            def tube(name, bone_name, radius, material, start=.02, end=.94):
                bone = bones[bone_name]
                axis = (bone.tail_local - bone.head_local).normalized()
                radial = front - axis * front.dot(axis)
                if radial.length < 1e-5:
                    radial = right_axis - axis * right_axis.dot(axis)
                radial.normalize()
                other = axis.cross(radial).normalized()
                rings = [bone.head_local.lerp(bone.tail_local, t) for t in (start, end)]
                verts = [c + (radial * math.cos(j*math.tau/8) + other * math.sin(j*math.tau/8))*radius
                         for c in rings for j in range(8)]
                return garment(name, verts, [(j,(j+1)%8,8+(j+1)%8,8+j) for j in range(8)], material, bone_name)

            def limb_radius(bone_name, fallback):
                bone = bones[bone_name]
                a, delta = bone.head_local, bone.tail_local-bone.head_local
                distances = []
                for point in body_points:
                    t = (point-a).dot(delta) / delta.length_squared
                    distance = (point-(a+delta*t)).length
                    if .25 < t < .8 and distance < shoulder_span * .32:
                        distances.append(distance)
                return max(fallback, percentile(distances, 90, fallback) + .012)

            ring_body('SCRUB_' + key + '_Torso',
                      [(waist, width*.92, depth_front*.95, depth_back*.95),
                       (center-up*.045, width, depth_front, depth_back),
                       (neck-up*.006, shoulder_span*.21, depth_front*.63, depth_back*.63)], 'scrub', 'chest')
            ring_body('SCRUB_' + key + '_Waist',
                      [(hips-up*.10, width*.89, depth_front*.98, depth_back*.98),
                       (waist+up*.028, width*.93, depth_front*.98, depth_back*.98)], 'scrub', 'hips')
            # Coat back and side panels split at the waist so pelvis movement
            # does not force all cloth to rotate with the chest during walking.
            upper_height = max(.10, (neck - waist).dot(up) * .95)
            upper_center = waist + up * upper_height * .5
            lower_height = torso_height * .36
            lower_center = waist - up * lower_height * .5
            for label, c, h, bone in [('Upper', upper_center, upper_height, 'chest'),
                                      ('Lower', lower_center, lower_height, 'hips')]:
                box('COAT_' + key + '_Back' + label, c-front*(depth_back+.017),
                    (width+.018, .012, h*.5), 'coat', bone)
                for side, sign in [('L', 1), ('R', -1)]:
                    box('COAT_' + key + '_Side' + side + label,
                        c+right_axis*(width+.015)*sign+front*(depth_front-depth_back)*.5,
                        (.013, (depth_front+depth_back)*.5+.025, h*.5), 'coat', bone)
                    opening = shoulder_span * .13
                    half_width = (width+.02-opening)*.5
                    panel_center = (opening+width+.02)*.5
                    box('COAT_' + key + '_Front' + side + label,
                        c+front*(depth_front+.023)+right_axis*panel_center*sign,
                        (half_width, .012, h*.5), 'coat', bone)
                    if label == 'Upper':
                        pocket_center = c-up*h*.22+front*(depth_front+.041)+right_axis*panel_center*sign
                        box('COAT_' + key + '_Pocket' + side, pocket_center,
                            (half_width*.72, .009, h*.13), 'coat', bone)
            for side in ['L', 'R']:
                upper_radius = limb_radius(side+'_upper_arm', shoulder_span*.12)
                lower_radius = limb_radius(side+'_forearm', shoulder_span*.10)
                tube('SCRUB_' + key + '_' + side + '_Sleeve', side+'_upper_arm', upper_radius, 'scrub', 0, .64)
                tube('COAT_' + key + '_' + side + '_UpperSleeve', side+'_upper_arm', upper_radius+.014, 'coat', .01, 1)
                tube('COAT_' + key + '_' + side + '_LowerSleeve', side+'_forearm', lower_radius+.013, 'coat', .02, .94)
                thigh_radius = limb_radius(side+'_thigh', shoulder_span*.14)
                shin_radius = limb_radius(side+'_shin', shoulder_span*.12)
                tube('SCRUB_' + key + '_' + side + '_Trouser', side+'_thigh', thigh_radius, 'scrub', .02, .98)
                tube('SCRUB_' + key + '_' + side + '_LowerTrouser', side+'_shin', shin_radius, 'scrub', .01, .85)
            badge_center = neck-up*torso_height*.25+front*(depth_front+.045)+right_axis*width*.57
            box('COAT_' + key + '_NameBadge', badge_center, (width*.19, .009, torso_height*.044), 'badge', 'chest')
            box('COAT_' + key + '_BadgeLine', badge_center+front*.012, (width*.14, .003, torso_height*.008), 'trim', 'chest')

            assert all(o.parent == arm and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers) for o in generated)
            assert all(len(v.groups) == 1 and abs(v.groups[0].weight-1) < 1e-6 for o in generated for v in o.data.vertices)
            animation_data = arm.animation_data
            action_before = animation_data.action if animation_data else None
            slot_before = getattr(animation_data, 'action_slot', None) if animation_data else None
            track_states = [(t, t.mute) for t in animation_data.nla_tracks] if animation_data else []
            frame_before = scene.frame_current
            walk_track = next((t for t, _ in track_states if t.name.rsplit('|',1)[-1] == 'Walk' or t.name.endswith('_Walk')), None)
            if walk_track is None:
                walk_track = next((t for t, _ in track_states if any('Walk' in s.action.name for s in t.strips if s.action)), None)
            displacement = 0
            sample_clip = None
            try:
                if animation_data and walk_track and walk_track.strips:
                    strip = walk_track.strips[0]
                    for track, _ in track_states:
                        track.mute = True
                    animation_data.action = strip.action
                    if hasattr(animation_data, 'action_slot') and getattr(strip, 'action_slot', None):
                        animation_data.action_slot = strip.action_slot
                    sample_clip = strip.action.name

                    def evaluated_points(frame):
                        scene.frame_set(frame)
                        bpy.context.view_layer.update()
                        depsgraph = bpy.context.evaluated_depsgraph_get()
                        return np.concatenate([np.array([tuple(o.matrix_world @ v.co)
                                                for v in o.evaluated_get(depsgraph).data.vertices]) for o in generated])
                    one, thirty = evaluated_points(1), evaluated_points(30)
                    assert np.isfinite(one).all() and np.isfinite(thirty).all()
                    displacement = float(np.linalg.norm(thirty-one, axis=1).max())
                    assert displacement > .001, 'Garments did not follow the existing Walk clip'
            finally:
                if animation_data:
                    animation_data.action = action_before
                    if action_before and slot_before:
                        animation_data.action_slot = slot_before
                    for track, mute in track_states:
                        track.mute = mute
                scene.frame_set(frame_before)
                bpy.context.view_layer.update()
            assert fingerprint(source_objects) == original_hash, 'Existing body or rig changed'
            record = {'id': 'COSTUME_' + key, 'sourceRoot': root.name,
                      'sourcePreserved': True, 'sourceFingerprint': original_hash,
                      'rig': arm.name, 'bones': len(arm.data.bones),
                      'objects': [{'name': o.name, 'bone': o['prep_costume_bone'],
                                   'vertices': len(o.data.vertices), 'material': o.data.materials[0].name,
                                   'parent': o.parent.name, 'weight': 1} for o in generated],
                      'weightCoverage': 1, 'sampleClip': sample_clip,
                      'displacementFrame1To30Meters': displacement,
                      'materials': {k: list(m.diffuse_color) for k,m in mats.items()},
                      'quality': 'Rigid low-poly clothing prototype; visually review intersections before release',
                      'mixamoAnimation': False}

            if export:
                # Independent object copies isolate city placement and animated
                # strip mutes. Mesh geometry and source armature stay untouched.
                staged = bpy.data.scenes.new('COSTUME_EXPORT_' + key)
                staged.unit_settings.system = 'METRIC'
                staged.unit_settings.scale_length = 1
                staged.render.fps = scene.render.fps
                bpy.context.window.scene = staged
                copies = {o: o.copy() for o in descendants(root)}
                for old, copied in copies.items():
                    if old.type == 'ARMATURE':
                        copied.data = old.data.copy()
                    staged.collection.objects.link(copied)
                    if old.parent in copies:
                        copied.parent = copies[old.parent]
                    for modifier in copied.modifiers:
                        if modifier.type == 'ARMATURE' and modifier.object in copies:
                            modifier.object = copies[modifier.object]
                staged_root = copies[root]
                staged_root.location = (0,0,0)
                staged_arm = copies[arm]
                if staged_arm.animation_data:
                    staged_arm.animation_data.action = None
                    for track in staged_arm.animation_data.nla_tracks:
                        track.mute = False
                staged.frame_set(1)
                bpy.context.view_layer.update()
                points = [o.matrix_world @ v.co for o in copies.values() if o.type == 'MESH' for v in o.data.vertices]
                min_z = min(p.z for p in points)
                staged_root.location.z -= min_z
                bpy.context.view_layer.update()
                for obj in staged.objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = staged_arm
                bpy.ops.export_scene.gltf(filepath=str(export_path), export_format='GLB',
                    use_selection=True, use_active_scene=True, export_yup=True,
                    export_animations=True, export_skins=True, export_animation_mode='NLA_TRACKS',
                    export_lights=False, export_cameras=False, export_extras=True, export_image_format='AUTO')
                doc, _binary = read_glb(export_path)
                clips = [a.get('name', '') for a in doc.get('animations', [])]
                assert doc.get('skins') and any('Walk' in n for n in clips) and any('Dance' in n for n in clips), clips
                costume_nodes = [n for n in doc['nodes'] if n.get('name','').startswith(('SCRUB_', 'COAT_'))]
                assert len(costume_nodes) >= len(generated)
                assert all('mesh' in n and 'skin' in n for n in costume_nodes)
                assert all('mesh' in n for n in doc['nodes'] if 'skin' in n)

                validation = bpy.data.scenes.new('COSTUME_VALIDATE_' + key)
                validation.unit_settings.system = 'METRIC'
                validation.unit_settings.scale_length = 1
                bpy.context.window.scene = validation
                bpy.ops.import_scene.gltf(filepath=str(export_path))
                validation_arm = next(o for o in validation.objects if o.type == 'ARMATURE')
                validation_garments = [o for o in validation.objects if o.type == 'MESH' and o.name.startswith(('SCRUB_', 'COAT_'))]
                assert len(validation_garments) >= len(generated)
                assert len(validation_arm.data.bones) >= len(arm.data.bones)-1
                assert all(v.groups for o in validation_garments for v in o.data.vertices)
                assert all(any(m.type == 'ARMATURE' and m.object == validation_arm for m in o.modifiers) for o in validation_garments)
                if validation_arm.animation_data:
                    for track in validation_arm.animation_data.nla_tracks:
                        track.mute = 'Idle' not in track.name
                record.update(url='/assets/cyber/'+export_path.name, path=str(export_path),
                              bytes=export_path.stat().st_size, sha256=sha256(export_path),
                              clips=clips, reimportValidated=True, reimportGarmentMeshes=len(validation_garments))
                if render:
                    validation.world = bpy.data.worlds.new('COSTUME_WORLD_' + key)
                    validation.world.color = (.23,.23,.23)
                    bpy.ops.object.light_add(type='AREA', location=(0,-3,3.5))
                    bpy.context.object.data.energy = 400
                    bpy.context.object.data.size = 4
                    bpy.ops.object.light_add(type='AREA', location=(2,2,3))
                    bpy.context.object.data.energy = 250
                    bpy.context.object.data.size = 3
                    bpy.ops.object.camera_add(location=(2.2,-4.5,1.8))
                    camera = bpy.context.object
                    camera.rotation_euler = (Vector((0,0,.9))-camera.location).to_track_quat('-Z','Y').to_euler()
                    camera.data.type = 'ORTHO'
                    camera.data.ortho_scale = 2.2
                    validation.camera = camera
                    validation.render.engine = 'CYCLES'
                    validation.cycles.samples = 8
                    validation.render.resolution_x = 480
                    validation.render.resolution_y = 600
                    validation.render.resolution_percentage = 100
                    validation.render.filepath = str(reports / (key+'_costume.png'))
                    validation.frame_set(1)
                    bpy.ops.render.render(write_still=True)
                    record['preview'] = validation.render.filepath
                # Keep validation scenes as editable preview pages. Dispose
                # only temporary copied source objects to avoid body duplicates.
                bpy.context.window.scene = scene
                stage_objects = list(staged.objects)
                staged_arm_data = staged_arm.data
                bpy.data.scenes.remove(staged)
                for obj in stage_objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                if staged_arm_data.users == 0:
                    bpy.data.armatures.remove(staged_arm_data)
                assert fingerprint(source_objects) == original_hash, 'Export changed source body or rig'
            records.append(record)
            (reports / (key+'_costume.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        bpy.context.window.scene = scene
        scene['prep_costumes_20261005'] = len(records)
        scene['prep_costume_note'] = 'Additive rigid bone-weighted prototypes; source rigs and animations preserved.'
        summary = {'version': 1, 'blenderVersion': bpy.app.version_string,
                   'scene': scene.name, 'collection': collection.name,
                   'characters': records, 'costumeObjects': sum(len(r['objects']) for r in records),
                   'sourceMeshesAndRigsPreserved': True, 'actualMixamoDownload': False}
        if save:
            bpy.ops.wm.save_as_mainfile(filepath=str(final_blend), compress=True, copy=True)
            summary['checkpoint'] = str(final_blend)
        (reports / 'costumes_20261005.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False))
        return summary
    finally:
        bpy.context.window.scene = scene_before
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in selected_before:
            if obj.name in bpy.context.scene.objects:
                obj.select_set(True)
        if active_before and active_before.name in bpy.context.scene.objects:
            bpy.context.view_layer.objects.active = active_before


def main():
    # Blender launches with its own arguments. A default exec of this file must
    # not accidentally parse a .blend path or host startup flags as our options.
    if 'bpy' in sys.modules and '--stage-obj' not in sys.argv:
        return build_costumes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-obj', action='store_true')
    parser.add_argument('--source')
    parser.add_argument('--output-dir')
    parser.add_argument('--height', type=float, default=1.8)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    if args.stage_obj:
        stage_obj(args.source, args.output_dir, args.height)
    else:
        raise RuntimeError('Run inside Blender for costumes, or use --stage-obj outside Blender')


if __name__ == '__main__':
    main()
