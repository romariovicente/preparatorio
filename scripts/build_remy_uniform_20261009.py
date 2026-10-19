"""Derive a fitted uniform from Remy's human garment topology and skin weights.

The supplied PNG mockups are references, not imported 3D clothes. Identity PNGs
are copied verbatim and used as transparent, skinned embroidery surfaces.
This script is safe to run in a fresh Blender background process only.
"""
import bpy,json,hashlib,shutil,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb'
TARGET=ROOT/'frontend/public/assets/characters/CHR_Remy_Senac_Uniform_20261009.glb'
REPORT=ROOT/'reports/costumes/remy_senac_uniform_20261009.json'
REFERENCES=Path(r'C:\Users\Senac\Downloads\NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode\Tudo pra colocar no jogo\Fardamentos e Jaleco')
IDENTITY=ROOT/'frontend/public/assets/uniforms/senac_20261009'
IDENTITY.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=sha(SOURCE)
mapping=[
 ('senac-logo.png','file_0000000019f8820e83f4b2b6bf3519f4.png','identity-logo'),
 ('jaleco-reference.png','file_000000004438820e8fd03848b8884c5e.png','reference-coat'),
 ('polo-reference-a.png','file_000000008de0820e92410ebffc030cf6.png','reference-polo'),
 ('romario-lettering-reference.png','file_00000000a254820ebef4f77ffb58a176.png','reference-lettering'),
 ('polo-reference-b.png','file_00000000cbec820ea88cce5e10e5ba7f.png','reference-polo'),
 ('nursing-crest.png','file_00000000e158820e8735fc17ca6766cc.png','identity-crest'),
 ('crest-with-romario-reference.png','file_00000000f450820ebd846b9e5dd0ec4c.png','reference-composite'),
]
refs=[]
for name,old,role in mapping:
 src=REFERENCES/old;dst=IDENTITY/name;shutil.copyfile(src,dst)
 assert sha(src)==sha(dst)
 refs.append({'name':name,'sourceFile':old,'role':role,'url':'/assets/uniforms/senac_20261009/'+name,'sha256':sha(src),'bytes':src.stat().st_size,'sourcePreserved':True})
(ROOT/'frontend/src/config/uniformReferences.json').write_text(json.dumps({'id':'senac_nursing_20261009','name':'Senac · Técnico de Enfermagem','kind':'supplied-2d-reference','files':refs,'wearableCostumeId':'COSTUME_Remy_Senac_20261009','note':'Mockups orientam a modelagem. Marca e brasão originais entram sem edição; nome de cada jogador é gerado em tempo real.'},ensure_ascii=False,indent=2),encoding='utf-8')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
top=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Tops'))
body=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('Body'))
original_objects=[o for o in scene.objects if o.type in ('MESH','ARMATURE','EMPTY')]
# The importer creates an unlinked bone-display icosphere; it is never exported.
original_objects=[o for o in original_objects if o.name!='Icosphere']

def fabric(name,color):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.85
 return mat
scrub_mat=fabric('SCRUB_Remy_Cotton',(1,1,1));coat_mat=fabric('COAT_Remy_Cotton',(.92,.94,.96))
garments=[]

def copied_garment(src,name,mat):
 obj=src.copy();obj.data=src.data.copy();obj.name=name;scene.collection.objects.link(obj)
 obj.data.materials.clear();obj.data.materials.append(mat)
 for face in obj.data.polygons:face.material_index=0
 garments.append(obj);return obj

scrub=copied_garment(top,'SCRUB_Remy_Shirt',scrub_mat)
coat=copied_garment(top,'COAT_Remy_FittedShell',coat_mat)
for obj,expansion in [(scrub,.003),(coat,.016)]:
 matrix=obj.matrix_world.copy();inverse=matrix.inverted();normal_matrix=matrix.to_3x3().inverted().transposed()
 for vertex in obj.data.vertices:
  point=matrix@vertex.co;normal=(normal_matrix@vertex.normal).normalized()
  point+=normal*expansion
  if obj==coat and point.z<1.14 and abs(point.x)<.235:
   # A thigh-length fitted shell uses the shirt's existing human surface,
   # with continuous torso/hips skin weights instead of bone rigid boxes.
   point.z=1.14+(point.z-1.14)*1.9
   point.x*=1.07
  vertex.co=inverse@point
 obj.data.update()

def skinned_surface(name,points,faces,mat,weights,uvs=None):
 mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(points,[],faces);mesh.update()
 obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
 obj.parent=arm;obj.matrix_world=body.matrix_world.copy()
 mesh.materials.append(mat)
 for old in body.vertex_groups:obj.vertex_groups.new(name=old.name)
 for i,vertex_weights in enumerate(weights):
  for group,weight in vertex_weights:
   if weight>.00001:obj.vertex_groups[group].add([i],weight,'REPLACE')
 modifier=obj.modifiers.new('Remy_Original_Skin','ARMATURE');modifier.object=arm
 if uvs:
  layer=mesh.uv_layers.new(name='Uniform_UV')
  for face in mesh.polygons:
   for loop in face.loop_indices:layer.data[loop].uv=uvs[mesh.loops[loop].vertex_index]
 for polygon in mesh.polygons:polygon.use_smooth=True
 garments.append(obj);return obj

# Sleeves use real arm topology and real weighted elbow deformation from Remy.
# They are fitted anatomical garment surfaces, not cylinder approximations.
arm_groups={g.index for g in body.vertex_groups if g.name.endswith(('LeftArm','RightArm','LeftForeArm','RightForeArm'))}
world=[body.matrix_world@v.co for v in body.data.vertices]
eligible={v.index for v in body.data.vertices if .29<abs(world[v.index].x)<.80 and sum(g.weight for g in v.groups if g.group in arm_groups)>.78}
faces=[tuple(p.vertices) for p in body.data.polygons if all(i in eligible for i in p.vertices)]
used=sorted({i for face in faces for i in face});indices={old:i for i,old in enumerate(used)}
normal_matrix=body.matrix_world.to_3x3().inverted().transposed();inverse=body.matrix_world.inverted()
points=[inverse@(world[i]+(normal_matrix@body.data.vertices[i].normal).normalized()*.017) for i in used]
weights=[[(g.group,g.weight) for g in body.data.vertices[i].groups] for i in used]
sleeves=skinned_surface('COAT_Remy_LongSleeves',points,[tuple(indices[i] for i in face) for face in faces],coat_mat,weights)

# Sample the original shirt surface to fit embroidery to the chest curvature.
tree=KDTree(len(top.data.vertices))
top_world=[top.matrix_world@v.co for v in top.data.vertices]
for i,p in enumerate(top_world):tree.insert(p,i)
tree.balance()

def embroidery_material(name,path=None):
 mat=fabric(name,(1,1,1));p=mat.node_tree.nodes.get('Principled BSDF')
 mat.surface_render_method='DITHERED';mat.use_backface_culling=False
 if path:
  texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(path),check_existing=True)
  mat.node_tree.links.new(texture.outputs['Color'],p.inputs['Base Color']);mat.node_tree.links.new(texture.outputs['Alpha'],p.inputs['Alpha'])
 else:p.inputs['Alpha'].default_value=0
 return mat

def chest_patch(name,cx,cz,width,height,mat,coat=False):
 points=[];weights=[];uvs=[];nx,ny=8,8
 for row in range(ny+1):
  for col in range(nx+1):
   x=cx+(col/nx-.5)*width;z=cz+(row/ny-.5)*height
   # Negative Blender Y is the front of Remy. Neighbours are constrained to
   # the front so a nearest rear/arm vertex cannot fold a chest patch inward.
   candidates=tree.find_n(Vector((x,-.15,z)),20)
   front=[(dist,i,p) for p,i,dist in candidates if p.y<.005 and abs(p.x-x)<.055]
   _,index,_=min(front,key=lambda item:item[0]) if front else (candidates[0][2],candidates[0][1],candidates[0][0])
   y=top_world[index].y-(.025 if coat else .009)
   points.append(body.matrix_world.inverted()@Vector((x,y,z)))
   weights.append([(g.group,g.weight) for g in top.data.vertices[index].groups]);uvs.append((col/nx,row/ny))
 faces=[(r*(nx+1)+c,r*(nx+1)+c+1,(r+1)*(nx+1)+c+1,(r+1)*(nx+1)+c) for r in range(ny) for c in range(nx)]
 return skinned_surface(name,points,faces,mat,weights,uvs)

crest=embroidery_material('Uniform_NursingCrest',IDENTITY/'nursing-crest.png')
logo=embroidery_material('Uniform_SenacLogo',IDENTITY/'senac-logo.png')
name_mat=embroidery_material('Uniform_PlayerName_Runtime')
for prefix,is_coat in [('COAT',True),('SCRUB',False)]:
 chest_patch(prefix+'_BRAND_Remy_Crest',-.094,1.345,.105,.118,crest,is_coat)
 chest_patch(prefix+'_BRAND_Remy_Senac',.101,1.405,.076,.078,logo,is_coat)
 chest_patch(prefix+'_NAME_Remy_Player',.078,1.313,.15,.061,name_mat,is_coat)

# Keep the original top in the preserved source file. The wearable export uses
# the fitted shirt/coat variants so two opaque shirts do not occupy one surface.
export_objects=[o for o in original_objects if o!=top]+garments
for obj in scene.objects:obj.select_set(False)
for obj in export_objects:obj.select_set(True)
bpy.context.view_layer.objects.active=arm
if arm.animation_data:
 arm.animation_data.action=None
 for track in arm.animation_data.nla_tracks:track.mute=False
scene.frame_set(1)
bpy.ops.export_scene.gltf(filepath=str(TARGET),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',export_lights=False,export_cameras=False,export_extras=True,export_image_format='AUTO')
assert sha(SOURCE)==source_hash

record={'id':'COSTUME_Remy_Senac_20261009','date':'2026-10-09','source':str(SOURCE),'sourceSha256':source_hash,'sourcePreserved':True,'url':'/assets/characters/'+TARGET.name,'sha256':sha(TARGET),'bytes':TARGET.stat().st_size,'method':'Existing human shirt topology, extended fitted hem, anatomical sleeves and original skin weights; surface embroidery uses byte-identical supplied PNGs. Player name is a runtime CanvasTexture on a weighted garment patch.','quality':'fitted prototype; not a finished tailoring simulation','original2dReferences':refs,'garments':[{'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'uvLayers':len(o.data.uv_layers),'weightedVertices':sum(bool(v.groups) for v in o.data.vertices),'maxInfluences':max((len(v.groups) for v in o.data.vertices),default=0)} for o in garments]}

# Independent reimport verifies skin connectivity and the actual exported asset.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET))
scene=bpy.context.scene;arm=next(o for o in scene.objects if o.type=='ARMATURE')
actual=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('COAT_','SCRUB_'))]
assert len(actual)==len(garments)
assert all(all(v.groups for v in o.data.vertices) for o in actual)
assert all(any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers) for o in actual)
record.update(reimportValidated=True,bones=len(arm.data.bones),reimportGarmentMeshes=len(actual),clips=[t.name for t in arm.animation_data.nla_tracks] if arm.animation_data else [])
for o in scene.objects:
 if o.name.startswith('SCRUB_'):o.hide_render=True
if arm.animation_data:
 for track in arm.animation_data.nla_tracks:track.mute='Idle' not in track.name
scene.frame_set(1)
scene.world=bpy.data.worlds.new('UniformWorld');scene.world.color=(.18,.18,.18)
for loc,power in [((2,-3,3),450),((-2,-2,2.5),250)]:
 bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.size=4
bpy.ops.object.camera_add(location=(1.4,-4,1.65));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.9))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.15;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.filepath=str(ROOT/'reports/costumes/remy_senac_uniform_20261009.png')
bpy.ops.render.render(write_still=True)
record['preview']=scene.render.filepath
REPORT.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'complete','path':str(TARGET),'report':str(REPORT),'bones':record['bones'],'garments':len(actual),'clips':record['clips']},ensure_ascii=False))
