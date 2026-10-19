import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
record={'objects':[],'bones':[],'images':[]}
for obj in bpy.data.objects:
 if obj.type=='MESH':
  p=[obj.matrix_world@v.co for v in obj.data.vertices]
  record['objects'].append({'name':obj.name,'vertices':len(p),'min':[min(v[a] for v in p) for a in range(3)],'max':[max(v[a] for v in p) for a in range(3)],'materials':[m.name for m in obj.data.materials],'weights':[{ 'name':g.name,'count':sum(1 for v in obj.data.vertices if any(i.group==g.index and i.weight>.001 for i in v.groups))} for g in obj.vertex_groups]})
for bone in arm.data.bones:
 record['bones'].append({'name':bone.name,'head':list(arm.matrix_world@bone.head_local),'tail':list(arm.matrix_world@bone.tail_local)})
for im in bpy.data.images:
 record['images'].append({'name':im.name,'size':list(im.size),'channels':im.channels})
print(json.dumps(record))
(ROOT/'reports/remy_uniform_source_inspection_20261009.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
if arm.animation_data:
 for track in arm.animation_data.nla_tracks: track.mute='Idle' not in track.name
bpy.context.scene.frame_set(1)
scene=bpy.context.scene
scene.world=bpy.data.worlds.new('UniformInspectWorld');scene.world.color=(.18,.18,.18)
for loc,power in [((2,-3,3),450),((-2,-2,2.5),250)]:
 bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.size=4
bpy.ops.object.camera_add(location=(2,-4,1.7))
cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.2;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.resolution_x=700;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.filepath=str(ROOT/'reports/remy_uniform_source_20261009.png')
bpy.ops.render.render(write_still=True)
