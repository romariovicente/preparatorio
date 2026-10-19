"""Recover saved rigs and assemble a colored, editable project with organized asset scenes."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
records=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
rigs={r['id']:r for r in json.loads((ROOT/'frontend/src/config/riggedAssets.json').read_text(encoding='utf-8'))}

def mat(name,color):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=.65
 return m
navy=mat('PREP_Navy',(.025,.09,.13));teal=mat('PREP_Teal',(.03,.38,.40));ivory=mat('PREP_Ivory',(.72,.78,.75));gold=mat('PREP_Gold',(.85,.49,.12))
def box(scene,col,name,loc,size,material):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.data.materials.append(material);return o

def lighting(scene,span,center):
 scene.world=bpy.data.worlds.new(scene.name+'_World');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.25,.35,.45,1);next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.7
 bpy.ops.object.light_add(type='SUN',location=(0,0,20));bpy.context.object.rotation_euler=(.5,-.3,-.4);bpy.context.object.data.energy=2
 bpy.ops.object.camera_add(location=Vector(center)+Vector((.6,-1,.9))*span);camera=bpy.context.object;camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=span*1.3;camera.data.clip_end=3000;scene.camera=camera
 scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100

def import_asset(scene,record,col,loc,extent=5,height=None):
 before=set(scene.objects);imgs=set(bpy.data.images)
 chosen=rigs.get(record['id'],record)
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/chosen['url'].lstrip('/')))
 bpy.context.view_layer.update()
 objects={o for o in set(scene.objects)-before if not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)}
 root=bpy.data.objects.new(record['id']+'_ROOT',None);col.objects.link(root)
 pts=[o.matrix_world@Vector(v) for o in objects if o.type=='MESH' for v in o.bound_box]
 lo=Vector([min(v[k] for v in pts) for k in range(3)]);hi=Vector([max(v[k] for v in pts) for k in range(3)]);center=(lo+hi)/2;center.z=lo.z
 factor=height/max(.001,hi.z-lo.z) if height else extent/max(.001,max(hi-lo))
 for o in objects:
  if o.parent not in objects:world=o.matrix_world.copy();o.parent=root;o.matrix_world=world
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o)
  if o.type=='MESH':
   if not o.data.materials:o.data.materials.append(teal);o['material_note']='Provisional color: no source material'
   if not any(m.type=='ARMATURE' for m in o.modifiers) and len(o.data.polygons)>50000:
    bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('PREP_Display_Proxy','DECIMATE');mod.ratio=35000/sum(len(p.vertices)-2 for p in o.data.polygons)
    bpy.ops.object.modifier_apply(modifier=mod.name)
 root.matrix_world=Matrix.Translation(loc)@Matrix.Scale(factor,4)@Matrix.Translation(-center)
 root['source_id']=record['id'];root['credits']=json.dumps(record['credits'],ensure_ascii=False);root['status']=chosen.get('notes','Original supplied model; display scale only')
 for image in set(bpy.data.images)-imgs:
  if image.type=='IMAGE' and image.size[0]:
   scale=min(1,512/max(image.size))
   if scale<1:image.scale(max(1,int(image.size[0]*scale)),max(1,int(image.size[1]*scale)))
   image.pack()
 # Original action tracks are kept; activate a single clip for the timeline.
 for o in objects:
  if o.animation_data:
   tracks=list(o.animation_data.nla_tracks)
   for j,t in enumerate(tracks):t.mute=j!=0
 if record['category'] in ['Veículos','Naves'] and not record.get('animated'):
  rest=root.location.copy()
  for f,d in [(1,0),(45,.3),(90,0)]:
   root.location=rest+Vector((0,0,d) if record['category']=='Naves' else (0,d,0));root.keyframe_insert(data_path='location',frame=f)
  root['animation_note']='Rigid presentation motion; not vehicle physics or wheel rig'
 return root

def gallery(category,items):
 name='ACERVO_'+category.upper().replace('Í','I').replace('Á','A').replace('Ó','O')
 scene=bpy.data.scenes.new(name);bpy.context.window.scene=scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 setcol=bpy.data.collections.new(name+'_APRESENTACAO');scene.collection.children.link(setcol)
 cols=4;rows=math.ceil(len(items)/cols);width=cols*8;depth=rows*9
 box(scene,setcol,'Piso',(12,(rows-1)*4.5,-.25),(width+2,depth+2,.25),navy)
 for i,r in enumerate(items):
  x=(i%cols)*8;y=(i//cols)*9
  col=bpy.data.collections.new(r['id']);scene.collection.children.link(col)
  box(scene,setcol,'Base_'+r['id'],(x,y,-.05),(6.6,6.6,.12),ivory)
  import_asset(scene,r,col,(x,y,.02),extent=5.5,height=2 if category=='Personagens' else None)
  curve=bpy.data.curves.new('Label_'+r['id'],'FONT');curve.body=r['name'][:45];curve.size=.21;curve.align_x='CENTER';curve.materials.append(gold)
  label=bpy.data.objects.new('Label_'+r['id'],curve);setcol.objects.link(label);label.location=(x,y-3.6,.03)
 scene.frame_start=1;scene.frame_end=90;scene.frame_set(1);lighting(scene,max(width,depth),(12,(rows-1)*4.5,0))
 scene['navigation']='Choose a scene from the top scene selector. Each model has its own collection and root.'
 scene.render.filepath=str(ROOT/'reports'/('ACERVO_'+category+'.png'));bpy.ops.render.render(write_still=True)
 # Each category is a recoverable checkpoint even before master assembly completes.
 dest=ROOT/'art/blender'/('ACERVO_'+category+'_20261002.blend');bpy.data.libraries.write(str(dest),{scene},fake_user=True,compress=True)
 return scene

for category in dict.fromkeys(r['category'] for r in records):
 gallery(category,[r for r in records if r['category']==category])
print('Organized',len(records),'models')
