import bpy,json,shutil,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE=Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Hospital\Thermometer\thermometer.glb')
assert 'PREP_THERMOMETER_REVIEW_20261020' not in bpy.data.scenes
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='648242dea0d5cc07a956be28fd5d0b87b6e50a07d13d1cc29524a49f80e5dbdd'
copy=ROOT/'art/source/hospital_equipment_20261020/Thermometer_Original.glb';copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE,copy)
scene=bpy.data.scenes.new('PREP_THERMOMETER_REVIEW_20261020');scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
for w in bpy.context.window_manager.windows:w.scene=scene
bpy.ops.import_scene.gltf(filepath=str(copy));fresh=list(scene.objects)
col=bpy.data.collections.new('THM20_SOURCE');scene.collection.children.link(col)
root=bpy.data.objects.new('THM20_ROOT',None);col.objects.link(root)
for obj in fresh:
    if not obj.parent:obj.parent=root
    col.objects.link(obj)
    for old in list(obj.users_collection):
        if old!=col:old.objects.unlink(obj)
bpy.context.view_layer.update();points=[o.matrix_world@Vector(v) for o in fresh if o.type=='MESH' for v in o.bound_box]
lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
root.location-=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z))
studio=bpy.data.collections.new('THM20_STUDIO');scene.collection.children.link(studio)
data=bpy.data.cameras.new('THM20_CAMERA');cam=bpy.data.objects.new(data.name,data);studio.objects.link(cam);cam.location=(.29,-.32,.25);target=Vector((0,0,(hi.z-lo.z)/2));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=58;data.clip_start=.001;data.clip_end=10;scene.camera=cam
for name,pos,energy,size in [('KEY',(.2,-.3,.4),15,.5),('FILL',(-.3,.1,.3),10,.4)]:
    data=bpy.data.lights.new('THM20_'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);studio.objects.link(obj);obj.location=pos;obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('THM20_WORLD');world.use_nodes=True;nodes=world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');bg.inputs['Color'].default_value=(.3,.4,.5,1);bg.inputs['Strength'].default_value=.4;out=nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs[0]);scene.world=world
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
path=ROOT/'reports/thermometer_source_review_20261020.png';scene.render.filepath=str(path)
record={'source':str(copy),'dimensionsBlender':list(hi-lo),'scene':scene.name,'objects':[{'name':o.name,'type':o.type,'size':list(o.dimensions)} for o in fresh],'preview':str(path),'sourceSHA256':hashlib.sha256(copy.read_bytes()).hexdigest(),'clinicalMeasurementImplemented':False}
(ROOT/'reports/THERMOMETER_REVIEW_20261020.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print(json.dumps(record))
