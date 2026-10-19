"""Assemble the same training courtyard for Blender and the playable frontend."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
assets={a['id']:a for a in json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))}
rigs=json.loads((ROOT/'frontend/src/config/riggedAssets.json').read_text(encoding='utf-8'))
assert len(rigs)==11
assert 'PREP_GAMEPLAY' not in bpy.data.scenes
with bpy.data.libraries.load(str(ROOT/'art/blender/PREPARATORIO_ISLAND.blend'),link=False) as (available,target):
    target.scenes=[n for n in ['PREP_ISLAND','PREP_CITY'] if n in available.scenes and n not in bpy.data.scenes]
scene=bpy.data.scenes.new('PREP_GAMEPLAY');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['controls']='Timeline plays a preview. Browser: WASD/arrows; open Biblioteca for the book/Drive.'
scene['rig_review']='Seven locomotion prototypes; four fitted rigs retain seated/bent source poses pending retopology.'
environment=bpy.data.collections.new('PREP_CAMPUS_ENVIRONMENT');scene.collection.children.link(environment)
characters=bpy.data.collections.new('PREP_PLAYABLE_CHARACTERS');scene.collection.children.link(characters)
study=bpy.data.collections.new('PREP_STUDY_CHARACTERS');scene.collection.children.link(study)
def move(obj,col=environment):
    for old in list(obj.users_collection):old.objects.unlink(obj)
    col.objects.link(obj)
def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
    node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.75
    return mat
floor=material('MAT_Campus_Concrete',(.42,.54,.54));green=material('MAT_Campus_Grass',(.13,.29,.16));wood=material('MAT_Campus_Desk',(.15,.29,.33));white=material('MAT_Campus_White',(.85,.89,.84))
def box(name,location,size,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.name=name;obj.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);obj.data.materials.append(mat);move(obj);return obj
box('MOD_Campus_Ground',(0,0,-.15),(32,32,.3),floor)
for x in [-13,13]:box('MOD_Campus_Garden',(x,0,.02),(4,29,.12),green)
box('PROP_Learning_Desk',(0,4.5,.55),(3.4,1.6,1.1),wood)
for x in [-7,7]:box('PROP_Anatomy_Pedestal',(x,4,.5),(1.4,1.4,1),white)
def imported(id,location,extent=None,height=None):
    before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/assets[id]['url'].lstrip('/')))
    objects={o for o in set(scene.objects)-before if not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)}
    points=[o.matrix_world@Vector(c) for o in objects if o.type=='MESH' for c in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=(lo+hi)/2;center.z=lo.z;scale=height/(hi.z-lo.z) if height else extent/max(hi-lo)
    root=bpy.data.objects.new(id+'_DISPLAY',None);environment.objects.link(root)
    for obj in objects:
        if obj.parent not in objects:world=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=world
        move(obj)
    root.matrix_world=Matrix.Translation(location)@Matrix.Scale(scale,4)@Matrix.Translation(-center)
    root['credits']=json.dumps(assets[id]['credits'],ensure_ascii=False)
    return root
imported('SUP_hospital_01',(0,18,0),extent=24)
imported('SUP_facultad_de_enfermeria_unal_colombia',(-21,3,0),extent=17)
imported('SUP_esqueleto',(-7,4,1),height=1.5)
imported('SUP_Anatomic_Muscle_study',(7,4,1),height=1.5)
imported('SUP_kit_hospital',(1.1,4.5,1.1),height=.4)
# The book on the desk shows a real page from the supplied PDF.
page_image=ROOT.parents[1]/'work/nursing_lesson_page.png'
if page_image.exists():
    page=material('MAT_Study_Book_Page',(.95,.95,.9));image=bpy.data.images.load(str(page_image));image.pack()
    texture=page.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    bsdf=next(n for n in page.node_tree.nodes if n.type=='BSDF_PRINCIPLED');page.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=1,location=(-.6,4.45,1.115));obj=bpy.context.object;obj.name='PROP_Study_Book_Page_07';obj.scale=(.6,.85,1);obj.data.materials.append(page);move(obj)
for x in [-6,6]:box('PROP_Campus_Bench',(x,-5,.43),(2.6,.65,.15),wood)
# Export environment before characters/cameras are added; preserve all original assets.
dest=ROOT/'frontend/public/assets/models/ENV_PREP_Campus.glb';assert not dest.exists()
bpy.ops.object.select_all(action='DESELECT')
for obj in environment.all_objects:
    if obj.type=='MESH':obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='JPEG',export_jpeg_quality=85,export_extras=True)
validation=bpy.data.scenes.new('VALIDATE_PREP_CAMPUS');bpy.context.window.scene=validation;bpy.ops.import_scene.gltf(filepath=str(dest));assert any(o.type=='MESH' for o in validation.objects)
bpy.context.window.scene=scene
for i,r in enumerate(rigs):
    source=bpy.data.scenes['RIG_'+r['id'][4:]];arm=next(o for o in source.objects if o.type=='ARMATURE');body=next(o for o in source.objects if o.type=='MESH')
    col=characters if r['playable'] else study
    rig=arm.copy();rig.data=arm.data.copy();col.objects.link(rig);rig.name='NPC_'+r['id'][4:]+'_Rig'
    mesh=body.copy();col.objects.link(mesh);mesh.parent=rig;mesh.name='NPC_'+r['id'][4:]+'_Body'
    for modifier in mesh.modifiers:
        if modifier.type=='ARMATURE':modifier.object=rig
    root=bpy.data.objects.new('NPC_'+r['id'][4:]+'_Path',None);col.objects.link(root);rig.parent=root
    x=(i%4)*3.2-5;y=(i//4)*3.2-4
    root.location=(x,y,0)
    if not r['playable']:rig.scale=(.7,.7,.7)
    clip='Walk' if r['playable'] else 'Gesture'
    action=next(t.strips[0].action for t in arm.animation_data.nla_tracks if t.name==clip)
    rig.animation_data_clear();rig.animation_data_create();track=rig.animation_data.nla_tracks.new();track.name=clip
    strip=track.strips.new(clip,1,action);strip.repeat=4
    rig['rig_status']='Locomotion prototype' if r['playable'] else 'Fitted rig; source pose retained; needs repose for locomotion'
    if r['playable']:
        for frame,offset in [(1,0),(60,-2.0),(120,0)]:root.location=(x,y+offset,0);root.keyframe_insert(data_path='location',frame=frame)
scene.frame_start=1;scene.frame_end=120;scene.render.fps=30;scene.frame_set(9)
scene.world=bpy.data.worlds.new('PREP_CAMPUS_WORLD');scene.world.color=(.38,.48,.54)
bpy.ops.object.camera_add(location=(17,-23,13));camera=bpy.context.object;camera.name='CAM_PREP_Gameplay';camera.rotation_euler=(Vector((0,2,1))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=40;scene.camera=camera
bpy.ops.object.light_add(type='AREA',location=(0,-4,15));light=bpy.context.object;light.data.energy=6500;light.data.size=18
bpy.ops.object.light_add(type='SUN',location=(0,-5,10));bpy.context.object.data.energy=1.5;bpy.context.object.rotation_euler=(.4,-.2,-.4)
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.filepath=str(ROOT/'reports/PREP_GAMEPLAY_overview.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL'
report={'scene':scene.name,'characters':11,'locomotionPrototypes':7,'limitedPoseRigs':4,'environmentGlb':str(dest.relative_to(ROOT)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'reimportValidated':True,'timeline':[1,120]}
(ROOT/'reports/gameplay_scene.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
