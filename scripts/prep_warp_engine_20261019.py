"""Import and prepare the supplied conceptual engine in the live Blender MCP session."""
import bpy, hashlib, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
SOURCE=Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Naves\Motor de Dobra Espacial\meshy-model.glb')
SHA='a63a5673ec54197b54849506a2b1cd41eb284c27ba077b485944d38d986e73be'
OUT=ROOT/'frontend/public/assets/additions20261019/PROP_Motor_Dobra_20261019.glb'
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
assert not bpy.data.scenes.get('PREP_WARP_ENGINE_20261019'), 'Inspect the existing new scene before repeating this increment'
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
prior=object_state(list(bpy.data.objects))
scene=bpy.data.scenes.new('PREP_WARP_ENGINE_20261019');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['author']='Romario Vicente Amaro';scene['concept']='Motor de dobra espacial · objeto de ficção científica'
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
imported=[o for o in bpy.data.objects if o not in before]
meshes=[o for o in imported if o.type=='MESH']
assert meshes and not any(o.type=='ARMATURE' for o in imported)
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
lo=Vector(tuple(min(v[i] for v in points) for i in range(3)))
hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
dims=hi-lo
scale=min(2.2/dims.z,4/max(dims.x,dims.y))
norm=Matrix.Diagonal((scale,scale,scale,1))@Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z)))
source_collection=bpy.data.collections.new('WARP19_Original_Preserved');scene.collection.children.link(source_collection)
runtime_collection=bpy.data.collections.new('WARP19_Runtime');scene.collection.children.link(runtime_collection)
root=bpy.data.objects.new('WARP19_Motor_Dobra',None);runtime_collection.objects.link(root)
root['source_sha256']=SHA;root['purpose']='Conceitual · sem simulação de propulsão real'
source_tri=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
ratio=min(1,170000/max(1,source_tri))
image_map={};material_map={};runtime=[];texture_sizes=[]
for original in meshes:
    copy=original.copy();copy.data=original.data.copy();copy.parent=root
    runtime_collection.objects.link(copy);copy.matrix_world=norm@original.matrix_world
    copy.name='WARP19_LOD_'+original.name
    for slot in copy.material_slots:
        mat=slot.material
        if not mat:continue
        if mat not in material_map:
            new=mat.copy();new.name='WARP19_'+mat.name;material_map[mat]=new
            if new.use_nodes:
                for node in new.node_tree.nodes:
                    if node.type!='TEX_IMAGE' or not node.image:continue
                    src=node.image
                    if src not in image_map:
                        img=src.copy();img.name='WARP19_LOD_'+src.name
                        w,h=img.size[:];factor=min(1,2048/max(w,h))
                        if factor<1:img.scale(max(1,round(w*factor)),max(1,round(h*factor)))
                        img.pack();image_map[src]=img
                        texture_sizes.append({'source':[w,h],'runtime':list(img.size)})
                    node.image=image_map[src]
        slot.material=material_map[mat]
    if ratio<1:
        mod=copy.modifiers.new('Runtime reduction; high detail original retained','DECIMATE');mod.ratio=ratio
        bpy.context.view_layer.objects.active=copy
        bpy.ops.object.modifier_apply(modifier=mod.name)
    runtime.append(copy)
for o in imported:
    for c in list(o.users_collection):c.objects.unlink(o)
    source_collection.objects.link(o);o['source_sha256']=SHA
source_collection.hide_render=True;source_collection.hide_viewport=True
bpy.context.view_layer.update()
final_points=[o.matrix_world@Vector(v) for o in runtime for v in o.bound_box]
final_lo=Vector(tuple(min(v[i] for v in final_points) for i in range(3)))
final_hi=Vector(tuple(max(v[i] for v in final_points) for i in range(3)))
assert abs(final_lo.z)<.02 and max((final_hi-final_lo).x,(final_hi-final_lo).y)<=4.01
originals=[o for o in bpy.data.objects if o.name in prior]
assert state_hash(object_state(originals))==state_hash(prior), 'An existing object changed'
OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in runtime_collection.all_objects:o.select_set(True)
bpy.context.view_layer.objects.active=runtime[0]
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,
    export_extras=True,export_animations=False,export_image_format='JPEG',export_jpeg_quality=90)
tri=sum(len(p.vertices)-2 for o in runtime for p in o.data.polygons)
assert tri<=185000 and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
report={'scene':scene.name,'source':str(SOURCE),'sourceSha256':SHA,'originalPreserved':True,
 'sourceTriangles':source_tri,'runtimeTriangles':tri,'runtimeMeshes':len(runtime),'textures':texture_sizes,
 'url':'/assets/additions20261019/'+OUT.name,'bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
 'dimensionsBlender':list(final_hi-final_lo),'scale':scale,'groundMin':final_lo.z,
 'positionThree':[76,.15,-43],'pedestal':[4.6,.12,4.6],'existingObjectsPreserved':len(prior),'validatedInBrowser':False}
(ROOT/'reports/WARP_ENGINE_BLENDER_20261019.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('WARP19_World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.16,.22,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
camera_data=bpy.data.cameras.new('WARP19_Camera');camera=bpy.data.objects.new('WARP19_Camera',camera_data);scene.collection.objects.link(camera)
camera.location=(6,-7,4.5);camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=45;scene.camera=camera
for name,position,power,size in [('Key',(3,-4,7),1400,5),('Rim',(-3,3,5),1800,4)]:
    data=bpy.data.lights.new('WARP19_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('WARP19_'+name,data);scene.collection.objects.link(light);light.location=position
    light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
scene.render.filepath=str(ROOT/'reports/warp_engine_preview_20261019.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
print(json.dumps(report,ensure_ascii=False))
