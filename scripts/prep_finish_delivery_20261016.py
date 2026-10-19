"""Create an organized animal exhibit and save the validated working master."""
import bpy, hashlib, json, sys
from pathlib import Path
from datetime import datetime
from mathutils import Vector

ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
records=json.loads((ROOT/'frontend/src/config/suppliedAdditions20261016.json').read_text(encoding='utf-8'))
assert len(records)==13 and all(r['reimportValidated'] for r in records)
prior=list(bpy.data.objects);before=state_hash(object_state(prior))
name='PREP_FAUNA_GALLERY_20261016'
assert name not in bpy.data.scenes,'Inspect an existing delivery exhibit before replacing it.'
scene=bpy.data.scenes.new(name);scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['purpose']='Organized supplied animal display; not another playable city or a wildlife simulation.'
scene.render.fps=30;scene.frame_start=1;scene.frame_end=250
for w in bpy.context.window_manager.windows:w.scene=scene
exhibit=bpy.data.collections.new('PREP_CITY_FAUNA_EXHIBIT_20261016');scene.collection.children.link(exhibit)
studio=bpy.data.collections.new('PREP_CITY_EXHIBIT_STUDIO_20261016');scene.collection.children.link(studio)
for code,pos,angle in [('FOX',(-3.3,-1.6,0),.3),('RABBIT',(-.8,-1.8,0),.2),('WOLF',(1.3,-1.4,0),.1),
                       ('LIONESS',(-2.3,1.5,0),.1),('HORSE',(2.8,1.5,0),.1)]:
    record=next(r for r in records if r['id']=='FAUNA_'+code+'_20261016')
    collections=[c for c in bpy.data.scenes[record['blenderScene']].collection.children
                 if c.name.startswith('PREP_CITY_FAUNA_'+code)]
    assert len(collections)==1,'Use the validated source collection, excluding preserved failed trials.'
    collection=collections[0]
    obj=bpy.data.objects.new('EXHIBIT_'+code,None);exhibit.objects.link(obj)
    obj.instance_type='COLLECTION';obj.instance_collection=collection;obj.location=pos;obj.rotation_euler.z=angle
    obj['asset_id']='FAUNA_'+code+'_20261016';obj['reuses_validated_source_collection']=True

def mat(name,color,rough=.5):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough
    return m
floor_mat=mat('MAT_PREP_EXHIBIT_FLOOR_20261016',(.075,.10,.12),.7)
mesh=bpy.data.meshes.new('MESH_PREP_EXHIBIT_FLOOR_20261016')
mesh.from_pydata([(-7,-5,-.025),(7,-5,-.025),(7,6,-.025),(-7,6,-.025)],[],[(0,1,2,3)])
floor=bpy.data.objects.new('PREP_EXHIBIT_FLOOR',mesh);studio.objects.link(floor);mesh.materials.append(floor_mat)
camdata=bpy.data.cameras.new('CAM_PREP_FAUNA_EXHIBIT');cam=bpy.data.objects.new(camdata.name,camdata);studio.objects.link(cam)
center=Vector((0,.5,1));cam.location=(10,-13,10)
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=11.4
scene.camera=cam
for label,pos,power,size,color in [('KEY',(1,-4,10),2400,8,(1,.94,.87)),('FILL',(-6,-1,5),1400,8,(.80,.9,1)),('RIM',(0,6,6),1900,6,(1,1,1))]:
    data=bpy.data.lights.new('LIGHT_PREP_EXHIBIT_'+label,'AREA');obj=bpy.data.objects.new(data.name,data);studio.objects.link(obj)
    obj.location=pos;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler();data.energy=power;data.size=size;data.color=color
world=bpy.data.worlds.new('WORLD_PREP_FAUNA_EXHIBIT');world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.09,.12,.16,1);bg.inputs['Strength'].default_value=.45;scene.world=world
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'reports/fauna_gallery_20261016.png')
scene.frame_set(1);bpy.ops.render.render(write_still=True)
assert state_hash(object_state(prior))==before,'A previous stored object channel changed while assembling exhibit.'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.shading.use_scene_lights=True
            area.spaces.active.shading.use_scene_world=True
guardian=bpy.app.driver_namespace.get('PREPARATORIO_AUTOSAVE_GUARDIAN')
checkpoint={'state':object_state(prior),'hash':before}
(ROOT/'art/blender/checkpoints/DELIVERY_BEFORE_EXHIBIT_20261016.json').write_text(json.dumps(checkpoint,ensure_ascii=False),encoding='utf-8')
saved_state=object_state(list(bpy.data.objects))
(ROOT/'art/blender/checkpoints/DELIVERY_SAVED_STATE_20261016.json').write_text(json.dumps({'state':saved_state,'hash':state_hash(saved_state)},ensure_ascii=False),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report={'timeLocal':datetime.now().astimezone().isoformat(timespec='seconds'),'master':str(MASTER),'masterBytes':MASTER.stat().st_size,
    'scenes':len(bpy.data.scenes),'objects':len(bpy.data.objects),'materials':len(bpy.data.materials),'collections':len(bpy.data.collections),
    'activeScene':scene.name,'newCatalogAssets':len(records),'animatedAnimals':sum(r['category']=='Animais' for r in records),
    'newCatalogClips':sum(len(r['animations']) for r in records),'previousStoredObjectChannelsMatch':True,
    'guardianRegistered':bool(guardian and bpy.app.timers.is_registered(guardian)),
    'deliveries':[{'id':r['id'],'url':r['url'],'bytes':r['bytes'],'sha256':r['sha256'],'animations':r['animations']} for r in records],
    'preview':scene.render.filepath,'limitations':['New assets are organized in Blender and accessible in the game catalog. They are not all placed in the playable city.',
    'Supplied OBJ materials are reconstructed presentation colors. Source MTL files are missing.',
    'New train/track/station are static assets; driving/boarding/path operation have not been implemented for these new models.',
    'No additional human character was promoted to playable without realistic rig and locomotion validation.']}
(ROOT/'reports/DELIVERY_SAVED_20261016.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PREP_DELIVERY_SAVED '+json.dumps({k:report[k] for k in ['masterBytes','scenes','objects','activeScene','newCatalogAssets','newCatalogClips','guardianRegistered']}))
