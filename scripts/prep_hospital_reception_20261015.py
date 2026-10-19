"""Create the first original hospital module, separate from the existing city.

Authored dimensions are game targets, not clinical/architectural certification.
Existing objects are never renamed, transformed, deleted or exported.
"""
import bpy,hashlib,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
OUT=ROOT/'frontend/public/assets/environments/ENV_Hospital_Reception_Module_20261015.glb'
SCENE='PREP_HOSPITAL_RECEPTION_20261015'
P='HSP15_'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert SCENE not in bpy.data.scenes and not OUT.exists(),'Preserve and inspect existing delivery.'
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
original=list(bpy.data.objects)
before=state_hash(object_state(original))
expected=json.loads((ROOT/'reports/hospital_checkpoint_20261015.json').read_text())
assert before==expected['objectStateHash']
scene=bpy.data.scenes.new(SCENE)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['author']='Romario Vicente Amaro'
scene['status']='FIRST_RECEPTION_MODULE_PROTOTYPE'
scene['runtime_enabled']=False
scene['future_macro_translation_xyz']=[500,-333,0]
scene['scope']='36 x 24 m module; educational game prototype, not an operational or certified hospital.'
for window in bpy.context.window_manager.windows:window.scene=scene
cols={}
for name in ('STRUCTURE','FACADES','ROOF','INTERIORS','DOORS','FURNITURE','SIGNAGE','LANDSCAPE','REFERENCE','LIGHTING'):
    col=bpy.data.collections.new(P+name);scene.collection.children.link(col);cols[name]=col
def rgb(value):
    value=value.lstrip('#');channels=[int(value[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in channels)
def material(name,color,rough=.6,metal=0,alpha=1,emission=0):
    mat=bpy.data.materials.new(P+name);mat.use_nodes=True
    node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    base=(*rgb(color),alpha);mat.diffuse_color=base
    node.inputs['Base Color'].default_value=base;node.inputs['Roughness'].default_value=rough
    node.inputs['Metallic'].default_value=metal;node.inputs['Alpha'].default_value=alpha
    if emission:
        node.inputs['Emission Color'].default_value=base;node.inputs['Emission Strength'].default_value=emission
    if alpha<1:
        mat.surface_render_method='DITHERED'
    return mat
mats={key:material(key,*value) for key,value in {
    'Wall':('#e9ece7',.75),'TileA':('#d5d8d2',.28),'TileB':('#d1d5cf',.32),
    'Grout':('#8b9690',.85),'Teal':('#125b62',.48),'Metal':('#889a9e',.28,.75),
    'Dark':('#253439',.5),'Glass':('#b3e0df',.12,.08,.24),'Wood':('#a67b50',.56),
    'Seat':('#297a83',.65),'Fabric':('#607b77',.8),'White':('#f8faf4',.35),
    'Screen':('#10333d',.28,0,1,.5),'Led':('#d8f8f1',.3,0,1,3),
    'Blue':('#32baca',.4,0,1,.5),'Leaf':('#42734f',.85),'Soil':('#45362b',.95),
    'Red':('#bc4545',.5),'Gold':('#bb9652',.5,.35)}.items()}
colliders=[]
def tag(obj):
    obj['hospital_module']=True;obj['author']='Romario Vicente Amaro';return obj
def box(name,center,size,mat='Wall',col='STRUCTURE',bevel=.015,solid=False,parent=None):
    dx,dy,dz=[v/2 for v in size]
    verts=[(x,y,z) for z in (-dz,dz) for y in (-dy,dy) for x in (-dx,dx)]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    mesh=bpy.data.meshes.new(P+name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=tag(bpy.data.objects.new(P+name,mesh));cols[col].objects.link(obj)
    obj.location=center;obj.data.materials.append(mats[mat]);obj.parent=parent
    if bevel:
        mod=obj.modifiers.new('Architectural edge radius','BEVEL');mod.width=min(bevel,min(size)*.25);mod.segments=3
        mod.limit_method='ANGLE'
    if solid:
        obj['walk_obstacle']=True;colliders.append(obj)
    return obj
def cylinder(name,center,radius,depth,mat='Metal',col='FURNITURE',segments=20):
    vertices=[(radius*math.cos(a*2*math.pi/segments),radius*math.sin(a*2*math.pi/segments),z)
              for z in (-depth/2,depth/2) for a in range(segments)]
    faces=[tuple(reversed(range(segments))),tuple(range(segments,segments*2))]
    faces += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    mesh=bpy.data.meshes.new(P+name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=tag(bpy.data.objects.new(P+name,mesh));cols[col].objects.link(obj);obj.location=center;mesh.materials.append(mats[mat])
    for f in mesh.polygons[2:]:f.use_smooth=True
    mod=obj.modifiers.new('Rounded rim','BEVEL');mod.width=min(.008,radius*.15);mod.segments=2
    return obj
def text(name,body,center,size=.24,mat='Dark',rotation=(math.pi/2,0,0)):
    data=bpy.data.curves.new(P+name,'FONT');data.body=body;data.size=size
    data.align_x='CENTER';data.align_y='CENTER';data.extrude=.0015
    obj=tag(bpy.data.objects.new(P+name,data));cols['SIGNAGE'].objects.link(obj)
    obj.location=center;obj.rotation_euler=rotation;data.materials.append(mats[mat]);return obj
def marker(name,position):
    obj=tag(bpy.data.objects.new(P+name,None));cols['SIGNAGE'].objects.link(obj);obj.location=position
    obj.empty_display_size=.25;return obj
def animate(obj,clip,field,closed,opened):
    setattr(obj,field,closed);obj.keyframe_insert(data_path=field,frame=1)
    setattr(obj,field,opened);obj.keyframe_insert(data_path=field,frame=31)
    action=obj.animation_data.action;action.name=clip+'_'+obj.name
    track=obj.animation_data.nla_tracks.new();track.name=clip
    track.strips.new(clip,1,action);obj.animation_data.action=None

# A continuous structural slab and a single mesh of actual porcelain tiles.
box('SLAB',(0,0,-.12),(36.2,24.2,.24),'Grout',bevel=.025)
vertices=[];faces=[];indices=[]
for x in range(-18,18):
    for y in range(-12,12):
        start=len(vertices);pad=.003
        vertices += [(x+pad,y+pad,.012),(x+1-pad,y+pad,.012),(x+1-pad,y+1-pad,.012),(x+pad,y+1-pad,.012)]
        faces.append(tuple(range(start,start+4)));indices.append((x+y)%2)
mesh=bpy.data.meshes.new(P+'PorcelainTiles');mesh.from_pydata(vertices,[],faces);mesh.update()
floor=tag(bpy.data.objects.new(P+'FLOOR_TILES',mesh));cols['STRUCTURE'].objects.link(floor)
mesh.materials.append(mats['TileA']);mesh.materials.append(mats['TileB'])
for face,index in zip(mesh.polygons,indices):face.material_index=index

# Exterior facade: opaque lower apron, transparent glazing and metal mullions.
for side in (-1,1):
    x=side*18
    box('SIDE_APRON_'+str(side),(x,0,.32),(.2,24,.64),'Wall','FACADES',solid=True)
    box('SIDE_GLASS_'+str(side),(x,0,2.13),(.06,24,2.96),'Glass','FACADES',bevel=.004,solid=True)
    box('SIDE_TOP_'+str(side),(x,0,3.85),(.22,24,.7),'Teal','FACADES')
    for y in range(-12,13,3):box('SIDE_MULLION_'+str(side)+'_'+str(y),(x,y,2.1),(.13,.10,3.25),'Metal','FACADES')
box('REAR_WALL',(0,12,2.1),(36,.2,4.2),'Wall',solid=True)
for side in (-1,1):
    width=16.8;center=side*9.6
    box('FRONT_APRON_'+str(side),(center,-12,.32),(width,.2,.64),'Wall','FACADES',solid=True)
    box('FRONT_GLASS_'+str(side),(center,-12,2.1),(width,.06,2.9),'Glass','FACADES',.004,True)
    box('FRONT_TOP_'+str(side),(center,-12,3.85),(width,.25,.7),'Teal','FACADES')
    for x in [side*v for v in (3,6,9,12,15,18)]:box('FRONT_MULLION_'+str(x),(x,-12,2.1),(.10,.13,3.1),'Metal','FACADES')
box('PUBLIC_DOOR_HEADER',(0,-12,2.52),(2.6,.25,.24),'Metal','FACADES')
box('PUBLIC_TRANSOM',(0,-12,3.0),(2.4,.06,.72),'Glass','FACADES',.004)
for side in (-1,1):
    leaf=box('DOOR_PUBLIC_'+('Left' if side<0 else 'Right'),(side*.6,-12.15,1.22),(1.2,.05,2.4),'Glass','DOORS',.008,True)
    animate(leaf,'Door_Open','location',(side*.6,-12.15,1.22),(side*1.85,-12.15,1.22))
    # Door trim follows the same local translation through parenting.
    box('DOOR_PUBLIC_HANDLE_'+str(side),(0,-.04,0),(.05,.035,.50),'Metal','DOORS',.008,parent=leaf)
    for edge in (-1,1):box('DOOR_PUBLIC_EDGE_'+str(side)+'_'+str(edge),(edge*.575,0,0),(.045,.065,2.4),'Metal','DOORS',.006,parent=leaf)
marker('WAYPOINT_ENTRANCE',(0,-11.2,.03))

# Four rear rooms and a genuinely clear central corridor, x=-1.6..+1.6.
for side in (-1,1):
    x=side*1.7
    for suffix,y,length in [('A',-2.4,3.2),('B',4,6.4),('C',10.4,3.2)]:
        box('CORRIDOR_WALL_'+str(side)+suffix,(x,y,2.1),(.2,length,4.2),'Wall','INTERIORS',solid=True)
    for y in (0,8):box('ROOM_LINTEL_'+str(side)+str(y),(x,y,3.3),(.2,1.6,1.8),'Wall','INTERIORS')
    box('ROOM_OUTER_'+str(side),(side*9.9,4,2.1),(.2,16,4.2),'Wall','INTERIORS',solid=True)
    for y in (-4,4):box('ROOM_TRANSVERSE_'+str(side)+str(y),(side*5.8,y,2.1),(8.2,.2,4.2),'Wall','INTERIORS',solid=True)
    # Neutral reserved side wings remain visible as later support areas.
    text('SUPPORT_'+str(side),'APOIO FUTURO',(side*13.7,10.5,.03),.45,'Teal',(0,0,0))
room_data=[('01',-1,0,'TRIAGEM 01'),('02',1,0,'TRIAGEM 02'),('03',-1,8,'ENTREVISTA'),('04',1,8,'ENFERMAGEM')]
for key,side,y,label in room_data:
    hinge=tag(bpy.data.objects.new(P+'DOOR_ROOM_'+key+'_HINGE',None));cols['DOORS'].objects.link(hinge)
    hinge.location=(side*1.8,y-.8,0)
    leaf=box('DOOR_ROOM_'+key+'_LEAF',(0,.8,1.22),(.06,1.6,2.4),'Wood','DOORS',.012,True,parent=hinge)
    animate(hinge,'Room_Open_'+key,'rotation_euler',(0,0,0),(0,0,side*-math.pi/2))
    marker('WAYPOINT_TRIAGE_'+key,(side*1.7,y,1.3))
    # Room labels face the corridor, slightly below the lintel.
    text('ROOM_LABEL_'+key,label,(side*1.59,y,2.67),.20,'Teal',(math.pi/2,0,-side*math.pi/2))
    for height in (.13,1.0):box('WALL_PROTECTOR_'+key+str(height),(side*1.58,y+2.35,height),(.035,2.9,.10),'Teal','INTERIORS',.01)

# Reception desk, with clear approaches and staff access around its ends.
box('RECEPTION_BASE',(-7,-6.25,.51),(6,1.5,1.02),'Wood','FURNITURE',.04,True)
box('RECEPTION_TOP',(-7,-6.25,1.065),(6.15,1.65,.09),'White','FURNITURE',.025)
box('RECEPTION_LIGHT',(-7,-7.02,.78),(5.5,.025,.025),'Led','FURNITURE',.005)
text('RECEPTION_FRONT','ACOLHIMENTO',(-7,-7.035,.49),.26,'White')
text('RECEPTION_BACK','RECEPÇÃO  ·  PREPARATÓRIO',(-7,-4.13,2.5),.34,'Teal')
for x in (-8.8,-5.2):
    box('MONITOR_STEM_'+str(x),(x,-6.0,1.28),(.08,.1,.38),'Metal','FURNITURE')
    box('MONITOR_'+str(x),(x,-6.0,1.57),(.72,.07,.44),'Dark','FURNITURE',.025)
    box('MONITOR_SCREEN_'+str(x),(x,-6.041,1.57),(.65,.01,.36),'Screen','FURNITURE',.01)
marker('WAYPOINT_RECEPTION',(-7,-7.8,.03))

def chair(key,x,y,rotation=0):
    root=tag(bpy.data.objects.new(P+'CHAIR_'+key,None));cols['FURNITURE'].objects.link(root)
    root.location=(x,y,0);root.rotation_euler.z=rotation
    parts=[('SEAT',(0,0,.46),(.62,.59,.12),'Seat'),('BACK',(0,.25,.82),(.62,.10,.65),'Seat')]
    for side in (-1,1):
        parts += [('ARM'+str(side),(side*.35,0,.70),(.065,.5,.07),'Metal')]
        for front in (-1,1):parts += [('LEG'+str(side)+str(front),(side*.26,front*.20,.23),(.04,.04,.46),'Metal')]
    for suffix,center,size,mat in parts:box('CHAIR_'+key+'_'+suffix,center,size,mat,'FURNITURE',.025,parent=root)
    box('CHAIR_COLLIDER_'+key,(x,y,.44),(.76,.72,.86),'Seat','REFERENCE',0,True).hide_render=True
for row,y in enumerate((-10.5,-5.3)):
    for index,x in enumerate((5,7.2,9.4,11.6,13.8)):chair(str(row)+'_'+str(index),x,y,math.pi if row else 0)
text('WAITING','ESPERA  ·  ÁREA DE ESTUDOS',(9.3,-4.13,2.5),.34,'Teal')

for key,side,y,label in room_data:
    x=side*5.8
    box('DESK_'+key,(x,y+2.25,.77),(2.3,.8,.10),'White','FURNITURE',.025,True)
    for end in (-1,1):box('DESK_LEG_'+key+str(end),(x+end*.95,y+2.25,.37),(.07,.6,.74),'Metal','FURNITURE')
    chair('ROOM_'+key,x,y+3.0,math.pi)
    box('TERMINAL_'+key,(x,y+2.25,1.2),(.60,.08,.44),'Screen','FURNITURE',.02)
    if key in ('01','02'):
        bx=side*7.8
        box('EXAM_BASE_'+key,(bx,y-.7,.40),(1.0,2.0,.55),'White','FURNITURE',.06,True)
        box('EXAM_MATTRESS_'+key,(bx,y-.7,.77),(1.05,2.04,.18),'Seat','FURNITURE',.07)
        box('EXAM_PILLOW_'+key,(bx,y+.02,.91),(.77,.42,.12),'White','FURNITURE',.055)
        cylinder('STOOL_'+key,(x,y+1,.5),.32,.1,'Seat')
        cylinder('STOOL_COLUMN_'+key,(x,y+1,.27),.05,.45)
    text('SIMULATION_'+key,'AMBIENTE DE SIMULAÇÃO',(x,y+3.85,1.9),.23,'Teal')

# Floor wayfinding stays flush and outside the clear route.
for side in (-1,1):box('CORRIDOR_EDGE_'+str(side),(side*1.42,3.8,.018),(.035,15.8,.008),'Blue','INTERIORS',0)
for x in (-15.5,15.5):
    box('PLANTER_'+str(x),(x,-10.2,.4),(1.0,1.0,.8),'White','LANDSCAPE',.08,True)
    box('SOIL_'+str(x),(x,-10.2,.81),(.82,.82,.04),'Soil','LANDSCAPE',.015)
    for index in range(7):
        angle=index*2*math.pi/7
        leaf=box('LEAF_'+str(x)+'_'+str(index),(x+math.cos(angle)*.2,-10.2+math.sin(angle)*.2,1.2+index%3*.13),(.13,.07,.9),'Leaf','LANDSCAPE',.04)
        leaf.rotation_euler=(.3*math.sin(angle),.3*math.cos(angle),angle)

# Realistic canopy, columns and fine roof joints; roof pieces are independently hideable.
box('ENTRY_WALK',(0,-14,.0),(8,4,.025),'TileA','STRUCTURE',.02)
box('ROOF_CANOPY',(0,-13.8,3.25),(8.6,3.8,.18),'White','ROOF',.04)
for x in (-4.1,4.1):cylinder('CANOPY_COLUMN_'+str(x),(x,-15.1,1.6),.09,3.2,'Metal','STRUCTURE',24)
for x in (-12,-6,0,6,12):
    box('ROOF_MAIN_'+str(x),(x,0,4.21),(5.985,24.3,.20),'White','ROOF',.02)
# Last roof bay covers both outer edges without scaling any original object.
for x in (-16.5,16.5):box('ROOF_EDGE_'+str(x),(x,0,4.21),(2.985,24.3,.20),'White','ROOF',.02)
for x in (-10,0,10):
    for y in (-8,0,8):
        box('ROOF_LED_'+str(x)+'_'+str(y),(x,y,3.97),(3.3,.14,.06),'Led','ROOF',.02)
box('ENTRY_SIGN',(0,-12.18,3.85),(11,.12,.82),'Teal','FACADES',.03)
text('ENTRY_TITLE','PREPARATÓRIO',(0,-12.26,3.96),.48,'White')
text('ENTRY_SUBTITLE','RECEPÇÃO E ACOLHIMENTO',(0,-12.26,3.58),.19,'White')
text('AUTHOR','Romario Vicente Amaro  ·  módulo educacional',(-12,-12.12,.35),.13,'Teal')
for side in (-1,1):
    box('CANOPY_LINE_'+str(side),(side*3.2,-13.8,3.14),(.08,3.3,.025),'Led','ROOF',.01)

# Clone the existing fitted character hierarchy for Blender-only scale review.
source_root=bpy.data.objects.get('CHAR_ANA_DEMO_ROOT')
if source_root:
    tree=[source_root]+list(source_root.children_recursive);clones={}
    for source in tree:
        clone=source.copy();clone.name=P+'REF_'+source.name
        if source.type=='ARMATURE':clone.data=source.data.copy()
        cols['REFERENCE'].objects.link(clone);clone['preview_reference']=True;clone['hospital_module']=True
        clones[source]=clone
    for source,clone in clones.items():
        clone.parent=clones.get(source.parent)
        for mod in clone.modifiers:
            if mod.type=='ARMATURE' and mod.object in clones:mod.object=clones[mod.object]
        for constraint in clone.constraints:
            if hasattr(constraint,'target') and constraint.target in clones:constraint.target=clones[constraint.target]
        if clone.hide_render:clone.hide_set(True)
    clones[source_root].location=(-2.8,-9.6,.02)
    for clone in clones.values():
        if clone.type=='ARMATURE':
            for bone in clone.pose.bones:
                for constraint in bone.constraints:
                    if hasattr(constraint,'target') and constraint.target in clones:constraint.target=clones[constraint.target]

# Analytical walk checks use the actual new mesh transforms with all doors open.
scene.frame_start=1;scene.frame_end=31;scene.render.fps=30
scene.frame_set(31);bpy.context.view_layer.update()
paths={'reception':[(0,-13.5),(0,-8.5),(-7,-8.5),(-7,-7.8)],
       'triage01':[(0,-13.5),(0,0),(-3,0)],'triage02':[(0,-13.5),(0,0),(3,0)],
       'support':[(0,-13.5),(0,8),(-3,8)],'nursing':[(0,-13.5),(0,8),(3,8)]}
def footprint(obj):
    points=[obj.matrix_world@Vector(v) for v in obj.bound_box]
    return {'name':obj.name,'minX':min(p.x for p in points),'maxX':max(p.x for p in points),
            'minY':min(p.y for p in points),'maxY':max(p.y for p in points),'maxZ':max(p.z for p in points)}
boxes=[footprint(o) for o in colliders if o.type=='MESH']
for obj in colliders:
    if obj.name.startswith(P+'CHAIR_COLLIDER_'):
        obj.hide_set(True)
failures=[];samples=0
for key,path in paths.items():
    for start,end in zip(path,path[1:]):
        count=max(1,math.ceil(math.dist(start,end)/.2))
        for index in range(count+1):
            t=index/count;x=start[0]+(end[0]-start[0])*t;y=start[1]+(end[1]-start[1])*t;samples+=1
            for obstacle in boxes:
                # Exact disc-vs-AABB test, not an expanded square at corners.
                dx=max(obstacle['minX']-x,0,x-obstacle['maxX']);dy=max(obstacle['minY']-y,0,y-obstacle['maxY'])
                if obstacle['maxZ']>.1 and dx*dx+dy*dy<.4*.4-1e-5:
                    failures.append({'path':key,'position':[x,y],'obstacle':obstacle['name']})
assert not failures, 'Walking path blocked: '+json.dumps(failures[:10])

# Bake only newly authored curves to mesh, without touching original objects.
for obj in list(scene.objects):
    if obj.type in ('FONT','CURVE') and not obj.get('preview_reference'):
        for other in bpy.context.selected_objects:other.select_set(False)
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target='MESH')
for obj in scene.objects:obj.select_set(False)
exported=[]
for obj in scene.objects:
    if obj.type in ('MESH','EMPTY') and not obj.get('preview_reference') and not obj.name.startswith(P+'CHAIR_COLLIDER_'):
        obj.select_set(True);exported.append(obj)
scene.frame_set(1)
OUT.parent.mkdir(parents=True,exist_ok=True)
result=bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,
    export_yup=True,export_apply=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=True,
    export_cameras=False,export_lights=False,export_skins=False,export_extras=True)
assert 'FINISHED' in result and OUT.exists()

def camera(name,location,target,lens=35,ortho=None):
    data=bpy.data.cameras.new(P+name);obj=bpy.data.objects.new(P+name,data);cols['LIGHTING'].objects.link(obj)
    obj.location=location;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens;data.clip_end=1000
    if ortho:data.type='ORTHO';data.ortho_scale=ortho
    return obj
outside=camera('CAM_EXTERIOR',(28,-36,19),(0,-1,1.4),ortho=49)
inside=camera('CAM_RECEPTION',(12,-10.8,2.3),(-5,-3.5,1.4),lens=24)
plan_cam=camera('CAM_PLAN',(0,0,50),(0,0,0),ortho=40)
world=bpy.data.worlds.new(P+'World');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.42,.55,.65,1);bg.inputs[1].default_value=.5
light=bpy.data.lights.new(P+'Daylight','SUN');light.energy=2.0
sun=bpy.data.objects.new(P+'Daylight',light);cols['LIGHTING'].objects.link(sun);sun.rotation_euler=(.55,-.45,-.3)
for x,y in [(-8,-6),(8,-6),(-5,5),(5,5)]:
    data=bpy.data.lights.new(P+'Soft_'+str(x)+str(y),'AREA');data.energy=650;data.shape='DISK';data.size=5
    obj=bpy.data.objects.new(data.name,data);cols['LIGHTING'].objects.link(obj);obj.location=(x,y,3.8)
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1600;scene.render.resolution_y=1100
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.camera=outside
assert state_hash(object_state(original))==before,'An earlier object changed; inspect before saving.'
# Save before rendering so a later interruption cannot lose the new geometry.
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
renders=[]
for key,cam in [('exterior',outside),('recepcao',inside),('planta',plan_cam)]:
    scene.camera=cam;scene.frame_set(31)
    if key=='planta':cols['ROOF'].hide_render=True
    path=ROOT/('reports/hospital_'+key+'_20261015.png');assert not path.exists()
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True,scene=scene.name);renders.append(str(path))
    cols['ROOF'].hide_render=False
scene.frame_set(1);scene.camera=inside
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
assert state_hash(object_state(original))==before
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report={'scene':SCENE,'master':str(MASTER),'sceneObjects':len(scene.objects),'exportedObjects':len(exported),
        'collections':[c.name for c in cols.values()],'materials':[m.name for m in mats.values()],
        'glb':str(OUT),'glbBytes':OUT.stat().st_size,'glbSha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'preservedObjects':len(original),'originalStoredStateBefore':before,'originalStoredStateAfter':state_hash(object_state(original)),
        'moduleWidthMeters':36,'moduleDepthMeters':24,'clearCorridorMeters':3.2,'publicDoorClearOpeningMeters':2.4,
        'roomDoorOpeningMeters':1.6,'walkCheckRadiusMeters':.4,'walkSamples':samples,'walkPathFailures':failures,
        'walkPathsBlenderXY':paths,'openDoorObstaclesBlenderXY':boxes,'previews':renders,
        'status':'saved-and-exported-awaiting-render-and-roundtrip-review',
        'limitations':['Separate module preview, not integrated into the playable city','No medical/architectural compliance certified','Four room shells and basic furniture; no complete hospital or clinical simulation','Shared character reference excluded from exported GLB']}
(ROOT/'reports/HOSPITAL_RECEPTION_20261015.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PREP_HOSPITAL_CREATED '+json.dumps({k:v for k,v in report.items() if k not in ('openDoorObstaclesBlenderXY','walkPathsBlenderXY')},ensure_ascii=False))
