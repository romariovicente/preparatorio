"""Author a real furniture derivative and a reversible hospital scene via live MCP."""
import bpy,json,math,sys,hashlib,struct
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_incremental_scene_tools_20261020 import save_scene_library,sha256
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
checkpoint=json.loads((ROOT/'reports/INTEGRATED_BEFORE_CHAIRS_20261020.json').read_text())
assert Path(checkpoint['checkpoint']).is_file()
assert 'PREP_HOSPITAL_CHAIRS_ASSET_20261020' not in bpy.data.scenes
review=bpy.data.scenes['PREP_CHAIR_SOURCE_REVIEW_20261020']
source=bpy.data.objects['CHAIR20_REVIEW_Eames']
# The supplied set includes an ottoman: retain it in the review scene only.
excluded=('Repose Pied','Boutons coussin')
sources=[o for o in source.children_recursive if o.type=='MESH' and not any(v in o.name for v in excluded)]
assert len(sources)==18,(len(sources),[o.name for o in sources])
scene=bpy.data.scenes.new('PREP_HOSPITAL_CHAIRS_ASSET_20261020')
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
for w in bpy.context.window_manager.windows:w.scene=scene
col=bpy.data.collections.new('HCH20_REAL_CHAIR');scene.collection.children.link(col)
root=bpy.data.objects.new('HCH20_LOUNGE_CHAIR',None);col.objects.link(root)
def center(obj):
    ps=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    return (Vector([min(p[i] for p in ps) for i in range(3)])+Vector([max(p[i] for p in ps) for i in range(3)]))/2
seat=next(o for o in sources if o.name=='Coussin Fauteuil_Cuir_0')
back=next(o for o in sources if o.name=='Coussin Haut Fauteuil_Cuir_0')
direction=center(back)-center(seat);angle=math.atan2(direction.x,direction.y)
rot=Matrix.Rotation(angle,4,'Z')
points=[rot@(o.matrix_world@v.co) for o in sources for v in o.data.vertices]
lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
scale=.98/(hi.z-lo.z)
centerxy=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
normalize=Matrix.Scale(scale,4)@Matrix.Translation(-centerxy)@rot
material_map={};image_map={};parts=[];tri_before=tri_after=0
texdir=ROOT/'art/source/hospital_chairs_20261020/runtime_textures';texdir.mkdir(parents=True,exist_ok=True)
for index,obj in enumerate(sources):
    mesh=obj.data.copy();mesh.transform(normalize@obj.matrix_world)
    copy=bpy.data.objects.new('HCH20_PART_'+str(index).zfill(2),mesh);col.objects.link(copy);copy.parent=root
    for i,mat in enumerate(list(mesh.materials)):
        if mat not in material_map:
            new=mat.copy();new.name='HCH20_'+mat.name
            if new.use_nodes:
                for node in new.node_tree.nodes:
                    if node.type!='TEX_IMAGE' or not node.image:continue
                    original=node.image
                    if original not in image_map:
                        image=original.copy();image.name='HCH20_'+original.name
                        longest=max(image.size);factor=min(1,1024/longest)
                        image.scale(max(1,round(image.size[0]*factor)),max(1,round(image.size[1]*factor)))
                        image.file_format='PNG';image.filepath_raw=str(texdir/(str(len(image_map)).zfill(2)+'.png'));image.save();image.pack();image_map[original]=image
                    node.image=image_map[original]
            material_map[mat]=new
        mesh.materials[i]=material_map[mat]
    mesh.calc_loop_triangles();initial=len(mesh.loop_triangles);tri_before+=initial
    if initial>1500:
        mod=copy.modifiers.new('HCH20_BROWSER_DETAIL','DECIMATE');mod.ratio=max(.07,min(1,65000/700000));mod.use_collapse_triangulate=True
        bpy.context.view_layer.objects.active=copy;copy.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name);copy.select_set(False)
    copy.data.calc_loop_triangles();tri_after+=len(copy.data.loop_triangles)
    copy['source_object']=obj.name;copy['source_geometry_preserved_in_review']=True
    parts.append(copy)
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box]
low=Vector([min(p[i] for p in points) for i in range(3)]);high=Vector([max(p[i] for p in points) for i in range(3)])
assert abs(low.z)<.002 and .975<high.z<.985
assert high.x-low.x<1.15 and high.y-low.y<1.15,(list(low),list(high))
root['source']='Eames Lounge Chair 01';root['footrest_excluded']=True;root['ground_origin']=True
out=ROOT/'frontend/public/assets/additions20261020/PROP_Hospital_Lounge_Chair_20261020.glb';out.parent.mkdir(parents=True,exist_ok=True)
for o in scene.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_active_scene=True,use_selection=True,export_animations=False,export_extras=True,export_image_format='JPEG',export_jpeg_quality=90)
docbytes=out.read_bytes();doc=json.loads(docbytes[20:20+struct.unpack_from('<I',docbytes,12)[0]])
assert len(doc.get('scenes',[]))==1 and not doc.get('animations')
assert len(doc.get('meshes',[]))==18
placements=[]
for row,z in enumerate((10.5,5.3)):
    for j,x in enumerate((5,7.2,9.4,11.6,13.8)):
        key=f'{row}_{j}';placements.append({'id':key,'originalRoot':'HSP15_CHAIR_'+key,'position':[x,.012,z],'rotation':[0,math.pi if row==0 else 0,0]})
for key,x,z in [('01',-5.8,-3),('02',5.8,-3),('03',-5.8,-11),('04',5.8,-11)]:
    placements.append({'id':'ROOM_'+key,'originalRoot':'HSP15_CHAIR_ROOM_'+key,'position':[x,.012,z],'rotation':[0,0,0]})
plan={'version':1,'ready':True,'asset':'/assets/additions20261020/'+out.name,'sourceScene':scene.name,
 'dimensions':[high.x-low.x,high.z-low.z,high.y-low.y], 'bounds':{'min':[low.x,low.z,-high.y],'max':[high.x,high.z,-low.y]},
 'placements':placements,'triangles':tri_after,'bytes':out.stat().st_size,'sha256':sha256(out),'sourceOriginal':str(ROOT/'art/source/hospital_chairs_20261020/Eames_Original.glb'),
 'sourceSha256':sha256(ROOT/'art/source/hospital_chairs_20261020/Eames_Original.glb'),
 'changes':['Separated lounge chair from supplied ottoman','Uniform scale and upright yaw; ground origin','Browser mesh simplification and 1024px texture copies; original source retained','Waiting rows face the shared aisle; room chairs face desks'],
 'certifiedClinicalOrArchitectural':False}
(ROOT/'frontend/src/config/hospitalChairs.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
assetlib=save_scene_library(scene,ROOT/'art/blender/PREPARATORIO_HOSPITAL_CHAIRS_ASSET_20261020.blend')
# Duplicate only hospital architecture; source scene and source chairs are retained.
hospital=bpy.data.scenes.new('PREP_HOSPITAL_CHAIRS_CITY_20261020');hospital.unit_settings.system='METRIC'
for w in bpy.context.window_manager.windows:w.scene=hospital
architecture=bpy.data.collections.new('HCH20_HOSPITAL');hospital.collection.children.link(architecture)
anchor=bpy.data.objects.new('HCH20_HOSPITAL_ANCHOR',None);architecture.objects.link(anchor);anchor.location=(48,38,.26)
old=bpy.data.scenes['PREP_HOSPITAL_RECEPTION_20261015'];mapping={}
originals=[o for o in old.objects if o.type in ('MESH','EMPTY','LIGHT') and not o.get('preview_reference') and not o.name.startswith('HSP15_CHAIR_')]
for obj in originals:
    copy=obj.copy();copy.name='HCH20_'+obj.name;architecture.objects.link(copy);mapping[obj]=copy
for obj,copy in mapping.items():
    copy.parent=mapping.get(obj.parent,anchor);copy.matrix_parent_inverse=obj.matrix_parent_inverse.copy();copy.matrix_basis=obj.matrix_basis.copy();copy['source_object']=obj.name
chairs=bpy.data.collections.new('HCH20_CHAIRS_PLACED');hospital.collection.children.link(chairs)
for p in placements:
    instance=bpy.data.objects.new('HCH20_CHAIR_'+p['id'],None);chairs.objects.link(instance);instance.instance_type='COLLECTION';instance.instance_collection=col
    instance.location=(48+p['position'][0],38-p['position'][2],.26+p['position'][1]);instance.rotation_euler.z=-p['rotation'][1]
hospital.world=old.world.copy()
studio=bpy.data.collections.new('HCH20_STUDIO');hospital.collection.children.link(studio)
camdata=bpy.data.cameras.new('HCH20_CAMERA_RECEPTION');cam=bpy.data.objects.new(camdata.name,camdata);studio.objects.link(cam);cam.location=(51,25,2.15);cam.rotation_euler=(Vector((58,30.4,1))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=28;camdata.clip_start=.03;hospital.camera=cam
for name,location in [('WAITING',(57,30,3.8)),('ROOM',(48,40,3.8))]:
    data=bpy.data.lights.new('HCH20_SOFT_'+name,'AREA');data.energy=800;data.shape='DISK';data.size=5
    light=bpy.data.objects.new(data.name,data);studio.objects.link(light);light.location=location
hospital.render.engine='BLENDER_EEVEE';hospital.render.resolution_x=1440;hospital.render.resolution_y=960;hospital.render.resolution_percentage=100;hospital.render.image_settings.file_format='PNG';hospital.view_settings.view_transform='AgX'
for image in bpy.data.images:
    if image.name.startswith('HCH20_') and image.users and not image.packed_file:image.pack()
citylib=save_scene_library(hospital,ROOT/'art/blender/PREPARATORIO_HOSPITAL_CHAIRS_CITY_20261020.blend')
report={'checkpoint':checkpoint['checkpoint'],'assetLibrary':assetlib,'hospitalLibrary':citylib,'asset':plan,'sourceChairMeshes':len(sources),'sourceTriangles':tri_before,'runtimeTriangles':tri_after,'images':len(image_map),'oldHospitalSceneUnchanged':True,'oldChairRootsRetained':14,'doorsPreserved':all(any(o.get('source_object')==name for o in hospital.objects) for name in ['HSP15_DOOR_PUBLIC_Left','HSP15_DOOR_PUBLIC_Right']),'preview':str(ROOT/'reports/hospital_chairs_20261020.png'),'masterSaved':False}
(ROOT/'reports/HOSPITAL_CHAIRS_BLENDER_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
hospital.render.filepath=report['preview'];bpy.ops.render.render(write_still=True)
print(json.dumps({'assetBytes':out.stat().st_size,'triangles':tri_after,'placements':len(placements),'preview':report['preview']}))
