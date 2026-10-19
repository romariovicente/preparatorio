"""Prepare independent copies and orthographic views for fitting humanoid rigs."""
import bpy,json,datetime
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'reports/rig_views';out.mkdir(parents=True,exist_ok=True)
checkpoint=ROOT/'art/blender/checkpoints'/('SESSION_BEFORE_RIG_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),compress=True)
records=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
for r in records:
    if r['category']!='Personagens':continue
    name='RIG_'+r['id'][4:]
    if name in bpy.data.scenes:continue
    scene=bpy.data.scenes.new(name);bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/r['url'].lstrip('/')))
    obj=next(o for o in scene.objects if o.type=='MESH');matrix=obj.matrix_world.copy()
    obj.parent=None;obj.matrix_world=matrix
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    lo=Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)])
    hi=Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)])
    center=(lo+hi)/2;center.z=lo.z;scale=1.7/(hi.z-lo.z)
    for vertex in obj.data.vertices:vertex.co=(vertex.co-center)*scale
    obj.data.update();obj.name=name+'_Body';obj['source_id']=r['id']
    scene.world=bpy.data.worlds.new(name+'_World');scene.world.color=(.45,.45,.45)
    scene.render.engine='CYCLES';scene.cycles.samples=4;scene.render.resolution_x=400;scene.render.resolution_y=400;scene.render.resolution_percentage=100
    bpy.ops.object.light_add(type='AREA',location=(0,-3,4));light=bpy.context.object;light.data.energy=350;light.data.size=5
    light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.2;scene.camera=cam
    for view,location in [('front',(0,-5,.85)),('side',(5,0,.85))]:
        cam.location=location;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/(name+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
    scene['source_id']=r['id']
    print('Prepared',name)
path=ROOT/'art/blender/PREPARATORIO_RIG_WORK.blend';assert not path.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
