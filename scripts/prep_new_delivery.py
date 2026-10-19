"""Derive only the October 6 delivery in isolated, factory background Blender.

The source directory is read-only. OBJ geometry duplicates are recorded and omitted
from derivatives. Missing material libraries are reported, never invented as facts.
One source scene and one organized derivative collection are saved for each asset.
"""
from pathlib import Path
import bpy,bmesh,json,hashlib,math,sys,struct,traceback
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/new_delivery_20261006';REPORT.mkdir(parents=True,exist_ok=True)
AUDIT=json.loads((REPORT/'source_audit.json').read_text(encoding='utf-8'))
SOURCE=Path(AUDIT['sourceRoot'])
OUT=ROOT/'frontend/public/assets/new-delivery';OUT.mkdir(parents=True,exist_ok=True)
ART=ROOT/'art/blender/new_delivery_20261006';ART.mkdir(parents=True,exist_ok=True)
SPECS={
 'bus_city':dict(id='VEH_Bus_City_20261006',label='Ônibus urbano PREPARATÓRIO',scope='ônibus',folder='BUS Yuxdesign high detail polygon model',kind='bus',length=12.4,budget=240000),
 'bus_brt':dict(id='VEH_Bus_BRT_20261006',label='Ônibus articulado PREPARATÓRIO',scope='ônibus',folder='Caio Millennium BRT - Mecedes Benz O500UDA',kind='bus',length=23.2,budget=240000),
 'bus_stop':dict(id='MOD_Bus_Stop_20261006',label='Parada de ônibus',scope='Parada de ônibus',kind='stop',width=8,budget=120000),
 'bus_terminal':dict(id='BLD_Bus_Terminal_20261006',label='Terminal de ônibus',scope='Terminal de Ônibus',kind='terminal',width=52,budget=120000),
 'student_xviii':dict(id='CHAR_Student_XVIII_20261006',label='Estudante do século XVIII',scope='Personagens/Estudiante S. XVIII',kind='character',height=1.75,budget=65000),
 'anatomy_xray':dict(id='EDU_Anatomy_XRay_20261006',label='Anatomia humana em camadas',scope='Esqueleto/Raio X Anatomia Humana',kind='anatomy',height=1.8,budget=180000),
}
key=sys.argv[sys.argv.index('--')+1];spec=SPECS[key];ID=spec['id']
dest=OUT/(ID+'.glb');blend=ART/(ID+'.blend');preview=REPORT/(ID+'.png');rp=REPORT/(ID+'.json')
assert not dest.exists(),f'Inspect existing output before overwriting: {dest}'
assert not blend.exists(),f'Inspect existing source scene before overwriting: {blend}'
audit=next(r for r in AUDIT['records'] if r['scope']==spec['scope'])
parts=[p for p in audit['objs'] if not spec.get('folder') or Path(p['path']).parent.name==spec['folder']]
parts.sort(key=lambda p:int(Path(p['path']).stem.split('_')[-1]))
credits=audit['glbs'][0]['asset'].get('extras',{}) if audit['glbs'] else {}
record={'id':ID,'label':spec['label'],'category':spec['kind'],'status':'processing','sourceCredits':credits,
 'licenseStatus':'CC-BY-4.0 embedded in supplied GLB' if credits.get('license') else 'No license or attribution file in supplied OBJ folder; source provenance pending',
 'sources':[], 'omittedDuplicateParts':[], 'excludedPresentationParts':[], 'modifications':[], 'rigged':False,'animations':[]}

def write_record():rp.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meshes(scene):return [o for o in scene.objects if o.type=='MESH' and not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
def bounds(objects):
 bpy.context.view_layer.update()
 # Decimation can retain unused positions outside rendered triangles. Exporters
 # drop them, so compare the actual face-referenced geometry on both sides.
 pts=[]
 for o in objects:
  used={i for polygon in o.data.polygons for i in polygon.vertices}
  pts.extend(o.matrix_world@o.data.vertices[i].co for i in used)
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
 return lo,hi
def triangles(objects):
 total=0
 for o in objects:o.data.calc_loop_triangles();total+=len(o.data.loop_triangles)
 return total
def point(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def material(name,color,metallic=0,roughness=.5,alpha=1):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,alpha)
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color
 bs.inputs['Metallic'].default_value=metallic;bs.inputs['Roughness'].default_value=roughness
 bs.inputs['Alpha'].default_value=alpha
 if alpha<1:m.surface_render_method='DITHERED'
 return m
def texture(mat,path,socket='Base Color',normal=False):
 bs=mat.node_tree.nodes.get('Principled BSDF');image=bpy.data.images.load(str(path),check_existing=True);image.pack()
 node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
 if normal:
  image.colorspace_settings.name='Non-Color';n=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(node.outputs['Color'],n.inputs['Color']);mat.node_tree.links.new(n.outputs['Normal'],bs.inputs['Normal'])
 else:mat.node_tree.links.new(node.outputs['Color'],bs.inputs[socket])
def text_mesh(collection,name,text,location,rotation,size,mat):
 curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.align_x='CENTER';curve.extrude=.001
 obj=bpy.data.objects.new(name,curve);collection.objects.link(obj);obj.location=location;obj.rotation_euler=rotation;curve.materials.append(mat)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH');return bpy.context.object
def studio(scene,objects):
 lo,hi=bounds(objects);center=(lo+hi)*.5;span=max(hi-lo)
 data=bpy.data.cameras.new('CAM_Delivery_Orthographic');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam)
 direction=Vector((1.15,-1.45,.8)) if spec['kind'] not in ['bus'] else Vector((1.5,-1.25,.9))
 cam.location=center+direction*span;point(cam,center);cam.data.type='ORTHO';cam.data.ortho_scale=span*1.28;cam.data.clip_end=max(1000,span*15);scene.camera=cam
 for name,offset,power,color in [('Key',(-1,-1,2),65,(1,.94,.9)),('Fill',(1,.4,1),35,(.84,.91,1)),('Rim',(-.3,1,1.5),45,(1,1,1))]:
  d=bpy.data.lights.new('LIGHT_Delivery_'+name,'AREA');o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o)
  o.location=center+Vector(offset)*span;point(o,center);d.energy=power*span*span;d.size=span*1.2
  d.color=color
 scene.world=bpy.data.worlds.new('WORLD_Delivery_Studio');scene.world.use_nodes=True
 bg=scene.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.08,.11,.15,1);bg.inputs['Strength'].default_value=.3
 scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
 scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
 scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(preview)

write_record()
try:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 source_scene=bpy.context.scene;source_scene.name='SOURCE_'+ID;source_scene['source_read_only']=True
 if parts:
  seen=set()
  for part in parts:
   if part['geometrySha256'] in seen:record['omittedDuplicateParts'].append(part['file']);continue
   seen.add(part['geometrySha256']);old=set(source_scene.objects)
   kwargs=dict(filepath=part['path'],forward_axis='Y',up_axis='Z') if spec['kind'] in ['bus','anatomy'] else dict(filepath=part['path'])
   bpy.ops.wm.obj_import(**kwargs)
   for obj in set(source_scene.objects)-old:obj['source_part']=Path(part['path']).name;obj['source_relative']=part['file'];obj['source_sha256']=part['sha256']
   record['sources'].append({path:part[path] for path in ['file','sha256','geometrySha256','missingMtllib']})
 else:
  source=audit['glbs'][0];bpy.ops.import_scene.gltf(filepath=source['path']);record['sources'].append({path:source[path] for path in ['file','sha256']})
 source_objects=meshes(source_scene);assert source_objects
 record['sourceBounds']=[list(v) for v in bounds(source_objects)];record['originalTriangles']=triangles(source_objects)
 work=bpy.data.scenes.new('PREP_'+ID);work.unit_settings.system='METRIC';work.unit_settings.scale_length=1
 collection=bpy.data.collections.new('PREP_DELIVERY_'+ID);work.collection.children.link(collection);bpy.context.window.scene=work
 derived=[]
 for source_obj in source_objects:
  obj=source_obj.copy();obj.data=source_obj.data.copy();matrix=source_obj.matrix_world.copy();obj.parent=None;collection.objects.link(obj);obj.matrix_world=matrix
  obj.name=ID+'_'+source_obj.get('source_part',source_obj.name);derived.append(obj)
  if key=='bus_brt' and source_obj.get('source_part')=='model_13.obj':
   bm=bmesh.new();bm.from_mesh(obj.data)
   pedestal_faces=[face for face in bm.faces if max(v.co.z for v in face.verts)<.01 or min(v.co.z for v in face.verts)<-.01]
   removed=len(pedestal_faces);bmesh.ops.delete(bm,geom=pedestal_faces,context='FACES');bm.to_mesh(obj.data);bm.free();obj.data.update()
   record['excludedPresentationParts'].append({'file':'model_13.obj','faces':removed,'reason':'Only rectangular display pedestal faces at/below tire ground removed from derivative; articulation bellows retained; source scene intact'})
 lo,hi=bounds(derived);size=hi-lo
 scale=spec['length']/size.y if spec.get('length') else spec['width']/size.x if spec.get('width') else spec['height']/size.z
 origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));transform=Matrix.Scale(scale,4)@Matrix.Translation(-origin)
 for obj in derived:obj.matrix_world=transform@obj.matrix_world
 record['normalizationScale']=scale
 record['modifications'].append('Uniform normalization of freshly imported static derivative only; centered horizontal origin and minimum Z=0; source geometry and files retained')
 if parts:
  mats={
   'body':material('MAT_PREP_Bus_Paint',(.035,.22,.32),.28,.28),
   'white':material('MAT_PREP_Porcelain',(.78,.83,.85),.12,.32),
   'dark':material('MAT_PREP_Rubber',(.018,.021,.026),0,.8),
   'glass':material('MAT_PREP_Window_Glass',(.055,.13,.18),.2,.15,.72),
   'metal':material('MAT_PREP_Anodized_Metal',(.32,.38,.43),.72,.3),
   'seat':material('MAT_PREP_Fabric_Seats',(.075,.12,.15),0,.75),
   'bone':material('MAT_PREP_Anatomy_Bone',(.78,.74,.58),0,.7),
   'muscle':material('MAT_PREP_Anatomy_Tissue',(.53,.10,.12),0,.6),
   'skin':material('MAT_PREP_Anatomy_XRay_Skin',(.32,.64,.71),0,.4,.22),
  }
  for obj in derived:
   part=int(Path(obj['source_part']).stem.split('_')[-1])
   if spec['kind']=='bus':
    if key=='bus_city':role='glass' if part==30 else 'dark' if 19<=part<=26 else 'white' if part in [1,3] else 'body' if part==2 else 'metal'
    else:role='dark' if part in [8,9,10,11] else 'glass' if part in [5,27,30] else 'white' if part in [0,15,21,25] else 'seat' if part in [18,19,20] else 'body' if part in [1,2,26] else 'metal'
   elif spec['kind']=='anatomy':role={0:'muscle',1:'skin',2:'bone',3:'muscle',9:'bone'}.get(part,'bone')
   else:role='white'
   obj.data.materials.clear();obj.data.materials.append(mats[role]);obj['recovered_material_role']=role
  record['modifications'].append('Missing OBJ MTL: documented provisional part-level PBR materials; no source logos/textures copied to buses')
  if spec['kind']=='terminal':
   folder=SOURCE/spec['scope'];mat=material('MAT_PREP_Terminal_Recovered',(.65,.68,.69),0,.55)
   texture(mat,folder/'terminalvaradero_d.png');texture(mat,folder/'terminalvaradero_n.png',normal=True)
   for obj in derived:obj.data.materials.clear();obj.data.materials.append(mat)
   record['modifications'].append('Terminal diffuse and normal association recovered from unambiguous matching basename; specular map retained in source, not asserted to be roughness')
 else:
  copies={}
  for obj in derived:
   for slot in obj.material_slots:
    original=slot.material
    if not original:continue
    if original not in copies:copies[original]=original.copy()
    slot.material=copies[original]
  image_copies={}
  for mat in copies.values():
   if not mat.use_nodes:continue
   for node in mat.node_tree.nodes:
    if node.type!='TEX_IMAGE' or not node.image:continue
    image=node.image
    if image not in image_copies:
     copied=image.copy();cap=2048 if spec['kind']=='character' else 1024
     factor=min(1,cap/max(copied.size))
     if factor<1:copied.scale(max(1,round(copied.size[0]*factor)),max(1,round(copied.size[1]*factor)))
     copied.pack();image_copies[image]=copied
    node.image=image_copies[image]
  record['modifications'].append('Original supplied PBR materials retained on derivative; textures capped at 2048 character / 1024 environment')
 total=triangles(derived);ratio=min(1,spec['budget']/total)
 for obj in derived:
  for face in obj.data.polygons:face.use_smooth=True
  if len(obj.data.polygons)>1000 and ratio<1:
   bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
   mod=obj.modifiers.new('PREP_Game_Mesh_Reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
   bpy.ops.object.modifier_apply(modifier=mod.name)
 if ratio<1:record['modifications'].append('Per-part decimation to web presentation budget; part hierarchy and source scene preserved')
 lo,hi=bounds(derived);ground_adjust=Matrix.Translation(Vector((0,0,-lo.z)))
 for obj in derived:obj.matrix_world=ground_adjust@obj.matrix_world
 lo,hi=bounds(derived);dims=hi-lo
 if spec['kind']=='bus':
  label_mat=material('MAT_PREP_Bus_Lettering',(.025,.12,.18),0,.4)
  front_label_mat=material('MAT_PREP_Bus_Destination_Lettering',(.9,.95,1),0,.4)
  derived.append(text_mesh(collection,'SIGN_PREPARATÓRIO','PREPARATÓRIO',(dims.x/2+.008,-dims.y*.15,dims.z*.36),(math.pi/2,0,math.pi/2),.2,label_mat))
  derived.append(text_mesh(collection,'SIGN_HOSPITAL_CENTRO','HOSPITAL / CENTRO',(0,-dims.y/2-.008,dims.z*.84),(math.pi/2,0,0),.14,front_label_mat))
  record['modifications'].append('Original Portuguese 3D PREPARATÓRIO/HOSPITAL CENTRO fleet signage added')
 bpy.ops.object.select_all(action='DESELECT')
 for obj in derived:obj.select_set(True)
 bpy.context.view_layer.objects.active=derived[0]
 record['preparedTriangles']=triangles(derived);record['preparedBounds']=[list(v) for v in bounds(derived)]
 bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,
  export_animations=False,export_skins=False,export_extras=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
 validation=bpy.data.scenes.new('VALIDATE_'+ID);bpy.context.window.scene=validation;bpy.ops.import_scene.gltf(filepath=str(dest))
 actual=meshes(validation);assert actual and all(math.isfinite(f) for o in actual for v in o.data.vertices for f in v.co)
 lo2,hi2=bounds(actual);lo1,hi1=[Vector(v) for v in record['preparedBounds']]
 assert max(abs(f) for f in (lo2-lo1))<.002 and max(abs(f) for f in (hi2-hi1))<.002,(list(lo1),list(lo2),list(hi1),list(hi2))
 data=dest.read_bytes();g=json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]])
 primitives=[sum(g['accessors'][p['indices']]['count']//3 for p in m['primitives'] if p.get('mode',4)==4) for m in g['meshes']]
 def node_triangles(i):
  n=g['nodes'][i];return (primitives[n['mesh']] if 'mesh' in n else 0)+sum(node_triangles(c) for c in n.get('children',[]))
 expected=sum(node_triangles(i) for i in g['scenes'][g.get('scene',0)]['nodes'])
 assert triangles(actual)==expected,(triangles(actual),expected)
 record.update(status='validated',url='/assets/new-delivery/'+dest.name,bytes=dest.stat().st_size,sha256=sha(dest),
  dimensions=list(hi2-lo2),triangles=expected,meshCount=len(actual),origin='horizontal center; ground Z=0; GLB Y-up',
  validation='Delivered GLB reimported; finite vertices; triangle primitives and bounds match',
  blend=str(blend),collection=collection.name,preview=str(preview))
 record['components']=[{'name':o.name,'sourcePart':o.get('source_part'),'materialRole':o.get('recovered_material_role')} for o in derived]
 if spec['kind']=='character':
  record['rigStatus']='Supplied GLB has no armature or animations; two historical photogrammetry figures side by side; static cultural display, not claimed playable'
  record['figures']=2
 studio(validation,actual)
 bpy.context.window.scene=work
 bpy.ops.wm.save_as_mainfile(filepath=str(blend))
 bpy.context.window.scene=validation;bpy.ops.render.render(write_still=True)
 record['previewRendered']=preview.exists();write_record()
 license_path=OUT/(ID+'.LICENSE.txt')
 license_path.write_text(json.dumps({'sourceCredits':credits,'licenseStatus':record['licenseStatus'],'sourceFiles':record['sources'],'modifications':record['modifications']},ensure_ascii=False,indent=2),encoding='utf-8')
 print('PREP_DELIVERY_VALIDATED '+json.dumps(record,ensure_ascii=False))
except Exception:
 record.update(status='failed',error=traceback.format_exc());write_record();raise
