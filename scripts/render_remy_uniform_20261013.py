"""Render the independently reimported uniform in its important real poses."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb'
OUT=ROOT/'reports/costumes'

def render(mode):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET))
 scene=bpy.context.scene;arm=next(o for o in scene.objects if o.type=='ARMATURE')
 for o in scene.objects:
  if o.name.startswith(('Tops','Bottoms')):o.hide_render=True
  if o.name.startswith('COAT_'):o.hide_render=mode=='scrubs'
  if o.name.startswith('SCRUB_'):o.hide_render=mode!='scrubs' and 'Trouser' not in o.name
 if arm.animation_data:
  arm.animation_data.action=None
  for t in arm.animation_data.nla_tracks:t.mute=('Walk' if mode=='walk' else 'Idle') not in t.name
 scene.frame_set(13 if mode=='walk' else 1)
 bpy.context.view_layer.update()
 if mode in ('seated','riding'):
  # Match the frontend FK pose, without altering the saved asset or clips.
  arm.animation_data_clear()
  bpy.context.view_layer.update()
  def point(part,child,direction):
   bone=arm.pose.bones['mixamorig:'+part];tip=arm.pose.bones['mixamorig:'+child]
   current=arm.matrix_world@bone.matrix;to=(arm.matrix_world@tip.matrix).translation-current.translation
   delta=to.normalized().rotation_difference(Vector(direction).normalized())
   target=delta.to_matrix().to_4x4()@current;target.translation=current.translation
   bone.matrix=arm.matrix_world.inverted()@target;bpy.context.view_layer.update()
  riding=mode=='riding'
  for side in ['Left','Right']:
   point(side+'UpLeg',side+'Leg',((.24 if side=='Left' else -.24) if riding else 0,-1,-.12 if riding else 0))
   point(side+'Leg',side+'Foot',(0,0,-1))
  if riding:point('Spine','Spine1',(0,-.53,.85))
  for side in ['Left','Right']:
   point(side+'Arm',side+'ForeArm',(.12 if side=='Left' else -.12,-.94 if riding else -.7,-.35 if riding else -.7))
   point(side+'ForeArm',side+'Hand',(0,-1,-.14))
 scene.world=bpy.data.worlds.new('UniformWorld');scene.world.color=(.18,.18,.18)
 for loc,power in [((2,-3,3),450),((-2,-2,2.5),250)]:
  bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.size=4
 focus=Vector((0,-.15,.9))
 bpy.ops.object.camera_add(location=(1.7,-4,1.65));cam=bpy.context.object
 cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.15;scene.camera=cam
 scene.render.engine='CYCLES';scene.cycles.samples=10
 scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
 scene.render.filepath=str(OUT/('remy_uniform_'+mode+'_20261013.png'))
 bpy.ops.render.render(write_still=True)
 print('UNIFORM_PREVIEW '+json.dumps({'pose':mode,'file':scene.render.filepath}))

for mode in ['scrubs','walk','seated','riding']:render(mode)
