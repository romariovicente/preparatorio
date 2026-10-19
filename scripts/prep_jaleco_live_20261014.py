"""Add two independent fitted characters to a dedicated live Blender scene."""
import bpy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from mathutils import Vector

ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
target=ROOT/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
asset=ROOT/'frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb'
expected='2cff412ae103b9b7d996d264bd4908cf80bd4e4dc93447afb53bc671c9542bfc'
if Path(bpy.data.filepath)!=target:
    raise RuntimeError('Unexpected live master: '+bpy.data.filepath)
if hashlib.sha256(asset.read_bytes()).hexdigest()!=expected:
    raise RuntimeError('Uniform asset hash changed')
scene_name='PREP_JALECO_QA_20261014'
if scene_name in bpy.data.scenes:
    raise RuntimeError('Jaleco scene already exists; inspect instead of duplicating')
legacy=bpy.context.scene
legacy_count=len(legacy.objects)
stamp=datetime.now().strftime('%H%M%S_%f')
checkpoint=ROOT/f'art/blender/checkpoints/BEFORE_JALECO_20261014_{stamp}.blend'
if 'FINISHED' not in bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True):
    raise RuntimeError('Checkpoint failed')
scene=bpy.data.scenes.new(scene_name)
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene['purpose']='Independent clothing QA; demonstration names only. Runtime uses each player profile.'
scene['author']='Romario Vicente Amaro'
def collection(name,parent):
    result=bpy.data.collections.new(name)
    parent.children.link(result)
    return result
world=collection('PREP_CITY_JALECO_20261014',scene.collection)
characters=collection('CHARACTERS_JALECO_20261014',world)
clothing=collection('CLOTHING_JALECO_20261014',world)
staging=collection('STAGING_JALECO_20261014',world)
def move_to(obj,destination):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    destination.objects.link(obj)
def material(name,color,metallic=0,roughness=.7):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metallic
    bsdf.inputs['Roughness'].default_value=roughness
    return mat
actors=[]
for key,name,x,color in [('romario','Romario Vicente Amaro',-.9,(.025,.20,.44)),('ana','Ana Clara',.9,(.04,.25,.13))]:
    actor_collection=collection('CHAR_'+key.upper()+'_DEMO_20261014',characters)
    before=set(bpy.data.objects)
    imported_result=bpy.ops.import_scene.gltf(filepath=str(asset))
    if 'FINISHED' not in imported_result:
        raise RuntimeError('Uniform import failed')
    imported=list(set(bpy.data.objects)-before)
    root=bpy.data.objects.new('CHAR_'+key.upper()+'_DEMO_ROOT',None)
    actor_collection.objects.link(root)
    root['display_name_demo']=name
    root['runtime_name_source']='individual player profile, not this demonstration label'
    root['source_sha256']=expected
    for obj in imported:
        original_name=obj.name.rsplit('.',1)[0] if obj.name.rsplit('.',1)[-1].isdigit() else obj.name
        obj['asset_node_name']=original_name
        move_to(obj,actor_collection)
        if obj.parent not in imported:
            matrix=obj.matrix_world.copy()
            obj.parent=root
            obj.matrix_world=matrix
        if obj.type=='ARMATURE' and obj.animation_data:
            obj.animation_data.action=None
            for track in obj.animation_data.nla_tracks:
                track.mute='Idle' not in track.name
        if obj.type=='MESH':
            obj.hide_render=False
            obj.hide_set(False)
            if original_name.startswith(('Tops','Bottoms')):
                obj.hide_render=True
                obj.hide_set(True)
            if original_name.startswith('SCRUB_') and 'Trouser' not in original_name:
                obj.hide_render=True
                obj.hide_set(True)
            if original_name.startswith(('COAT_','SCRUB_')):
                clothing.objects.link(obj)
                for slot in obj.material_slots:
                    if slot.material:
                        slot.material=slot.material.copy()
                        slot.material.name=f'{key}_{slot.material.name}'
                        if original_name.startswith('SCRUB_') and not original_name.startswith(('SCRUB_NAME_','SCRUB_BRAND_')):
                            slot.material.diffuse_color=(*color,1)
                            node=next((n for n in slot.material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
                            if node:
                                node.inputs['Base Color'].default_value=(*color,1)
            if original_name.startswith(('COAT_NAME_','SCRUB_NAME_')):
                image=bpy.data.images.load(str(ROOT/f'art/generated/uniform_names_20261014/demo_{key}.png'),check_existing=True)
                image.pack()
                for slot in obj.material_slots:
                    mat=slot.material
                    tree=mat.node_tree
                    for node in list(tree.nodes):
                        if node.type=='TEX_IMAGE':
                            tree.nodes.remove(node)
                    tex=tree.nodes.new('ShaderNodeTexImage')
                    tex.image=image
                    bsdf=next((n for n in tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
                    tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
                    tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
                    mat.diffuse_color=(1,1,1,1)
                    mat.surface_render_method='DITHERED'
        obj.name=f'{key.upper()}_{original_name}'
    scene.frame_set(1)
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    visible_meshes=[o for o in imported if o.type=='MESH' and not o.hide_render]
    points=[o.evaluated_get(depsgraph).matrix_world@Vector(v) for o in visible_meshes for v in o.evaluated_get(depsgraph).bound_box]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    scale=1.7/(high.z-low.z)
    root.scale=(scale,scale,scale)
    root.location=(x-(low.x+high.x)*scale/2,-(low.y+high.y)*scale/2,-low.z*scale)
    arms=[o for o in imported if o.type=='ARMATURE']
    if len(arms)!=1 or len(arms[0].data.bones)!=55:
        raise RuntimeError('Expected one preserved 55-bone rig per actor')
    actors.append({'demo_name':name,'root':root.name,'objects':len(imported),'bones':len(arms[0].data.bones),'scale':scale,'height_m':1.7,
                   'name_meshes':[o.name for o in imported if o['asset_node_name'].startswith(('COAT_NAME_','SCRUB_NAME_'))]})

floor=material('MAT_JALECO_STAGE_20261014',(.075,.10,.13),roughness=.82)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.09))
ground=bpy.context.object
ground.name='QA_FLOOR_20261014'
ground.dimensions=(6,5,.18)
ground.data.materials.append(floor)
move_to(ground,staging)
label_mat=material('MAT_JALECO_LABEL_20261014',(.78,.87,.94))
def label(body,loc,size=.13):
    curve=bpy.data.curves.new('QA_LABEL_DATA','FONT')
    curve.body=body
    curve.align_x='CENTER'
    curve.size=size
    curve.extrude=.0003
    obj=bpy.data.objects.new('QA_LABEL_'+body,curve)
    staging.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(1.57079632679,0,0)
    curve.materials.append(label_mat)
    return obj
label('PREPARATÓRIO | JALECOS INDIVIDUAIS',(0,.30,2.04),.15)
label('Nomes demonstrativos. No jogo, cada usuário usa o próprio nome.',(0,.30,1.89),.065)
for actor,x in zip(actors,[-.9,.9]):
    label(actor['demo_name'],(x,-.3,-.01),.085)
    label('55 ossos | 1,70 m',(x,-.3,-.10),.065)
scene.world=bpy.data.worlds.new('WORLD_JALECO_QA_20261014')
scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.12,.15,.20,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.45
for index,location,power,size in [(1,(2,-3,4),550,4),(2,(-3,-2,3),350,3),(3,(0,2,3.5),400,3)]:
    data=bpy.data.lights.new(f'QA_AREA_{index}','AREA')
    data.energy=power
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(data.name,data)
    staging.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('CAM_JALECO_QA_20261014')
camera=bpy.data.objects.new(camera_data.name,camera_data)
staging.objects.link(camera)
camera.location=(0,-6,1.35)
camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'
camera_data.ortho_scale=3.7
scene.camera=camera
scene.render.engine='CYCLES'
scene.cycles.samples=12
scene.render.resolution_x=1400
scene.render.resolution_y=1050
scene.render.resolution_percentage=100
scene.render.filepath=str(ROOT/'reports/costumes/jalecos_individuais_blender_20261014.png')
scene.view_settings.view_transform='AgX'
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.overlay.show_overlays=False
            area.spaces.active.region_3d.view_perspective='CAMERA'
if len(legacy.objects)!=legacy_count:
    raise RuntimeError('Legacy scene changed during additive import')
if 'FINISHED' not in bpy.ops.wm.save_as_mainfile(filepath=str(target)):
    raise RuntimeError('Clothing master save failed')
bpy.ops.render.render(write_still=True)
report={'time_local':datetime.now().isoformat(timespec='seconds'),'scene':scene.name,'objects':len(scene.objects),
        'legacy_scene':legacy.name,'legacy_objects_preserved':legacy_count,'actors':actors,
        'source_sha256':expected,'master':str(target),'checkpoint':str(checkpoint),
        'preview':scene.render.filepath,'name_images_packed':True,'metric':scene.unit_settings.system,'scale_length':scene.unit_settings.scale_length}
(ROOT/'reports/blender_jaleco_live_20261014.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report))
