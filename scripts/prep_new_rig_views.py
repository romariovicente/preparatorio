"""Prepare only newly supplied unskinned humanoids for visual bone fitting."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
items=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'reports/supplied').glob('*.json')]
for r in items:
 if r.get('status')!='validated' or r['category']!='Personagens' or r['animated'] or (ROOT/'reports/rigs'/(r['id'][4:]+'.json')).exists():continue
 name='RIG_'+r['id'][4:]
 if name in bpy.data.scenes:continue
 scene=bpy.data.scenes.new(name);bpy.context.window.scene=scene
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/r['url'].lstrip('/')));bpy.context.view_layer.update()
 obj=next(o for o in scene.objects if o.type=='MESH');world=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=world
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 lo=Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)]);center=(lo+hi)/2;center.z=lo.z
 for v in obj.data.vertices:v.co=(v.co-center)*(1.7/(hi.z-lo.z))
 obj.data.update();scene['source_id']=r['id'];scene.world=bpy.data.worlds.new(name+'_World');scene.world.color=(.4,.4,.4)
 scene.render.engine='CYCLES';scene.cycles.samples=4;scene.render.resolution_x=400;scene.render.resolution_y=400;scene.render.resolution_percentage=100
 bpy.ops.object.light_add(type='AREA',location=(0,-3,4));bpy.context.object.data.energy=400;bpy.context.object.data.size=5
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.3;scene.camera=cam
 for view,loc in [('front',(0,-5,.85)),('side',(5,0,.85))]:
  cam.location=loc;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'reports/rig_views'/(name+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('New humanoid views prepared')
