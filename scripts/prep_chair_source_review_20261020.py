import bpy,json,math,shutil,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
BASE=Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Cadeiras')
assert bpy.data.scenes.get('PREP_CHAIR_SOURCE_REVIEW_20261020') is None
scene=bpy.data.scenes.new('PREP_CHAIR_SOURCE_REVIEW_20261020')
for w in bpy.context.window_manager.windows:w.scene=scene
scene.unit_settings.system='METRIC'
col=bpy.data.collections.new('CHAIR20_SOURCE_REVIEW');scene.collection.children.link(col)
out=ROOT/'art/source/hospital_chairs_20261020';out.mkdir(parents=True,exist_ok=True)
records=[]
for index,(key,relative) in enumerate([
 ('Eames','Eames Lounge Chair 01/eames_lounge_chair.glb'),
 ('Driftwood','luxury Chair driftwood art 3d model/luxury_chair_driftwood_art_3d_model_.glb'),
 ('Chaise','intricately carved luxury chaise lounge/intricately_carved_luxury_chaise_lounge.glb')]):
    dest=out/(key+'_Original.glb');shutil.copy2(BASE/relative,dest)
    before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(dest))
    fresh=set(scene.objects)-before
    root=bpy.data.objects.new('CHAIR20_REVIEW_'+key,None);col.objects.link(root)
    for obj in fresh:
        if obj.parent not in fresh:obj.parent=root
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(v) for o in fresh if o.type=='MESH' for v in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    root.location=Vector((index*3,0,0))-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    records.append({'key':key,'source':str(dest),'boundsMin':list(lo),'boundsMax':list(hi),'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'size':list(o.dimensions),'location':list(o.location)} for o in fresh]})
mat=bpy.data.materials.new('CHAIR20_REVIEW_FLOOR');mat.diffuse_color=(.35,.4,.43,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(3,0,-.005));floor=bpy.context.object;floor.name='CHAIR20_REVIEW_FLOOR';floor.data.materials.append(mat)
world=bpy.data.worlds.new('CHAIR20_REVIEW_WORLD');world.use_nodes=True
nodes=world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');outnode=nodes.new('ShaderNodeOutputWorld')
bg.inputs['Color'].default_value=(.5,.6,.7,1);bg.inputs['Strength'].default_value=.6;world.node_tree.links.new(bg.outputs[0],outnode.inputs[0]);scene.world=world
for name,loc,energy,size in [('KEY',(1,-3,5),1400,6),('FILL',(5,3,4),900,5)]:
    data=bpy.data.lights.new('CHAIR20_'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);col.objects.link(obj);obj.location=loc;obj.rotation_euler=(Vector((3,0,.5))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('CHAIR20_REVIEW_CAMERA');cam=bpy.data.objects.new(data.name,data);col.objects.link(cam);cam.location=(9,-9,5);cam.rotation_euler=(Vector((3,0,.6))-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=48;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
path=ROOT/'reports/chair_source_review_20261020.png';scene.render.filepath=str(path)
(ROOT/'reports/CHAIR_SOURCE_REVIEW_20261020.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print(json.dumps({'scene':scene.name,'preview':str(path),'assets':len(records)}))
