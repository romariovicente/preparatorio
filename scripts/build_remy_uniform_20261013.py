"""Complete the interrupted uniform in a fresh background Blender process.

Keeps both original files. Garment surfaces derive from Remy's existing meshes
and skin; no invented replacement character or animation is exported.
"""
import bpy, json, hashlib, math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb'
OLD=ROOT/'frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261009.glb'
TARGET=ROOT/'frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261013.glb'
BLEND=ROOT/'art/blender/CHR_Remy_Senac_Uniform_20261013.blend'
REPORT=ROOT/'reports/costumes/remy_senac_uniform_20261013.json'
IDENTITY=ROOT/'frontend/public/assets/uniforms/senac_20261009'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash,old_hash=sha(SOURCE),sha(OLD)
REPORT.parent.mkdir(parents=True,exist_ok=True);BLEND.parent.mkdir(parents=True,exist_ok=True)
references=json.loads((ROOT/'frontend/src/config/uniformReferences.json').read_text(encoding='utf-8'))
for reference in references['files']:
 assert sha(IDENTITY/reference['name'])==reference['sha256']

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
top=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Tops'))
bottom=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Bottoms'))
body=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Body'))
originals=[o for o in scene.objects if o.type in ('MESH','ARMATURE','EMPTY') and o.name!='Icosphere']
garments=[]

def fabric(name,color):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
 p.inputs['Roughness'].default_value=.86
 return mat
scrub_mat=fabric('SCRUB_Remy_Cotton',(.247,.515,.682))
coat_mat=fabric('COAT_Remy_Cotton',(.94,.955,.97))
button_mat=fabric('COAT_Remy_Button',(.79,.83,.87))

def weight_names(src,index):
 return [(src.vertex_groups[g.group].name,g.weight) for g in src.data.vertices[index].groups if g.weight>1e-5]

def copied_garment(src,name,mat):
 obj=src.copy();obj.data=src.data.copy();obj.name=name;scene.collection.objects.link(obj)
 obj.data.materials.clear();obj.data.materials.append(mat)
 for p in obj.data.polygons:p.material_index=0
 garments.append(obj);return obj

def surface(name,points,faces,mat,weights,uvs=None):
 mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(points,[],faces);mesh.update()
 obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
 # Vertices are authored in world metres. Inverse binds follow the original rig.
 obj.parent=arm;obj.matrix_world=body.matrix_world.copy()
 inv=obj.matrix_world.inverted()
 for vertex,point in zip(mesh.vertices,points):vertex.co=inv@Vector(point)
 mesh.materials.append(mat)
 groups={g.name:obj.vertex_groups.new(name=g.name) for g in body.vertex_groups}
 for index,vertex_weights in enumerate(weights):
  total=sum(w for _,w in vertex_weights)
  for name,weight in vertex_weights:
   if weight>1e-5:groups[name].add([index],weight/total,'REPLACE')
 mod=obj.modifiers.new('Remy_Original_Skin','ARMATURE');mod.object=arm
 if uvs:
  layer=mesh.uv_layers.new(name='Uniform_UV')
  for polygon in mesh.polygons:
   for loop in polygon.loop_indices:layer.data[loop].uv=uvs[mesh.loops[loop].vertex_index]
 for polygon in mesh.polygons:polygon.use_smooth=True
 garments.append(obj);return obj

body_points=[body.matrix_world@v.co for v in body.data.vertices]
body_tree=KDTree(len(body_points))
for i,p in enumerate(body_points):body_tree.insert(p,i)
body_tree.balance()

shirt=copied_garment(top,'SCRUB_Remy_Shirt',scrub_mat)
coat=copied_garment(top,'COAT_Remy_FittedShell',coat_mat)
# Expand radially instead of offsetting mixed outer/inner vertex normals. Apply
# one continuous mapping across the whole hem, preserving shirt connectivity.
for obj,is_coat in [(shirt,False),(coat,True)]:
 inv=obj.matrix_world.inverted()
 for v in obj.data.vertices:
  p=obj.matrix_world@v.co
  if p.z<1.26:
   amount=max(0,min(1,(1.10-p.z)/.215)) if is_coat else 0
   p.x=(p.x+.009)*(1.09+amount*.08 if is_coat else 1.015)-.009
   p.y=(p.y-.035)*(1.19+amount*.15 if is_coat else 1.025)+.035
   if is_coat and p.z<1.10:
    p.z=1.10+(p.z-1.10)*2.03
    # The lower coat follows the thighs, with a smooth transition at the hips.
    # It remains a skinned garment, not a cloth simulation.
    factor=max(0,min(.82,(.995-p.z)/.31))
    if factor>0:
     for g in obj.vertex_groups:g.remove([v.index])
     side='Left' if p.x>-.006 else 'Right'
     obj.vertex_groups['mixamorig:Hips'].add([v.index],1-factor,'REPLACE')
     obj.vertex_groups['mixamorig:'+side+'UpLeg'].add([v.index],factor,'REPLACE')
  elif is_coat:
   # Keep short sleeves outside the scrub shirt at the shoulder seam.
   p.y=(p.y-.073)*1.14+.073;p.z=(p.z-1.426)*1.14+1.426
  v.co=inv@p
 obj.data.update()

trousers=copied_garment(bottom,'SCRUB_Remy_Trousers',scrub_mat)
inv=trousers.matrix_world.inverted()
for v in trousers.data.vertices:
 p=trousers.matrix_world@v.co;cx=.083 if p.x>-.006 else -.092
 old_z=p.z
 if old_z<.70:
  taper=max(0,min(1,(.70-old_z)/.18))
  p.z=.14+(old_z-.52)*(.56/.18) if old_z>=.52 else .14+(old_z-.52)*.15
  p.x=cx+(p.x-cx)*(1.025-taper*.34)
  p.y=(p.y-.025)*(1.025-taper*.25)+.025
  _,index,_=body_tree.find(p)
  for g in trousers.vertex_groups:g.remove([v.index])
  for name,weight in weight_names(body,index):trousers.vertex_groups[name].add([v.index],weight,'REPLACE')
 else:
  p.x=cx+(p.x-cx)*1.025;p.y=(p.y-.025)*1.025+.025
 v.co=inv@p
trousers.data.update()

# Anatomical sleeves and trouser legs inherit the supplied elbow/knee weights.
def body_region(name,predicate,expand,mat):
 eligible={i for i,p in enumerate(body_points) if predicate(i,p)}
 faces=[tuple(p.vertices) for p in body.data.polygons if all(i in eligible for i in p.vertices)]
 used=sorted({i for face in faces for i in face});lookup={old:i for i,old in enumerate(used)}
 return surface(name,[expand(body_points[i].copy()) for i in used],
  [tuple(lookup[i] for i in face) for face in faces],mat,[weight_names(body,i) for i in used])

arm_groups={g.index for g in body.vertex_groups if g.name.endswith(('LeftArm','RightArm','LeftForeArm','RightForeArm'))}
def sleeve(i,p):return .27<abs(p.x)<.689 and sum(g.weight for g in body.data.vertices[i].groups if g.group in arm_groups)>.72
def expand_sleeve(p):
 p.y=(p.y-.073)*1.28+.073;p.z=(p.z-1.426)*1.28+1.426;return p
body_region('COAT_Remy_LongSleeves',sleeve,expand_sleeve,coat_mat)
leg_groups={g.index for g in body.vertex_groups if g.name.endswith(('UpLeg','LeftLeg','RightLeg','LeftFoot','RightFoot'))}
def leg(i,p):return .125<p.z<.98 and sum(g.weight for g in body.data.vertices[i].groups if g.group in leg_groups)>.72
def expand_leg(p):
 cx=.081 if p.x>-.006 else -.094
 r=Vector((p.x-cx,p.y-.028,0));r.normalize();p+=r*.009;return p
# The trouser surface is continuous from the original waistband to the ankles;
# its extended vertices are weighted from the actual knees/calves, avoiding the
# separate shorts-over-calves seam of the first recovery preview.
body_region('SCRUB_Remy_TrouserLining',leg,expand_leg,scrub_mat)

top_points=[top.matrix_world@v.co for v in top.data.vertices]
tree=KDTree(len(top_points))
for i,p in enumerate(top_points):tree.insert(p,i)
tree.balance()
def chest_point(x,z,is_coat):
 candidates=tree.find_n(Vector((x,-.15,z)),24)
 front=[(dist,i,p) for p,i,dist in candidates if p.y<.005 and abs(p.x-x)<.055]
 _,index,_=min(front,key=lambda item:item[0]) if front else (candidates[0][2],candidates[0][1],candidates[0][0])
 y=(top_points[index].y-.035)*(1.19 if is_coat else 1.025)+.035-(.009 if is_coat else .004)
 return Vector((x,y,z)),weight_names(top,index)

def patch(name,cx,cz,width,height,mat,is_coat=True,outline=None):
 points=[];weights=[];uvs=[];nx,ny=10,8
 for r in range(ny+1):
  for c in range(nx+1):
   p,w=chest_point(cx+(c/nx-.5)*width,cz+(r/ny-.5)*height,is_coat)
   points.append(p);weights.append(w);uvs.append((c/nx,r/ny))
 faces=[(r*(nx+1)+c,r*(nx+1)+c+1,(r+1)*(nx+1)+c+1,(r+1)*(nx+1)+c) for r in range(ny) for c in range(nx)]
 return surface(name,points,faces,mat,weights,uvs)

def embroidery(name,path=None):
 mat=fabric(name,(1,1,1));p=mat.node_tree.nodes.get('Principled BSDF')
 mat.surface_render_method='DITHERED';mat.use_backface_culling=False
 if path:
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
  mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);mat.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha'])
 else:p.inputs['Alpha'].default_value=0
 return mat
crest=embroidery('Uniform_NursingCrest',IDENTITY/'nursing-crest.png')
logo=embroidery('Uniform_SenacLogo',IDENTITY/'senac-logo.png')
name_mat=embroidery('Uniform_PlayerName_Runtime')
for prefix,is_coat in [('COAT',True),('SCRUB',False)]:
 patch(prefix+'_BRAND_Remy_Crest',-.106,1.325,.112,.127,crest,is_coat)
 patch(prefix+'_BRAND_Remy_Senac',.105,1.407,.072,.073,logo,is_coat)
 patch(prefix+'_NAME_Remy_Player',.093,1.302,.159,.060,name_mat,is_coat)

# Lapels, a narrow front placket, buttons and pockets make the outer shell read
# as a coat rather than a lengthened shirt. They share the original chest skin.
for side in [-1,1]:
 coords=[(side*.045,1.49),(side*.123,1.455),(side*.041,1.365),(side*.018,1.397)]
 points=[];weights=[]
 for x,z in coords:
  p,w=chest_point(x,z,True);p.y-=.006;points.append(p);weights.append(w)
 surface('COAT_Remy_Lapel_'+('Left' if side>0 else 'Right'),points,[(0,1,2,3)],coat_mat,weights)
 # Pockets lie on the torso, above the bend at the hips.
 patch('COAT_Remy_Pocket_'+('Left' if side>0 else 'Right'),side*.115,1.065,.108,.115,coat_mat)
patch('COAT_Remy_FrontPlacket',-.007,1.22,.022,.355,coat_mat)
for i,z in enumerate([1.38,1.29,1.20,1.11]):
 center,w=chest_point(-.007,z,True);center.y-=.008
 points=[center]+[center+Vector((math.cos(a)*.0075,-.003,math.sin(a)*.0075)) for a in [2*math.pi*k/12 for k in range(12)]]
 surface('COAT_Remy_Button_'+str(i+1),points,[(0,k+1,(k+1)%12+1) for k in range(12)],button_mat,[w]*len(points))

for obj in scene.objects:obj.select_set(False)
for obj in originals+garments:obj.select_set(True)
bpy.context.view_layer.objects.active=arm
if arm.animation_data:
 arm.animation_data.action=None
 for track in arm.animation_data.nla_tracks:track.mute=False
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.export_scene.gltf(filepath=str(TARGET),export_format='GLB',use_selection=True,export_yup=True,
 export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',export_lights=False,
 export_cameras=False,export_extras=True,export_image_format='AUTO')
assert sha(SOURCE)==source_hash and sha(OLD)==old_hash
record={'id':'COSTUME_Remy_Senac_20261013','baseId':'CHR_Remy_Mixamo_20261005','date':'2026-10-13',
 'source':str(SOURCE),'sourceSha256':source_hash,'sourcePreserved':True,'previousDerivativePreserved':True,
 'previousDerivativeSha256':old_hash,'url':'/assets/characters/'+TARGET.name,'blend':str(BLEND),
 'sha256':sha(TARGET),'bytes':TARGET.stat().st_size,'quality':'skinned fitted prototype',
 'method':'Continuous radial coat expansion, thigh-aware hem weights, original knee/elbow surfaces, preserved original clothes and genuine skeletal clips.',
 'replacedMeshes':['Tops001','Bottoms001'],'original2dReferences':references['files'],
 'garments':[{'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),
  'weightedVertices':sum(bool(v.groups) for v in o.data.vertices)} for o in garments],
 'limits':['No physical cloth simulation; seated coat hem uses FK/thigh weights.','The preserved source contains large embedded textures; optimization is deferred.']}

# Independently reimport the actual exported file and verify the garment skin.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET))
scene=bpy.context.scene;arm=next(o for o in scene.objects if o.type=='ARMATURE')
actual=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('COAT_','SCRUB_'))]
assert len(actual)==len(garments)
assert all(all(v.groups for v in o.data.vertices) for o in actual)
assert all(any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers) for o in actual)
record.update(reimportValidated=True,bones=len(arm.data.bones),garmentMeshes=len(actual),
 clips=[t.name for t in arm.animation_data.nla_tracks] if arm.animation_data else [])
for o in scene.objects:
 if o.name.startswith(('Tops','Bottoms')):o.hide_render=True
 if o.name.startswith('SCRUB_') and 'Trouser' not in o.name:o.hide_render=True
if arm.animation_data:
 arm.animation_data.action=None
 for track in arm.animation_data.nla_tracks:track.mute='Idle' not in track.name
scene.frame_set(1)
scene.world=bpy.data.worlds.new('UniformWorld');scene.world.color=(.18,.18,.18)
for loc,power in [((2,-3,3),450),((-2,-2,2.5),250)]:
 bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.size=4
bpy.ops.object.camera_add(location=(1.4,-4,1.65));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=2.15;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.filepath=str(ROOT/'reports/costumes/remy_senac_uniform_20261013.png')
bpy.ops.render.render(write_still=True);record['preview']=scene.render.filepath
REPORT.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('UNIFORM_COMPLETE '+json.dumps({'path':str(TARGET),'report':str(REPORT),'bones':record['bones'],'garments':len(actual),'clips':record['clips']},ensure_ascii=False))
