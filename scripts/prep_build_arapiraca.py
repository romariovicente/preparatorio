"""Additive, metre-based Arapiraca cyberpunk prototype. Run only inside Blender MCP.

Geography is a fictional compression of the visually inspected AL-220/HEA layout,
not a cadastral copy. New object transforms are defined before parenting. Existing
scenes, source models, armatures, materials and pivots are never rewritten.
"""
import bpy, math, json, hashlib, os
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'frontend/public/assets/cyber'
PUBLIC.mkdir(parents=True,exist_ok=True)
REPORT=ROOT/'reports'
NAME='00_ARAPIRACA_CYBER_20261005'
if bpy.data.scenes.get(NAME): raise RuntimeError('Scene already exists. Preserve it; inspect before any rerun.')
scene=bpy.data.scenes.new(NAME);bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.fps=60;scene.frame_start=1;scene.frame_end=7201
scene['author']='Romario Vicente Amaro'
scene['geography']='Fictional Arapiraca: HEA north of diagonal AL-220; inland city. Marine and forest areas are portal biomes.'
scene['reference_latitude']=-9.7348704;scene['reference_longitude']=-36.6498059
scene['traffic_status']='Prototype based on CTB/CONTRAN references; not a certified civil traffic design.'
cols={}
def col(name,sc=scene):
 c=bpy.data.collections.new('ARAP_'+name);sc.collection.children.link(c);cols[name]=c;return c
ground=col('01_TERRAIN');roads=col('02_ROADS_BIKE_LANES');buildings=col('03_BUILDINGS')
science=col('04_KNOWLEDGE_LAB');props=col('05_PUBLIC_PROPS');farm=col('06_FARM')
transit=col('07_TRANSIT');sky=col('08_HELIOCENTRIC_CLOCK');npcs=col('09_NPCS');lighting=col('10_CAMERAS_LIGHTS')
M={}
def material(key,color,metal=0,rough=.65,emission=0):
 m=bpy.data.materials.new('MAT_ARAP_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1)
 b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emission
 M[key]=m;return m
for args in [('navy',(.012,.024,.055),.45,.4,0),('concrete',(.20,.24,.32),.05,.8,0),('ivory',(.72,.83,.84),.1,.5,0),('glass',(.025,.22,.32),.6,.25,0),('cyan',(.02,.8,1),.25,.25,3),('magenta',(.95,.015,.45),.2,.25,3),('gold',(1,.5,.055),.25,.35,1),('asphalt',(.035,.042,.060),0,.96,0),('white',(.91,.94,.93),0,.6,0),('yellow',(1,.73,.04),0,.7,0),('bike_red',(.48,.025,.03),0,.8,0),('red',(.8,.025,.035),0,.5,2),('green',(.015,.55,.12),0,.5,2),('earth',(.24,.12,.065),0,.95,0),('foliage',(.04,.26,.13),0,.95,0),('water',(.02,.19,.27),.25,.3,0),('purple',(.26,.08,.50),.3,.4,.4),('skin',(.44,.23,.15),0,.75,0),('bronze',(.44,.24,.09),.75,.35,0)]:material(*args)
# Small procedural micro-detail stays in the .blend; uniform PBR colors export
# portably to glTF without pretending that Noise nodes are baked textures.
for key in ['concrete','earth','asphalt']:
 m=M[key];noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=32
 bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.1;bump.inputs['Distance'].default_value=.015
 m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Normal'])

def xyz(p):return (p[0],-p[2],p[1]) # Three Y-up plan -> Blender Z-up
def adopt(o,name,c,mat):
 o.name=name
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o)
 if mat:o.data.materials.append(M[mat] if isinstance(mat,str) else mat)
 o['prep_author']='Romario Vicente Amaro';return o
def box(name,p,size,mat='navy',c=buildings):
 bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(p));o=adopt(bpy.context.object,name,c,mat)
 # Dimensions in Y-up, applied only on freshly generated independent mesh.
 o.scale=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 return o
def cylinder(name,p,r,d,mat='concrete',c=props,vertices=12):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d,location=xyz(p));return adopt(bpy.context.object,name,c,mat)
def sphere(name,p,r,mat='cyan',c=props,scale=(1,1,1),sub=1):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=r,location=xyz(p));o=adopt(bpy.context.object,name,c,mat);o.scale=(scale[0],scale[2],scale[1]);return o
def cone(name,p,r1,r2,d,mat='foliage',c=props):
 bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=r1,radius2=r2,depth=d,location=xyz(p));return adopt(bpy.context.object,name,c,mat)
def text(name,body,p,size=.6,mat='cyan',c=props,standing=True):
 cu=bpy.data.curves.new(name+'_font','FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.extrude=.012
 o=bpy.data.objects.new(name,cu);c.objects.link(o);o.location=xyz(p)
 if standing:o.rotation_euler=(math.pi/2,0,0)
 cu.materials.append(M[mat]);return o
def segment(name,a,b,width,height,mat='concrete',c=roads):
 aa=Vector(xyz(a));bb=Vector(xyz(b));delta=bb-aa
 o=box(name,((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2),(width,height,delta.length),mat,c)
 o.rotation_euler=delta.to_track_quat('Y','Z').to_euler();return o
def ring(name,p,r,thick=.22,mat='cyan',c=science,vertical=False):
 bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=6,location=xyz(p),major_radius=r,minor_radius=thick)
 o=adopt(bpy.context.object,name,c,mat)
 if vertical:o.rotation_euler[0]=math.pi/2
 return o
def root_obj(name,c):
 o=bpy.data.objects.new(name,None);c.objects.link(o);return o
def parent_all(objects,root):
 for o in objects:
  if o!=root and not o.parent:mx=o.matrix_world.copy();o.parent=root;o.matrix_world=mx
def keyed_cycle(o,points,frames,rotations=None):
 for i,(p,f) in enumerate(zip(points,frames)):
  o.location=xyz(p);o.keyframe_insert(data_path='location',frame=f)
  if rotations:o.rotation_euler[2]=-rotations[i];o.keyframe_insert(data_path='rotation_euler',frame=f)
 if o.animation_data and o.animation_data.action:
  o.animation_data.action.name=o.name+'_Route'
  slot=o.animation_data.action_slot
  for layer in o.animation_data.action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for fc in bag.fcurves:
      for k in fc.keyframe_points:k.interpolation='LINEAR'
      fc.modifiers.new('CYCLES')

box('ENV_ARAP_Base',(0,-.5,0),(260,1,260),'earth',ground)
box('ENV_ARAP_UrbanPlate',(0,-.03,-12),(218,.08,194),'concrete',ground)
box('ENV_ARAP_SeaPortal',(133,-.1,0),(32,.1,90),'water',ground)
for i in range(8):box('ENV_ARAP_Shore_'+str(i),(113+i*.9,.05,-40+i*10),(7,.15,9),'gold',ground)

# Road corridors with reserved red cycle lanes, white lane boundaries, opposing
# yellow centre markings, distinct sidewalk and stop/crosswalk markings.
road_axes=[((-115,-80),(113,58),'AL220_HEA_AXIS'),((-106,35),(108,35),'EAST_WEST'),((-106,-75),(108,-75),'NORTH_ACCESS'),((-106,80),(108,80),'SOUTH_ACCESS'),((-80,-108),(-80,115),'WEST_COLLECTOR'),((35,-108),(35,115),'EAST_COLLECTOR'),((105,-108),(105,115),'OUTER_COLLECTOR')]
for (ax,az),(bx,bz),rid in road_axes:
 a=Vector((ax,az));b=Vector((bx,bz));d=b-a;normal=Vector((-d.y,d.x)).normalized();length=d.length;unit=d.normalized()
 segment('ROAD_'+rid,(ax,.08,az),(bx,.08,bz),12,.14,'asphalt')
 for side in [-1,1]:
  for off,w,mat in [(7.3,2,'bike_red'),(6.15,.15,'white'),(8.45,.15,'white'),(9.75,2.3,'concrete')]:
   p=a+normal*(off*side);q=b+normal*(off*side);segment('ROAD_'+rid+'_'+mat+'_'+str(side),(p.x,.19,p.y),(q.x,.19,q.y),w,.08,mat)
  # White same-direction margins and yellow opposing-direction centre lines.
  p=a+normal*.18*side;q=b+normal*.18*side;segment('ROAD_'+rid+'_Centre_'+str(side),(p.x,.17,p.y),(q.x,.17,q.y),.1,.035,'yellow')
 for n in range(12,int(length)-12,18):
  mid=a+unit*n
  for side in [-1,1]:
   p=mid+normal*(7.3*side)
   symbol=text('CYCLE_'+rid+'_'+str(n)+'_'+str(side),'BIKE',(p.x,.245,p.y),.46,'white',roads,False)
   symbol.rotation_euler[2]=math.atan2(-d.x,-d.y)
 for n in range(20,int(length)-15,30):
  p=a+unit*n+normal*11.3
  cylinder('LAMP_'+rid+'_'+str(n),(p.x,3.5,p.y),.16,7,'navy',props)
  box('LAMP_'+rid+'_Beam_'+str(n),(p.x,7,p.y),(2.8,.15,.4),'cyan',props)

def crosswalk(x,z,axis='x'):
 for i in range(9):
  size=(.6,.025,7.8) if axis=='x' else (7.8,.025,.6)
  p=(x+(i-4)*.9,.28,z) if axis=='x' else (x,.28,z+(i-4)*.9)
  box('MARK_Zebra_'+str(x)+'_'+str(z)+'_'+str(i),p,size,'white',roads)
 stop=box('MARK_Stop_'+str(x)+'_'+str(z),(x-5,.3,z),( .3,.025,5.6),'white',roads)
 return stop
for junction,(x,z) in enumerate([(-80,35),(35,35),(105,35),(-80,-75),(35,-75),(105,80)]):
 crosswalk(x+12,z);crosswalk(x,z+12,'z')
 for axis,dx,dz in [('NS',-9,-9),('EW',9,9)]:
  cylinder('TRAFFIC_Pole',(x+dx,2.8,z+dz),.13,5.6,'navy',roads)
  box('TRAFFIC_Housing',(x+dx,5,z+dz),(.65,1.8,.42),'navy',roads)
  for j,(signal,mat) in enumerate([('R','red'),('Y','yellow'),('G','green')]):
   # Initial phase NS green/EW red; runtime updates individual cloned materials.
   enabled=(axis=='NS' and signal=='G') or (axis=='EW' and signal=='R')
   name='MAT_SIGNAL_J'+str(junction)+'_'+axis+'_'+signal
   m=material(name,tuple(M[mat].diffuse_color[:3]),0,.5,3 if enabled else 0)
   if not enabled:next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.015,.02,.025,1)
   sphere('TRAFFIC_J'+str(junction)+'_'+axis+'_'+signal,(x+dx,5.6-j*.55,z+dz+.25),.20,m,roads)
  box('TRAFFIC_PedestrianHousing',(x+dx+1,2.5,z+dz),(.5,1,.3),'navy',roads)
  for j,(signal,mat) in enumerate([('R','red'),('G','green')]):
   enabled=signal=='R'
   m=material('MAT_PED_J'+str(junction)+'_'+axis+'_'+signal,tuple(M[mat].diffuse_color[:3]),0,.5,3 if enabled else 0)
   if not enabled:next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.015,.02,.025,1)
   sphere('TRAFFIC_J'+str(junction)+'_PED_'+axis+'_'+signal,(x+dx+1,2.75-j*.5,z+dz+.18),.14,m,roads)
 # PCD curb ramps: shallow sloped plane, clear landing; exact accessibility
 # dimensions still require a civil design review before a real-world claim.
 for sx in [-1,1]:
  o=box('SIDEWALK_Ramp_PCD',(x+sx*10,.3,z+14),(2,.18,2.2),'ivory',roads);o.rotation_euler[0]=-.07
  box('SIDEWALK_Tactile',(x+sx*10,.42,z+15),(1.8,.04,.6),'yellow',roads)
def sign(p,kind):
 x,y,z=p;cylinder('SIGN_Pole_'+kind,(x,1.4,z),.06,2.8,'navy',roads)
 if kind=='PARE':
  o=cylinder('SIGN_R1_STOP',(x,2.8,z),.5,.07,'red',roads,8);o.rotation_euler[0]=math.pi/2
  text('SIGN_StopText','PARE',(x,2.63,z+.06),.23,'white',roads)
 elif kind=='30':
  o=cylinder('SIGN_R19',(x,2.8,z),.5,.07,'red',roads,24);o.rotation_euler[0]=math.pi/2
  q=cylinder('SIGN_R19_White',(x,2.8,z+.05),.4,.075,'white',roads,24);q.rotation_euler[0]=math.pi/2
  text('SIGN_SpeedText','30',(x,2.65,z+.1),.32,'asphalt',roads)
 elif kind=='BIKE':
  o=cylinder('SIGN_R34_CycleExclusive',(x,2.8,z),.48,.07,'red',roads,24);o.rotation_euler[0]=math.pi/2
  q=cylinder('SIGN_R34_White',(x,2.8,z+.05),.40,.075,'white',roads,24);q.rotation_euler[0]=math.pi/2
  for xx in [-.18,.18]:ring('SIGN_R34_BikeWheel',(x+xx,2.7,z+.10),.115,.012,'asphalt',roads,True)
  for a,b in [((-.18,2.7),(0,2.9)),((0,2.9),(.18,2.7)),((-.18,2.7),(.10,2.7)),((.10,2.7),(0,2.9)),((.18,2.7),(.13,3.0))]:
   segment('SIGN_R34_BikeFrame',(x+a[0],a[1],z+.11),(x+b[0],b[1],z+.11),.02,.02,'asphalt',roads)
 else:
  box('SIGN_Info_'+kind,(x,2.8,z),(1.6,.8,.09),'navy',roads);text('SIGN_InfoText',kind,(x,2.63,z+.08),.17,'white',roads)
for p,k in [((-67,0,47),'PARE'),((24,0,-63),'PARE'),((-105,0,22),'30'),((95,0,12),'30'),((49,0,49),'BIKE'),((-66,0,58),'BIKE'),((8,0,49),'ONIBUS'),((-65,0,-38),'ESTACAO'),((23,0,-33),'HOSPITAL')]:sign(p,k)

def facade(name,x,z,w,d,h,signage,c=buildings):
 box(name+'_Foundation',(x,.35,z),(w+2,.6,d+2),'navy',c)
 box(name+'_Core',(x,h/2+.6,z),(w,h,d),'concrete',c)
 box(name+'_Roof',(x,h+.7,z),(w+1,.5,d+1),'navy',c)
 front=z+d/2+.04
 for yy in range(2,int(h)-1,3):
  for xx in range(int(-w/2+2),int(w/2-1),4):
   box(name+'_Window',(x+xx,yy+.6,front),(2.9,1.6,.1),'glass',c)
   box(name+'_WindowLight',(x+xx,yy-.22,front+.05),(3,.06,.08),'cyan',c)
 box(name+'_Portal',(x,2.1,front+.4),(3,3,.35),'glass',c)
 box(name+'_Canopy',(x,4.2,front+2),(8,.35,4),'magenta',c)
 text(name+'_Title',signage,(x,h+1.5,front+.08),min(1,w/max(10,len(signage))),'cyan',c)
 return front

# HEA reference: long campus north of the regional diagonal artery, access
# canopy, ambulance approach, annexes and enclosed internal teaching ward.
front=facade('BLD_PREP_Emergency_HEA_Concept',48,-38,36,27,11,'PREP | EMERGENCIA')
facade('BLD_PREP_HEA_Annex',48,-59,26,10,6,'ENSINO • TRIAGEM')
for x in [32,64]:box('BLD_HEA_Accent',(x,7,-23.8),(.5,10,.5),'magenta',buildings)
box('HEA_RedCross_Horizontal',(48,8,-23.4),(3,.7,.12),'red',buildings)
box('HEA_RedCross_Vertical',(48,8,-23.4),(.7,3,.14),'red',buildings)
# Hospital classroom and care stations visible as a separate open pavilion.
box('HEA_TrainingFloor',(51,.3,-12),(25,.35,9),'ivory',science)
for i in range(4):
 x=43+i*5;box('MED_Bed_'+str(i),(x,1,-12),(1.7,.5,3),'ivory',science)
 box('MED_Mattress_'+str(i),(x,1.4,-12),(1.6,.35,2.8),'cyan',science)
 box('MED_Monitor_'+str(i),(x,2.4,-14),(1.2,.8,.12),'navy',science)
 text('MED_MonitorData_'+str(i),'SIMULACAO',(x,2.3,-13.9),.13,'cyan',science)
facade('BLD_PREP_Laboratory',80,-38,23,24,10,'LAB | CRONOVITAE',science)
# Open ring accelerator plaza, with injector, magnets and protective railing.
box('LAB_AcceleratorDeck',(79,.4,-7),(24,.6,20),'navy',science)
ring('LAB_ParticleAccelerator',(79,1.8,-7),7.5,.65,'ivory',science)
ring('LAB_AcceleratorEnergy',(79,1.8,-7),7.5,.12,'cyan',science)
for i in range(12):
 a=i*math.tau/12;box('LAB_Dipole_'+str(i),(79+7.5*math.cos(a),1.8,-7+7.5*math.sin(a)),(1.7,1.4,1.4),'purple',science)
for i in range(6):box('LAB_Console_'+str(i),(69+i*3,1.2,4),(1.5,1.6,.8),'glass',science)
text('LAB_Warning','LABORATORIO DIDATICO | NAO CLINICO',(79,4,4.5),.55,'gold',science)

# Knowledge plaza, central stylized brain and language monuments.
cylinder('PLAZA_Base',(0,.15,0),21,.35,'navy',science,48)
for r in [8,17,20]:ring('PLAZA_LightRing',(0,.4,0),r,.08,'cyan',science)
cylinder('PLAZA_BrainPedestal',(0,1.5,0),4.5,3,'concrete',science,12)
for hemisphere in [-1,1]:
 sphere('PLAZA_BrainHemisphere',(hemisphere*1.8,7,0),4,'purple',science,(.7,.85,1.05),2)
 for j in range(10):
  a=j*math.tau/10;sphere('PLAZA_BrainFold',(hemisphere*(1.4+1.3*abs(math.sin(a))),7+2.3*math.cos(a),2.2*math.sin(a)),.8,'cyan' if j%3==0 else 'purple',science,(.85,1,.65),1)
text('PLAZA_Title','PRACA DO CONHECIMENTO',(0,1.5,9),1.1,'cyan',science)
for i,lang in enumerate(['JavaScript','Python','HTML','CSS','GLSL','JSON']):
 a=i*math.tau/6;x=14*math.cos(a);z=14*math.sin(a)
 cylinder('STAT_LanguageBase_'+lang,(x,1,z),2.3,2,'concrete',science,8)
 sphere('STAT_LanguageGem_'+lang,(x,4,z),1.6,'magenta' if i%2 else 'cyan',science,sub=1)
 text('STAT_LanguageText_'+lang,lang,(x,2.6,z+2.2),.45,'gold',science)
def nightingale(x,z,scale=1):
 c=props;cylinder('STAT_NightingaleBase',(x,.7,z),1.5*scale,1.4*scale,'navy',c,8)
 cone('STAT_NightingaleDress',(x,2.4*scale,z),1*scale,.42*scale,2.4*scale,'bronze',c)
 sphere('STAT_NightingaleHead',(x,4.05*scale,z),.43*scale,'bronze',c)
 segment('STAT_NightingaleArm',(x+.35*scale,3.3*scale,z),(x+1.1*scale,2.9*scale,z),.25*scale,.25*scale,'bronze',c)
 cylinder('STAT_NightingaleLamp',(x+1.1*scale,2.7*scale,z),.22*scale,.55*scale,'gold',c)
 text('STAT_NightingalePlaque','FLORENCE NIGHTINGALE',(x,.6,z+1.55*scale),.19*scale,'gold',c)
for x,z in [(-23,3),(22,-16),(24,-22),(-55,-32)]:nightingale(x,z)

facade('BLD_ItemShop',-45,25,20,15,8,'LOJA • JALecos & ITENS')
facade('BLD_MotoDealer',-46,53,21,17,7,'NEON MOTO | MOTOTAXI')
facade('BLD_CarDealer',67,57,24,22,8,'AUTOS • UTILITARIOS')
facade('BLD_HelicopterHangar',85,90,30,22,13,'HELIPORTO')
box('HANGAR_LargeDoor',(85,5,101.1),(21,9,.2),'glass',buildings)
ring('HANGAR_Helipad',(84,.25,72),9,.25,'yellow',ground)
text('HANGAR_H','H',(84,.28,72),8,'white',ground,False)
for i in range(9):
 x=-56+(i%3)*17;z=-30-(i//3)*19
 facade('BLD_Residential_'+str(i),x,z,11,12,5+(i%3)*3,'SETOR '+str(i+1))
# Basement elevator shaft is public. The creator home geometry is private.
box('LIFT_Entrance',(-17,3,56),(8,6,8),'navy',buildings)
box('LIFT_GlassSide',(-20,3,56),(.15,5.6,7),'glass',buildings)
for x in [-19.5,-14.5]:box('LIFT_Rail',(x,-3,56),(.14,14,.15),'cyan',buildings)
text('LIFT_Title','CASAS SUBTERRANEAS',(-17,6.5,60.1),.45,'cyan',buildings)
facade('BLD_UndergroundGallery',-20,61,28,12,5,'GALERIA SUBTERRANEA')

for i,(x,z) in enumerate([(-24,16),(17,18),(30,-16),(-65,-37),(74,71)]):
 box('TERM_Education_'+str(i),(x,1.6,z),(1.3,3,.7),'navy',science)
 box('TERM_Screen_'+str(i),(x,2.1,z+.4),(1.15,1.3,.1),'cyan',science)
 sphere('TERM_Hologram_'+str(i),(x,4,z),.65,'magenta',science)
 text('TERM_Label_'+str(i),'JARVIS | APRENDA',(x,3.2,z+.45),.2,'gold',science)
for i,(x,z) in enumerate([(-33,16),(-17,-9),(27,8),(65,-19)]):
 ring('TELEPORT_Ring_'+str(i),(x,.4,z),2.2,.2,'magenta',science)
 for dx in [-2,2]:box('TELEPORT_Pylon_'+str(i),(x+dx,2.3,z),(.4,4.5,.6),'cyan',science)
text('AUTHOR_Plaque','ROMARIO VICENTE AMARO | PREPARATORIO',(0,.8,21),.6,'gold',props)

# Digital billboard has a static portable body; its live synchronized screen is
# rendered by the game from sampleWorldClock, as is the smartphone UI.
for x in [-12,12]:box('BILLBOARD_Pillar',(x,7,25),(.6,14,.6),'navy',props)
box('BILLBOARD_Frame',(0,14,25),(28,9,1),'magenta',props)
box('BILLBOARD_Screen',(0,14,25.6),(26,7.6,.12),'navy',props)
text('BILLBOARD_Brand','CHRONOVITAE | JARVIS-IA',(0,15.8,25.8),1,'cyan',props)
text('BILLBOARD_Message','CONHECIMENTO • CULTURA • FUTURO',(0,12.8,25.8),.62,'gold',props)

# Parking stalls are integrated with the collector street, avoiding sidewalks.
parking=[]
for name,x,z in [('Hospital',15,-50),('Centro',-6,-44),('Hangar',96,63)]:
 box('PARK_'+name,(x,.17,z),(14,.12,18),'asphalt',ground)
 for i in range(4):
  sz=z-6+i*4
  box('PARK_Line_'+name,(x,.26,sz),(12,.03,.11),'white',roads)
  parking.append({'id':name+'-'+str(i),'position':[x,.1,sz+1.8],'size':[5,3.6]})
 text('PARK_Label_'+name,'P',(x,.27,z),3,'cyan',ground,False)

# Rail loop is a fictional futuristic transport line, not a claim that a real
# present-day passenger service operates this route in Arapiraca.
railpoints=[(-95,-103),(102,-103),(117,-88),(117,92),(100,114),(-97,114),(-115,96),(-115,-85),(-95,-103)]
for j,(a,b) in enumerate(zip(railpoints,railpoints[1:])):
 av=Vector(a);bv=Vector(b);d=bv-av;n=Vector((-d.y,d.x)).normalized()
 for side in [-1,1]:
  p=av+n*.75*side;q=bv+n*.75*side;segment('RAIL_'+str(j)+'_'+str(side),(p.x,.4,p.y),(q.x,.4,q.y),.1,.15,'ivory',transit)
 for k in range(int(d.length/2)):
  p=av+d.normalized()*k*2;o=box('RAIL_Sleeper',(p.x,.2,p.y),(2.4,.15,.25),'navy',transit);o.rotation_euler[2]=math.atan2(-d.x,-d.y)
facade('BLD_Station',-70,-88,27,16,7,'ARAPIRACA | TREM FUTURISTA',transit)
box('STATION_Approach',(-70,.22,-59),(20,.25,36),'concrete',ground)
box('STATION_Platform',(-70,.8,-102),(35,1.4,6),'ivory',transit)
for x in [-9,9]:box('BUS_ShelterPole',(x,1.7,35),(.18,3.4,.18),'cyan',transit)
box('BUS_ShelterRoof',(0,3.5,35),(21,.25,4),'navy',transit)
text('BUS_StopLabel','ONIBUS • LINHA CONHECIMENTO',(0,3.9,37),.6,'gold',transit)

# Farm and cultivation plots.
facade('FARM_House',-26,104,13,12,5,'FAZENDA PREP',farm)
facade('FARM_Barn',25,104,18,14,7,'CELEIRO',farm)
for i in range(3):
 cylinder('FARM_Silo_'+str(i),(42+i*6,5,111),2.6,10,'ivory',farm,12)
 cone('FARM_SiloRoof_'+str(i),(42+i*6,10.7,111),2.8,.1,1.4,'cyan',farm)
for row in range(5):
 for column in range(8):
  x=-17+column*4;z=86+row*3
  box('FARM_Soil_'+str(row)+'_'+str(column),(x,.18,z),(3.6,.3,2.3),'earth',farm)
  for j in range(3):cone('FARM_Plant',(x-1+j,.8,z),.32,.1,1.4,'foliage',farm)
for i in range(30):
 x=-115+(i%10)*24;z=-116+(i//10)*30
 cylinder('TREE_Trunk',(x,2,z),.35,4,'earth',props)
 sphere('TREE_Crown',(x,5.2,z),2.7,'foliage',props,(1,1.2,1),1)

# Dedicated gateway landscapes with more complete separate biome scenes below.
for x,z,label in [(-90,90,'AMAZONIA'),(-90,-95,'FLORESTA NEGRA'),(105,0,'OCEANO')]:
 ring('PORTAL_'+label,(x,3,z),3,.22,'magenta',science,True)
 text('PORTAL_Label_'+label,label,(x,7,z),.7,'cyan',science)

scene.world=bpy.data.worlds.new('ARAP_NightWorld');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.006,.015,.04,1)
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.45
def light_and_camera(sc,c,center,span):
 bpy.context.window.scene=sc
 bpy.ops.object.light_add(type='SUN',location=(0,0,60));o=adopt(bpy.context.object,'ARAP_SunLight',c,None);o.rotation_euler=(.5,-.4,-.6);o.data.energy=2.3
 bpy.ops.object.light_add(type='AREA',location=(0,-80,130));o=adopt(bpy.context.object,'ARAP_Fill',c,None);o.data.energy=2200;o.data.shape='DISK';o.data.size=100
 bpy.ops.object.camera_add(location=Vector(xyz(center))+Vector((.75,-1.2,1))*span)
 camera=adopt(bpy.context.object,'ARAP_Camera',c,None);camera.rotation_euler=(Vector(xyz(center))-camera.location).to_track_quat('-Z','Y').to_euler()
 camera.data.type='ORTHO';camera.data.ortho_scale=span*1.42;camera.data.clip_end=2000;sc.camera=camera
 sc.render.engine='CYCLES';sc.cycles.samples=12;sc.render.resolution_x=1440;sc.render.resolution_y=1000;sc.render.resolution_percentage=100

# Heliocentric teaching clock: 120 seconds per orbit, exactly the runtime schema.
clock={'epochMs':1791201600000,'orbitPeriodSeconds':120,'dayPeriodSeconds':240,'orbitRadius':14,'sunCenter':[0,55,0],'blenderFps':60,'blenderStartFrame':1}
sphere('SKY_Sun',(0,55,0),5,'gold',sky,sub=2)
orbit=root_obj('SKY_Orbit_Controller',sky);orbit.location=xyz((0,55,0))
earth=sphere('SKY_Earth',(14,55,0),2.2,'cyan',sky,sub=2);parent_all([earth],orbit)
# Small low-poly continents on the celestial globe.
for i in range(6):
 a=i*math.tau/6;p=(14+1.9*math.cos(a),55+1.1*math.sin(a),.9*math.sin(a))
 patch=sphere('SKY_Continent',p,.75,'foliage',sky,(.9,.35,.9),1);parent_all([patch],earth)
ring('SKY_OrbitGuide',(0,55,0),14,.045,'cyan',sky)
for f,a in [(1,0),(7201,-math.tau)]:orbit.rotation_euler[2]=a;orbit.keyframe_insert(data_path='rotation_euler',frame=f)
orbit['clock_schema']=json.dumps(clock)

# Reusable vehicles and interaction props. All pivot roots have metre dimensions.
prop_scene=bpy.data.scenes.new('01_ARAPIRACA_PROPS_20261005');prop_scene.unit_settings.system='METRIC';prop_scene.unit_settings.scale_length=1
prop_scene.render.fps=60;prop_scene.frame_start=1;prop_scene.frame_end=121
prop_records=[];prop_collections={}
def make_prop(pid,label,category,builder):
 bpy.context.window.scene=prop_scene
 c=bpy.data.collections.new('ARAP_PROP_'+pid);prop_scene.collection.children.link(c)
 before=set(c.objects);r=root_obj('PROP_'+pid+'_Root',c);builder(c)
 parent_all(list(c.objects),r);r['prop_id']=pid;r['author']='Romario Vicente Amaro'
 prop_collections[pid]=c
 dest=PUBLIC/('PROP_'+pid+'_20261005.glb')
 if dest.exists():raise FileExistsError(str(dest))
 bpy.ops.object.select_all(action='DESELECT')
 for o in c.objects:o.select_set(True)
 bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_extras=True,export_cameras=False,export_lights=False)
 prop_records.append({'id':pid,'url':'/assets/cyber/'+dest.name,'label':label,'category':category,'animations':[],'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
 return r
def wheel(c,x,z,r=.5):
 o=cylinder('VEH_Wheel',(x,r,z),r,.3,'navy',c,12);o.rotation_euler[1]=math.pi/2
 hub=cylinder('VEH_Hub',(x+.16,r,z),r*.45,.04,'cyan',c,12);hub.rotation_euler[1]=math.pi/2
def bus(c):
 box('VEH_BusChassis',(0,.65,0),(2.5,.5,9),'navy',c);box('VEH_BusBody',(0,2,0),(2.45,2.4,8.8),'ivory',c)
 for z in [-3,-1,1,3]:
  for x in [-1.24,1.24]:box('VEH_BusWindows',(x,2.35,z),(.08,1.1,1.5),'glass',c)
 box('VEH_BusFront',(0,2.35,4.48),(2,1.2,.06),'glass',c)
 for x in [-1.3,1.3]:
  for z in [-2.8,2.8]:wheel(c,x,z,.5)
 box('VEH_BusNeon',(0,1.1,4.52),(2,.12,.08),'cyan',c)
 text('VEH_BusDestination','CONHECIMENTO',(0,3.4,4.55),.19,'gold',c)
def train(c):
 for j in range(3):
  z=-j*7;box('VEH_TrainCar',(0,1.6,z),(2.8,2.7,6.4),'navy',c)
  box('VEH_TrainRoof',(0,3.1,z),(3,.25,6.5),'cyan',c)
  for x in [-1.43,1.43]:
   for dz in [-2,0,2]:box('VEH_TrainGlass',(x,2,z+dz),(.08,1.2,1.5),'glass',c)
  for x in [-1.1,1.1]:
   for dz in [-2.2,2.2]:wheel(c,x,z+dz,.36)
 box('VEH_TrainWindshield',(0,2.1,3.25),(2.5,1.4,.1),'glass',c)
def elevator(c):
 box('LIFT_CabinFloor',(0,.12,0),(4,.25,4),'ivory',c)
 box('LIFT_CabinBack',(0,1.6,-1.95),(4,3.2,.14),'glass',c)
 for x in [-1.95,1.95]:box('LIFT_CabinSide',(x,1.6,0),(.14,3.2,4),'glass',c)
 box('LIFT_CabinRoof',(0,3.3,0),(4,.2,4),'cyan',c)
def tractor(c):
 box('VEH_Tractor',(0,1.1,0),(1.5,1.2,3),'gold',c);box('VEH_TractorCab',(0,2.2,-.7),(1.7,1.8,1.6),'glass',c)
 box('VEH_TractorRoof',(0,3.2,-.7),(2,.18,1.9),'magenta',c)
 for x in [-.9,.9]:
  wheel(c,x,-.8,.8);wheel(c,x,1.1,.47)
 cylinder('VEH_TractorExhaust',(.5,2.3,.8),.12,1.7,'navy',c)
def harvester(c):
 box('VEH_Harvester',(0,1.7,0),(3,2.4,4),'gold',c);box('VEH_HarvesterCab',(0,3,1),(2,1.8,1.7),'glass',c)
 box('VEH_HarvesterHeader',(0,.7,3.3),(5,.8,1.3),'navy',c)
 for x in [-1.65,1.65]:
  for z in [-1.2,1.4]:wheel(c,x,z,.8)
 segment('VEH_HarvesterAuger',(-1.4,3,-1),(-4.5,3.1,-1),.3,.3,'ivory',c)
def moto(c):
 box('VEH_MotoFrame',(0,.7,0),(.5,.7,1.7),'yellow',c);box('VEH_MotoSeat',(0,1.2,-.3),(.7,.15,1.1),'navy',c)
 for z in [-.9,.95]:wheel(c,0,z,.45)
 box('VEH_MotoHeadlamp',(0,1.2,1),(.5,.4,.15),'cyan',c)
 segment('VEH_MotoHandle',(-.55,1.6,.65),(.55,1.6,.65),.08,.08,'ivory',c)
 text('VEH_MotoTaxiPlate','MOTOTAXI',(0,1.6,-1),.17,'yellow',c)
def truck(c):
 box('VEH_TruckChassis',(0,.7,0),(2.6,.4,5.7),'navy',c);box('VEH_TruckCab',(0,2.1,1.5),(2.5,2.7,2.5),'magenta',c)
 box('VEH_TruckWindshield',(0,2.6,2.78),(2.2,1,.08),'glass',c)
 for x in [-1.3,1.3]:
  for z in [-2,-.8,1.9]:wheel(c,x,z,.6)
def trailer(c,kind):
 box('VEH_TrailerChassis',(0,.8,0),(2.65,.3,8),'navy',c)
 if kind=='flatbed':box('VEH_TrailerDeck',(0,1.1,0),(2.7,.25,8),'ivory',c)
 if kind=='box':box('VEH_TrailerBox',(0,2.3,0),(2.6,2.7,7.9),'cyan',c)
 if kind=='tanker':
  o=cylinder('VEH_TrailerTank',(0,2.2,0),1.25,7.4,'ivory',c,16);o.rotation_euler[0]=math.pi/2
 for x in [-1.4,1.4]:
  for z in [-2.5,-1.1]:wheel(c,x,z,.6)
def phone(c):
 box('PROP_ChronovitaeBody',(0,.14,0),(.085,.16,.009),'navy',c)
 box('PROP_ChronovitaeScreen',(0,.14,.005),(.074,.139,.0015),'cyan',c)
 text('PROP_ChronovitaeBrand','CV',(0,.196,.006),.008,'navy',c)
 sphere('PROP_ChronovitaeCamera',(0,.209,.006),.002,'navy',c)
def rod(c):
 segment('PROP_FishingRod',(0,.05,0),(0,2.1,-.5),.027,.027,'ivory',c)
 cylinder('PROP_FishingReel',(0,.42,-.03),.085,.06,'gold',c)
 segment('PROP_FishingLine',(0,2.1,-.5),(0,.3,-1.8),.005,.005,'cyan',c)
def flower(c):
 cylinder('PROP_FlowerStem',(0,.25,0),.025,.5,'foliage',c,6)
 sphere('PROP_FlowerHeart',(0,.57,0),.08,'gold',c)
 for i in range(6):
  a=math.tau*i/6;sphere('PROP_FlowerPetal',(.13*math.cos(a),.55,.13*math.sin(a)),.11,'magenta',c)
def bench(c):
 box('PROP_BenchSeat',(0,.55,0),(2.4,.16,.8),'ivory',c);box('PROP_BenchBack',(0,1,-.35),(2.4,.8,.15),'navy',c)
 for x in [-.9,.9]:box('PROP_BenchLeg',(x,.25,0),(.15,.5,.65),'cyan',c)
def fish(c,mat='cyan',shark=False):
 sphere('FAUNA_Body',(0,.55,0),.5 if not shark else 1,mat,c,(.42,.5,1.6),1)
 tail=cone('FAUNA_Tail',(0,.55,-.9 if not shark else -1.8),.4 if not shark else .75,0,.12,mat,c);tail.rotation_euler[0]=math.pi/2
 fin=cone('FAUNA_Dorsal',(0,.92 if not shark else 1.3,0),.25 if not shark else .5,0,.5 if not shark else .9,mat,c)
 for x in [-.19,.19]:sphere('FAUNA_Eye',(x,.64,.58 if not shark else 1.2),.03 if not shark else .08,'navy',c)
for pid,label,cat,fn in [('bus','Ônibus Conhecimento','Transporte',bus),('train','Trem futurista','Transporte',train),('elevator','Cabine elevador','Interações',elevator),('tractor','Trator agrícola','Fazenda',tractor),('harvester','Colheitadeira','Fazenda',harvester),('mototaxi','Mototáxi','Transporte',moto),('truck','Cavalo mecânico','Transporte',truck),('smartphone','CHRONOVITAE','Interações',phone),('fishing-rod','Vara de pesca','Interações',rod),('flower','Flor coletável','Interações',flower),('bench','Banco para sentar','Interações',bench),('shark','Tubarão estilizado','Fauna',lambda c:fish(c,'concrete',True)),('fish-blue','Peixe azul','Fauna',lambda c:fish(c,'cyan')),('fish-yellow','Peixe amarelo','Fauna',lambda c:fish(c,'gold')),('fish-red','Peixe vermelho','Fauna',lambda c:fish(c,'magenta'))]:make_prop(pid,label,cat,fn)
for kind in ['flatbed','box','tanker']:make_prop('truck-trailer-'+kind,'Reboque '+kind,'Transporte',lambda c,k=kind:trailer(c,k))

# Show the same real reusable assets in the integrated Blender scene.
bpy.context.window.scene=scene
def place_prop(pid,p,heading=0,animate=None):
 source=prop_collections[pid];copies={o:o.copy() for o in source.objects}
 for old,o in copies.items():
  transit.objects.link(o);o.name='WORLD_'+pid+'_'+old.name
 for old,o in copies.items():
  if old.parent in copies:o.parent=copies[old.parent]
 r=next(o for old,o in copies.items() if old.parent is None)
 r.location=xyz(p);r.rotation_euler[2]=-heading
 if animate:keyed_cycle(r,*animate)
 return r
bus_route=[(0,.2,35),(95,.2,35),(95,.2,-75),(-80,.2,-75),(-80,.2,35),(0,.2,35)]
place_prop('bus',bus_route[0],animate=(bus_route,[1,1081,2161,3241,4321,5401]))
place_prop('train',(-70,.3,-103),animate=([(a,.3,b) for a,b in [(-70,-103),(102,-103),(117,92),(-97,114),(-115,-85),(-70,-103)]],[1,1441,2881,4321,5761,7201]))
lift=place_prop('elevator',(-17,.4,56),animate=([(-17,.4,56),(-17,-6,56),(-17,-6,56),(-17,.4,56)],[1,241,481,721]))
lift['interaction']='Elevator access, game movement controlled by simulation state.'
place_prop('tractor',(-5,.1,105),animate=([(-5,.1,105),(16,.1,105),(-5,.1,105)],[1,601,1201]))
place_prop('harvester',(23,.1,90));place_prop('mototaxi',(-43,.1,65));place_prop('truck',(90,.1,50));place_prop('truck-trailer-tanker',(90,.1,43))
for p in [(-12,.1,8),(12,.1,8),(28,.1,-16),(0,.1,38)]:place_prop('bench',p)
for i in range(16):place_prop('flower',(-20+i*2.5,.1,22))
place_prop('fishing-rod',(106,.2,14));place_prop('fish-blue',(127,.2,0));place_prop('fish-yellow',(134,.2,8));place_prop('shark',(140,.1,-6))
phone_display=place_prop('smartphone',(19,0,23));phone_display.scale=(22,22,22)
# Blender exhibits the same quarter-orbit phase on both displays. The runtime
# displays the full clock text from one sampleWorldClock value every frame.
for quarter in range(4):
 for device,p,size in [('BILLBOARD',(0,14,25.82),.9),('PHONE',(19,2.7,23.14),.17)]:
  label=text('CLOCK_'+device+'_Q'+str(quarter),'ORBITA '+str(quarter+1)+'/4 | JARVIS',p,size,'cyan',transit)
  for q in range(5):
   label.hide_render=q%4!=quarter;label.hide_viewport=q%4!=quarter
   label.keyframe_insert(data_path='hide_render',frame=1+q*1800)
   label.keyframe_insert(data_path='hide_viewport',frame=1+q*1800)
# Imported prepared armatures stay intact. Local copies are staged as NPCs.
rigged=json.loads((ROOT/'frontend/src/config/riggedAssets.json').read_text(encoding='utf-8'))
chosen=[next((a for a in rigged if a['id'].removeprefix('SUP_')==key),None) for key in ['doctor_horror_hospital','jumpsuit_low_poly','school_girl_v21']]
npc_report=[]
for i,rec in enumerate(x for x in chosen if x):
 before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/rec['url'].lstrip('/')))
 new=set(scene.objects)-before;r=root_obj('NPC_ARAP_'+rec['id'],npcs)
 for o in new:
  for c in list(o.users_collection):c.objects.unlink(o)
  npcs.objects.link(o)
 parent_all(new,r)
 pts=[o.matrix_world@Vector(v) for o in new if o.type=='MESH' for v in o.bound_box]
 lo=Vector([min(v[k] for v in pts) for k in range(3)]);hi=Vector([max(v[k] for v in pts) for k in range(3)])
 r.scale=(1.8/max(.01,hi.z-lo.z),)*3;r.location=xyz([(48,0,-21),(-10,0,14),(-68,0,-45)][i]);r.location.z-=lo.z*r.scale.z
 for o in new:
  if o.animation_data:
   for j,t in enumerate(o.animation_data.nla_tracks):t.mute=j!=0
 npc_report.append({'id':rec['id'],'meshes':sum(o.type=='MESH' for o in new),'armatures':sum(o.type=='ARMATURE' for o in new),'bones':sum(len(o.data.bones) for o in new if o.type=='ARMATURE')})

# Separate low-poly environmental biomes, accessible through portals in runtime.
biomes=[]
for bid,label,dark in [('amazon','Floresta Amazônica',False),('black-forest','Floresta Negra',True),('ocean','Reserva marinha',False)]:
 sc=bpy.data.scenes.new('BIOME_'+bid.upper()+'_20261005');bpy.context.window.scene=sc;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
 c=bpy.data.collections.new('ARAP_BIOME_'+bid);sc.collection.children.link(c)
 sc.world=scene.world
 box('BIOME_Floor',(0,-.2,0),(130,.4,130),'water' if bid=='ocean' else 'earth',c)
 if bid!='ocean':
  for i in range(72):
   x=((i*17)%119)-59;z=((i*29)%119)-59
   if abs(x)<9 and abs(z)<9:continue
   cylinder('BIOME_Trunk',(x,2.8,z),.35,5.6,'earth',c)
   if dark:
    for h,rad in [(4,2.8),(6,2.2),(8,1.6)]:cone('BIOME_Pine',(x,h,z),rad,0,4,'foliage',c)
   else:
    sphere('BIOME_Canopy',(x,6,z),3.5,'foliage',c,(1.3,.9,1.3),1)
    for k in [-1,1]:segment('BIOME_Vine',(x+k,6,z),(x+k,.5,z),.07,.07,'foliage',c)
  box('BIOME_RangerHut',(0,1.5,-15),(9,3,7),'navy',c)
  text('BIOME_SafeZone','ACAMPAMENTO | ZONA SEGURA',(0,4,-11),.55,'cyan',c)
  sc['combat_policy']='Fictional combat allowed only outside safe camp; never in hospital/city.'
 else:
  for i in range(18):
   sphere('BIOME_Coral',((i*11)%91-45,.4,(i*17)%91-45),2,'purple' if i%2 else 'gold',c,(.6,1.1,.6),1)
  # Copy real modeled fish geometry into the marine scene.
  for i in range(12):
   source=prop_collections[['fish-blue','fish-yellow','fish-red','shark'][i%4]]
   copies={o:o.copy() for o in source.objects}
   for o in copies.values():c.objects.link(o)
   for old,o in copies.items():
    if old.parent in copies:o.parent=copies[old.parent]
   r=next(o for old,o in copies.items() if old.parent is None);r.location=xyz(((i%4)*12-18,1,(i//4)*16-16))
 bpy.ops.object.select_all(action='DESELECT')
 for o in c.objects:o.select_set(True)
 path=PUBLIC/('ENV_Biome_'+bid+'_20261005.glb')
 if path.exists():raise FileExistsError(str(path))
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_lights=False,export_cameras=False)
 biomes.append({'id':bid,'label':label,'url':'/assets/cyber/'+path.name,'combatAllowed':bid!='ocean','safeRadius':12})
 light_and_camera(sc,c,(0,0,0),105)

# Private owner home: never linked into a public scene or exported into public/.
private=Path(os.environ.get('LOCALAPPDATA',str(ROOT/'private_local')))/'PREPARATORIO'
private.mkdir(parents=True,exist_ok=True)
home=bpy.data.scenes.new('PRIVATE_CREATOR_HOME_20261005');bpy.context.window.scene=home
home.unit_settings.system='METRIC';home.unit_settings.scale_length=1;home.world=scene.world
c=bpy.data.collections.new('PRIVATE_OWNER_HOME');home.collection.children.link(c)
box('PRIVATE_HomeFloor',(0,-.15,0),(14,.3,12),'navy',c)
for x in [-7,7]:box('PRIVATE_HomeWall',(x,1.8,0),(.25,3.6,12),'concrete',c)
box('PRIVATE_HomeBack',(0,1.8,-6),(14,3.6,.25),'concrete',c)
for x in [-4.5,4.5]:box('PRIVATE_HomeFront',(x,1.8,6),(5,3.6,.25),'concrete',c)
door=box('PRIVATE_Door',(0,1.6,6),(3.5,3.2,.18),'glass',c)
box('PRIVATE_Keypad',(2.5,1.7,6.2),(.65,.85,.12),'cyan',c)
for j in range(12):box('PRIVATE_Key_'+str(j),(2.3+(j%3)*.2,1.95-(j//3)*.16,6.29),(.14,.11,.035),'navy',c)
text('PRIVATE_Author','ROMARIO VICENTE AMARO',(0,3.9,6.3),.45,'gold',c)
box('PRIVATE_Bed',(4,.5,-3),(3,.65,4),'ivory',c);box('PRIVATE_Desk',(-4,.9,-3),(4,.2,1.6),'ivory',c)
box('PRIVATE_Terminal',(-4,1.6,-3.3),(2,1.1,.12),'cyan',c)
box('PRIVATE_Sofa',(-4,.5,1),(4,1,1.5),'purple',c)
ring('PRIVATE_Portal',(0,.05,-2),1.6,.1,'cyan',c)
bpy.ops.object.select_all(action='DESELECT')
for o in c.objects:o.select_set(True)
private_path=private/'Romario_PrivateHome_20261005.glb'
if private_path.exists():raise FileExistsError('Private output already exists')
bpy.ops.export_scene.gltf(filepath=str(private_path),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_extras=False)
light_and_camera(home,c,(0,0,0),13)
private_blend=private/'Romario_PrivateHome_20261005.blend'
bpy.data.libraries.write(str(private_blend),{home},fake_user=True,compress=True)
# Unlink/remove only newly created private datablocks from PUBLIC master.
private_objects=list(home.objects)
bpy.context.window.scene=scene
bpy.data.scenes.remove(home)
for o in private_objects:bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(c)

# Export static urban environment only, excluding live transit/NPCs/clock which
# are updated by the client. Their original editable copies stay in the .blend.
bpy.context.window.scene=scene
bpy.ops.object.select_all(action='DESELECT')
export_cols=[ground,roads,buildings,science,props,farm]
env_objects=[]
for c in export_cols:
 for o in c.objects:o.select_set(True);env_objects.append(o)
env_path=PUBLIC/'ENV_Arapiraca_Cyber_20261005.glb'
if env_path.exists():raise FileExistsError(str(env_path))
bpy.ops.export_scene.gltf(filepath=str(env_path),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_lights=False,export_cameras=False,export_extras=True)
zones=[{'id':a,'label':b,'position':p,'approach':q} for a,b,p,q in [
 ('plaza','Praça do Conhecimento',[0,0,0],[0,0,20]),('hospital','Hospital de Emergência PREP',[48,0,-38],[48,0,-21]),('laboratory','Laboratório e acelerador',[80,0,-38],[79,0,7]),('station','Estação Arapiraca',[-70,0,-55],[-70,0,-43]),('store','Loja e roupas',[-45,0,25],[-45,0,37]),('hangar','Hangar e concessionárias',[85,0,65],[85,0,73]),('farm','Fazenda',[0,0,100],[0,0,105]),('bus-stop','Ponto Conhecimento',[0,0,35],[0,0,35]),('amazon','Portal Amazônia',[-90,0,90],[-90,0,90]),('black-forest','Portal Floresta Negra',[-90,0,-95],[-90,0,-95]),('beach','Portal Oceano',[105,0,0],[105,0,0])]]
colliders=[{'x':x,'z':z,'w':w,'d':d} for x,z,w,d in [(48,-38,36,27),(48,-59,26,10),(80,-38,23,24),(-45,25,20,15),(-46,53,21,17),(67,57,24,22),(85,90,30,22),(-70,-88,27,16),(-26,104,13,12),(25,104,18,14)]]
manifest={'version':1,'author':'Romario Vicente Amaro','units':'meters','sceneUrl':'/assets/cyber/'+env_path.name,'props':prop_records,'zones':zones,'colliders':colliders,'clock':clock,'biomes':biomes,'parking':parking,'reference':'arapiracaReference.json','status':'Interactive local prototype; geographically compressed fictional city.'}
(ROOT/'frontend/src/config/cyberWorldManifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
light_and_camera(scene,lighting,(0,3,0),220)
scene.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_floor=False
   area.spaces.active.region_3d.view_distance=260
   area.spaces.active.region_3d.view_location=Vector((0,0,5))
# Asset presentation collection grid without changing local pivots of GLBs.
bpy.context.window.scene=prop_scene
for i,(pid,c) in enumerate(prop_collections.items()):
 r=next(o for o in c.objects if o.parent is None);r.location=xyz(((i%6)*11,0,(i//6)*25))
light_and_camera(prop_scene,prop_scene.collection,(28,0,30),90)
bpy.context.window.scene=scene
city_blend=ROOT/'art/blender/PREPARATORIO_ARAPIRACA_CYBER_20261005.blend'
bpy.data.libraries.write(str(city_blend),{scene,prop_scene,*[bpy.data.scenes['BIOME_'+b['id'].upper()+'_20261005'] for b in biomes]},fake_user=True,compress=True)
master=ROOT/'art/blender/PREPARATORIO_PROJETO_20261005.blend'
if master.exists():raise FileExistsError(str(master))
bpy.ops.wm.save_as_mainfile(filepath=str(master))
report={'blenderVersion':bpy.app.version_string,'scene':scene.name,'objectsInCity':len(scene.objects),'meshesInCity':sum(o.type=='MESH' for o in scene.objects),'cityCollections':[c.name for c in scene.collection.children],'newMaterials':[m.name for m in M.values()],'exportedProps':len(prop_records),'biomes':biomes,'npcRigs':npc_report,'environment':{'path':str(env_path),'bytes':env_path.stat().st_size,'sha256':hashlib.sha256(env_path.read_bytes()).hexdigest()},'blends':[str(city_blend),str(master)],'privateHomePublic':False,'privateHomeAsset':str(private_path),'clock':clock,'originalScenesPreserved':True}
(REPORT/'arapiraca_build_20261005.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
