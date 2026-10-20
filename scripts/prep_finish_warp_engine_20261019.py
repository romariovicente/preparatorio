import bpy,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
scene=bpy.data.scenes['PREP_WARP_ENGINE_20261019'];bpy.context.window.scene=scene
collection=bpy.data.collections['WARP19_Runtime'];meshes=[o for o in collection.all_objects if o.type=='MESH']
report_path=ROOT/'reports/WARP_ENGINE_BLENDER_20261019.json';report=json.loads(report_path.read_text('utf-8'))
out=ROOT/'frontend/public/assets/additions20261019/PROP_Motor_Dobra_20261019.glb'
bpy.ops.object.select_all(action='DESELECT')
for o in collection.all_objects:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,
    export_extras=True,export_animations=False,export_image_format='JPEG',export_jpeg_quality=90)
data=out.read_bytes();doc=json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]])
tri=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
assert len(doc['scenes'])==1 and len(doc['meshes'])==1 and tri==170000 and len(data)<20_000_000
report.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),singleSceneExport=True)
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
world=scene.world or bpy.data.worlds.new('WARP19_World');scene.world=world;world.use_nodes=True
nodes=world.node_tree.nodes;bg=next((n for n in nodes if n.type=='BACKGROUND'),None) or nodes.new('ShaderNodeBackground')
output=next((n for n in nodes if n.type=='OUTPUT_WORLD'),None) or nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(bg.outputs[0],output.inputs['Surface'])
bg.inputs['Color'].default_value=(.12,.16,.22,1);bg.inputs['Strength'].default_value=.45
if not scene.camera:
    data=bpy.data.cameras.new('WARP19_Camera');camera=bpy.data.objects.new('WARP19_Camera',data);scene.collection.objects.link(camera)
    camera.location=(6,-7,4.5);camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=45;scene.camera=camera
for name,position,power,size in [('Key',(3,-4,7),1400,5),('Rim',(-3,3,5),1800,4)]:
    if bpy.data.objects.get('WARP19_'+name):continue
    data=bpy.data.lights.new('WARP19_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('WARP19_'+name,data);scene.collection.objects.link(light);light.location=position
    light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
library=ROOT/'art/blender/PREPARATORIO_WARP_ENGINE_20261019.blend';bpy.data.libraries.write(str(library),{scene},compress=True)
scene.render.filepath=str(ROOT/'reports/warp_engine_preview_20261019.png');bpy.ops.render.render(write_still=True)
report.update(library=str(library),libraryBytes=library.stat().st_size,render=scene.render.filepath)
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
print(json.dumps(report,ensure_ascii=False))
