"""Read-only live Blender audit before the 2026-10-13 master resume.

Run through work/blender_rpc.py; this does not modify Blender datablocks.
"""
import bpy
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from mathutils import Vector

PROJECT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
REPORT = PROJECT / ('reports/blender_master_recovered_audit_20261013.json' if bpy.data.filepath else 'reports/blender_master_resume_audit_20261013.json')
scene = bpy.context.scene

def rounded(values):
    return [round(float(v), 6) for v in values]

def object_row(obj):
    return {
        'name': obj.name, 'type': obj.type,
        'parent': obj.parent.name if obj.parent else None,
        'collections': [c.name for c in obj.users_collection],
        'location': rounded(obj.location), 'rotation_euler': rounded(obj.rotation_euler),
        'scale': rounded(obj.scale), 'dimensions': rounded(obj.dimensions),
        'hide_viewport': obj.hide_viewport, 'hide_render': obj.hide_render,
        'hidden_in_active_view_layer': obj.hide_get() if obj.name in bpy.context.view_layer.objects else None,
        'modifiers': [{'name': m.name, 'type': m.type, 'object': getattr(getattr(m, 'object', None), 'name', None)} for m in obj.modifiers],
    }

def aggregate_bounds(objects):
    mesh_objects = [o for o in objects if o.type == 'MESH']
    points = [o.matrix_world @ Vector(v) for o in mesh_objects for v in o.bound_box]
    if not points:
        return {'mesh_count': 0}
    lo = [min(v[i] for v in points) for i in range(3)]
    hi = [max(v[i] for v in points) for i in range(3)]
    return {'mesh_count': len(mesh_objects), 'minimum': rounded(lo), 'maximum': rounded(hi), 'dimensions': rounded([hi[i] - lo[i] for i in range(3)])}

objects = list(scene.objects)
object_ids = {o.as_pointer() for o in objects}
root_members = {}
for obj in objects:
    root = obj
    while root.parent and root.parent.as_pointer() in object_ids:
        root = root.parent
    root_members.setdefault(root, []).append(obj)
roots = []
for root, members in sorted(root_members.items(), key=lambda item: item[0].name.lower()):
    row = object_row(root)
    row['descendant_count_in_scene'] = len(members) - 1
    row['aggregate_bounds'] = aggregate_bounds(members)
    roots.append(row)

armatures = []
for obj in objects:
    if obj.type != 'ARMATURE':
        continue
    row = object_row(obj)
    row.update({'bone_count': len(obj.data.bones), 'bone_names': [b.name for b in obj.data.bones],
        'pose_position': obj.data.pose_position, 'rigged_meshes': [o.name for o in objects if any(m.type == 'ARMATURE' and m.object == obj for m in o.modifiers)],
        'constraints': [{'bone': p.name, 'name': c.name, 'type': c.type, 'target': getattr(getattr(c, 'target', None), 'name', None)} for p in obj.pose.bones for c in p.constraints]})
    anim = obj.animation_data
    row['active_action'] = anim.action.name if anim and anim.action else None
    row['nla_tracks'] = [{'name': t.name, 'mute': t.mute, 'strips': [{'name': s.name, 'action': s.action.name if s.action else None, 'start': s.frame_start, 'end': s.frame_end} for s in t.strips]} for t in anim.nla_tracks] if anim else []
    armatures.append(row)

garment_pattern = re.compile(r'jaleco|uniform|coat|clothing|garment|costume|scrub|jacket|lab_coat|medic|doctor', re.I)
garments = [object_row(o) | {'vertices': len(o.data.vertices), 'polygons': len(o.data.polygons), 'vertex_groups': [g.name for g in o.vertex_groups], 'materials': [m.name if m else None for m in o.data.materials]} for o in objects if o.type == 'MESH' and garment_pattern.search(o.name)]

images = []
for im in bpy.data.images:
    absolute = bpy.path.abspath(im.filepath, library=im.library) if im.filepath else ''
    packed = bool(im.packed_file) or bool(getattr(im, 'packed_files', []))
    missing = im.source in {'FILE', 'MOVIE', 'SEQUENCE'} and bool(im.filepath) and not packed and not Path(absolute).is_file()
    images.append({'name': im.name, 'source': im.source, 'filepath': im.filepath, 'resolved_path': absolute,
        'packed': packed, 'missing': missing, 'size': list(im.size), 'users': im.users})

materials = []
shader_counts = Counter()
for mat in bpy.data.materials:
    nodes = list(mat.node_tree.nodes) if mat.use_nodes and mat.node_tree else []
    shaders = [n.bl_idname for n in nodes if n.type.startswith('BSDF') or n.type in {'EMISSION', 'MIX_SHADER', 'ADD_SHADER'}]
    shader_counts.update(shaders)
    materials.append({'name': mat.name, 'users': mat.users, 'use_nodes': mat.use_nodes,
        'shader_nodes': shaders, 'image_nodes': [{'node': n.name, 'image': n.image.name if n.image else None} for n in nodes if n.type == 'TEX_IMAGE']})

report = {
    'audit_time_local': datetime.now().isoformat(timespec='seconds'),
    'read_only_scene_audit': True, 'blender_version': bpy.app.version_string,
    'filepath': bpy.data.filepath, 'is_dirty': bpy.data.is_dirty, 'scene': scene.name,
    'all_scene_names': [s.name for s in bpy.data.scenes],
    'mode': bpy.context.mode, 'active_object': object_row(bpy.context.active_object) if bpy.context.active_object else None,
    'selected_objects': [o.name for o in bpy.context.selected_objects],
    'counts': {'scene_objects': len(objects), 'all_objects': len(bpy.data.objects), 'meshes': len(bpy.data.meshes),
        'materials': len(bpy.data.materials), 'images': len(bpy.data.images), 'actions': len(bpy.data.actions),
        'armatures_in_scene': len(armatures), 'root_objects': len(roots), 'object_types': dict(Counter(o.type for o in objects))},
    'units': {'system': scene.unit_settings.system, 'scale_length': scene.unit_settings.scale_length, 'length_unit': scene.unit_settings.length_unit},
    'frame': {'current': scene.frame_current, 'start': scene.frame_start, 'end': scene.frame_end, 'fps': scene.render.fps},
    'root_collections': [{'name': c.name, 'objects': len(c.all_objects), 'hide_viewport': c.hide_viewport, 'hide_render': c.hide_render} for c in scene.collection.children],
    'root_objects': roots, 'armatures': armatures, 'garment_meshes': garments,
    'actions': [{'name': a.name, 'users': a.users, 'frame_range': rounded(a.frame_range), 'fake_user': a.use_fake_user} for a in bpy.data.actions],
    'shader_node_counts': dict(shader_counts), 'materials': materials, 'images': images,
    'missing_images': [im for im in images if im['missing']],
    'libraries': [{'filepath': lib.filepath, 'resolved_path': bpy.path.abspath(lib.filepath), 'missing': not Path(bpy.path.abspath(lib.filepath)).is_file()} for lib in bpy.data.libraries],
    'scene_aggregate_bounds': aggregate_bounds(objects),
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'report': str(REPORT), 'filepath': report['filepath'], 'is_dirty': report['is_dirty'],
    'scene': report['scene'], 'counts': report['counts'], 'root_collections': report['root_collections'],
    'active_object': report['active_object'], 'garment_mesh_names': [g['name'] for g in garments],
    'armature_names': [a['name'] for a in armatures], 'missing_image_count': len(report['missing_images']),
    'scene_aggregate_bounds': report['scene_aggregate_bounds']}, ensure_ascii=True))
