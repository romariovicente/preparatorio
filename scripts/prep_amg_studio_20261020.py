import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert not bpy.data.scenes.get('PREP_AMG_ONE_STUDIO_20261020'),'Inspect the existing studio instead of duplicating it'
source=bpy.data.collections['AMGO19_Interactive']
scene=bpy.data.scenes.new('PREP_AMG_ONE_STUDIO_20261020');bpy.context.window.scene=scene
scene.collection.children.link(source);scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['author']='Romario Vicente Amaro';scene['assetScene']='PREP_AMG_ONE_20261019'
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('AMGST20_World');world.use_nodes=True;scene.world=world
nodes=world.node_tree.nodes;bg=next((n for n in nodes if n.type=='BACKGROUND'),None) or nodes.new('ShaderNodeBackground')
output=next((n for n in nodes if n.type=='OUTPUT_WORLD'),None) or nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs[0],output.inputs['Surface']);bg.inputs['Color'].default_value=(.13,.17,.22,1);bg.inputs['Strength'].default_value=.4
data=bpy.data.cameras.new('AMGST20_Camera');camera=bpy.data.objects.new('AMGST20_Camera',data);scene.collection.objects.link(camera)
camera.location=(6,-8,3.8);camera.rotation_euler=(Vector((0,0,.65))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=48;scene.camera=camera
for name,location,power,size in [('Key',(2,-4,6),1500,5),('Rim',(-3,3,4),1800,4),('Fill',(-4,-3,3),700,4)]:
    data=bpy.data.lights.new('AMGST20_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('AMGST20_'+name,data);scene.collection.objects.link(light);light.location=location
    light.rotation_euler=(Vector((0,0,.6))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.015));floor=bpy.context.object;floor.name='AMGST20_Floor'
mat=bpy.data.materials.new('AMGST20_Concrete');mat.diffuse_color=(.16,.20,.24,1);floor.data.materials.append(mat)
scene.render.filepath=str(ROOT/'reports/amg_one_preview_20261020.png')
library=ROOT/'art/blender/PREPARATORIO_AMG_ONE_20261020.blend'
bpy.data.libraries.write(str(library),{scene},compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
bpy.ops.render.render(write_still=True)
report={'scene':scene.name,'assetScene':scene['assetScene'],'author':scene['author'],'library':str(library),
 'libraryBytes':library.stat().st_size,'sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'preview':scene.render.filepath,
 'originalInteractiveGroupsPreserved':True,'master':str(MASTER),'masterBytes':MASTER.stat().st_size}
(ROOT/'reports/AMG_ONE_SAVED_QA_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
