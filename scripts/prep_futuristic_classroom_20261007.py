"""Additive standalone classroom with original Mixamo Remy skins and seated rigs.

Run in independent Blender background. User assets and the live Blender are never
modified. A repeat refuses completed outputs so earlier deliveries are preserved.
"""
from pathlib import Path
import bpy, math, json, hashlib, struct
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'frontend/public/assets/characters/CHR_Remy_Mixamo_20261005.glb'
BLEND=ROOT/'art/blender/PREPARATORIO_CLASSROOM_FUTURISTIC_20261007.blend'
ARCH=ROOT/'frontend/public/assets/environments/ENV_Classroom_Futuristic_20261007.glb'
NPC=ROOT/'frontend/public/assets/environments/NPC_Classroom_Remy_20261007.glb'
REPORT=ROOT/'reports/classroom_futuristic_validation_20261007.json'
PREVIEW=ROOT/'reports/classroom_futuristic_20261007.png'
for p in (BLEND,ARCH,NPC,REPORT):
    if p.exists():raise FileExistsError('Preserve existing delivery: '+str(p))
for p in (BLEND,ARCH,NPC,REPORT,PREVIEW):p.parent.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_sha=sha(SOURCE)
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
scene=bpy.context.scene;scene.name='PREP_CLASSROOM_FUTURISTIC_20261007'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.fps=30;scene.frame_start=scene.frame_end=1
def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
architecture=collection('PREP_CLASSROOM_ARCHITECTURE')
furniture=collection('PREP_CLASSROOM_FURNITURE')
education=collection('PREP_CLASSROOM_EDUCATIONAL')
students=collection('PREP_CLASSROOM_REAL_STUDENTS')
review=collection('PREP_CLASSROOM_REVIEW_LIGHTS')
def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o);return o
def mat(name,color,rough=.5,metal=0,emission=0,glass=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    if glass:p.inputs['Transmission Weight'].default_value=.94;p.inputs['IOR'].default_value=1.46
    return m
M={'porcelain':mat('MAT_Classroom_Porcelain',(.72,.77,.79),.28),
   'graphite':mat('MAT_Classroom_Graphite',(.027,.042,.064),.31,.5),
   'steel':mat('MAT_Classroom_BrushedSteel',(.24,.29,.33),.32,.88),
   'wood':mat('MAT_Classroom_WarmOak',(.34,.21,.12),.48),
   'fabric':mat('MAT_Classroom_SeatFabric',(.055,.20,.26),.84),
   'floor':mat('MAT_Classroom_Terrazzo',(.42,.47,.50),.48),
   'cyan':mat('MAT_Classroom_CyanLED',(.03,.78,1),.22,.15,3),
   'amber':mat('MAT_Classroom_AmberLED',(1,.47,.08),.28,.1,1.6),
   'white':mat('MAT_Classroom_Text',(.80,.96,1),.4,0,.6),
   'glass':mat('MAT_Classroom_WindowGlass',(.70,.89,.92),.12,.05,glass=True),
   'display':mat('MAT_Classroom_Display',(.006,.026,.047),.25,.12),
   'leaf':mat('MAT_Classroom_PlantLeaf',(.055,.22,.09),.7)}
def finish(o,name,material,c,bevel=0):
    o.name=name
    if o.type=='MESH':
        o.data.name=name+'_Mesh';o.data.materials.append(M[material])
        for p in o.data.polygons:p.use_smooth=True
        if bevel:
            mod=o.modifiers.new('Realistic edge radius','BEVEL');mod.width=bevel;mod.segments=3
            mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    move(o,c);o['prep_authorship']='Romario Vicente Amaro';return o
def box(name,location,size,material,c=architecture,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);o=bpy.context.object
    # New architecture only: size in mesh coordinates, no hierarchy transforms.
    for v in o.data.vertices:v.co.x*=size[0];v.co.y*=size[1];v.co.z*=size[2]
    return finish(o,name,material,c,bevel)
def cylinder(name,location,radius,depth,material,c=furniture,vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=location)
    return finish(bpy.context.object,name,material,c,.008)
def rod(name,start,end,radius,material,c=furniture):
    a,b=Vector(start),Vector(end);o=cylinder(name,(a+b)/2,radius,(b-a).length,material,c,20)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def text(name,body,location,size,material='white',c=education):
    data=bpy.data.curves.new(name+'_Font','FONT');data.body=body;data.size=size;data.align_x='CENTER';data.extrude=.0008
    o=bpy.data.objects.new(name,data);c.objects.link(o);o.location=location;o.rotation_euler=(math.pi/2,0,math.pi)
    data.materials.append(M[material]);return o
def shell(name,x,y,material,back=False):
    # Continuous gently curved upholstery shell, rather than a cube seat.
    verts=[];faces=[];nu,nv=20,12
    for j in range(nv+1):
        v=j/nv
        for i in range(nu+1):
            u=(i/nu-.5)*.55
            if back:verts.append((x+u,y+.235+.035*(2*u/.55)**2+.11*v*v,.47+.55*v))
            else:verts.append((x+u,y+(v-.5)*.51,.45+.025*(2*u/.55)**2-.009*math.sin(v*math.pi)))
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i;faces.append((a,a+1,a+nu+2,a+nu+1))
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);furniture.objects.link(o);mesh.materials.append(M[material])
    for p in mesh.polygons:p.use_smooth=True
    s=o.modifiers.new('Upholstery thickness','SOLIDIFY');s.thickness=.055
    b=o.modifiers.new('Soft shell edges','BEVEL');b.width=.018;b.segments=3
    return o

# Full size 14 x 12 m room, doorway, glazed side walls and an open central skylight.
box('MOD_Classroom_Floor',(0,0,-.10),(14,12,.20),'floor')
for x in range(-6,7,2):box('MOD_Floor_Inlay_'+str(x),(x,0,.003),(.012,11.8,.006),'steel',bevel=0)
box('BLD_Classroom_FrontWall',(0,-5.92,1.88),(14,.16,3.76),'porcelain')
box('BLD_Classroom_RearWallLeft',(-1.65,5.92,1.88),(10.7,.16,3.76),'porcelain')
box('BLD_Classroom_RearWallRight',(6.72,5.92,1.88),(.56,.16,3.76),'porcelain')
box('BLD_Classroom_DoorLintel',(5.53,5.92,3.12),(1.8,.18,1.28),'porcelain')
for sign in (-1,1):
    x=sign*6.92
    box('MOD_GlassWall_'+str(sign),(x,0,1.98),(.08,11.75,3.25),'glass')
    for y in (-5.7,-3.0,0,3,5.7):box('MOD_WindowMullion_'+str((sign,y)),(x,y,1.98),(.16,.10,3.56),'graphite')
    for z in (.28,3.68):box('MOD_WindowRail_'+str((sign,z)),(x,0,z),(.14,11.9,.14),'graphite')
    box('MOD_CeilingSide_'+str(sign),(sign*6.0,0,3.84),(2,12,.16),'porcelain')
    box('MOD_CeilingLED_'+str(sign),(sign*5.18,0,3.70),(.06,11.3,.028),'cyan',bevel=.008)
    box('MOD_LowWallBench_'+str(sign),(sign*6.64,0,.24),(.45,11.5,.46),'graphite')
for y in (-5.86,5.86):box('MOD_RoofFrame_'+str(y),(0,y,3.84),(14,.25,.24),'graphite')
door=box('MOD_Classroom_Door',(5.53,5.92,1.22),(1.63,.06,2.4),'glass')
door['interaction']='hinged_door';door['openingAngleDegrees']=85
for x in (4.65,6.41):box('MOD_Classroom_DoorFrame_'+str(x),(x,5.92,1.23),(.095,.16,2.46),'steel')
rod('PROP_Classroom_DoorHandle',(6.12,5.79,.97),(6.12,5.79,1.25),.022,'steel',architecture)
text('SIGN_Classroom','SALA DE AULA • PREPARATÓRIO',(0,-5.815,3.24),.33,'graphite')
text('SIGN_Author','Autoria: Romario Vicente Amaro',(0,-5.812,.31),.16,'graphite')
text('SIGN_Exit','SAÍDA',(5.53,5.81,2.79),.20,'graphite')

# Curved ergonomic desks, upholstered seats, real proportions and cable details.
positions=[(x,y) for y in (-2.05,.10,2.25,4.40) for x in (-4,0,4)]
for index,(x,y) in enumerate(positions,1):
    prefix='PROP_Desk_%02d'%index;dy=y-.73
    box(prefix+'_Top',(x,dy,.76),(1.35,.78,.07),'wood',furniture,.085)
    for sx in (-.53,.53):
        rod(prefix+'_Leg',(x+sx,dy,.045),(x+sx,dy,.72),.030,'steel')
        box(prefix+'_Foot',(x+sx,dy,.035),(.09,.54,.035),'graphite',furniture,.018)
    box(prefix+'_LED',(x,dy-.38,.749),(1.18,.018,.018),'cyan',furniture,.006)
    tablet=box(prefix+'_Tablet',(x+.34,dy,.818),(.37,.255,.018),'graphite',furniture,.018)
    tablet.rotation_euler.x=.08
    box(prefix+'_TabletScreen',(x+.34,dy,.829),(.32,.21,.004),'display',furniture,.012)
    for k in range(3):box(prefix+'_ScreenLine_'+str(k),(x+.34,dy-.06+k*.041,.832),(.23,.009,.002),'cyan',furniture,.003)
    chair='PROP_Chair_%02d'%index;shell(chair+'_Seat',x,y,'fabric');shell(chair+'_Back',x,y,'fabric',True)
    cylinder(chair+'_GasLift',(x,y,.23),.04,.39,'steel')
    cylinder(chair+'_BaseHub',(x,y,.075),.08,.06,'graphite')
    for k in range(5):
        a=k*math.tau/5
        rod(chair+'_Star_'+str(k),(x,y,.09),(x+.32*math.cos(a),y+.32*math.sin(a),.055),.021,'steel')
        wheel=cylinder(chair+'_Caster_'+str(k),(x+.32*math.cos(a),y+.32*math.sin(a),.048),.048,.032,'graphite',vertices=20)
        wheel.rotation_euler.y=math.pi/2

box('EDU_Hologram_Bezel',(0,-5.69,2.03),(6.7,.12,1.92),'graphite',education,.095)
box('EDU_Hologram_Display',(0,-5.611,2.03),(6.46,.025,1.71),'display',education,.06)
for x in (-3.28,3.28):box('EDU_Hologram_LED_'+str(x),(x,-5.584,2.03),(.025,.018,1.70),'cyan',education,.006)
text('EDU_Hologram_Title','ANATOMIA • CONHECIMENTO • CUIDADO',(0,-5.58,2.55),.25)
text('EDU_Hologram_Lesson','Aula de enfermagem: aprender para cuidar',(0,-5.579,2.11),.20)
text('EDU_Hologram_Status','JARVIS-IA | CHRONOVITAE | AMBIENTE DIDÁTICO',(0,-5.578,1.38),.16,'cyan')
for x in (-2.8,2.8):
    for z in (1.68,1.9,2.12):box('EDU_Hologram_Data_'+str((x,z)),(x,-5.576,z),(.37,.012,.014),'cyan',education,.004)
box('PROP_Lecturer_Desk',(0,-4.29,.78),(2.0,.76,.09),'wood',furniture,.075)
for x in (-.82,.82):box('PROP_Lecturer_Support_'+str(x),(x,-4.29,.385),(.12,.64,.77),'steel',furniture)
for x in (-5.7,5.7):
    cylinder('PROP_PlantPot_'+str(x),(x,-4.7,.24),.25,.48,'porcelain',architecture)
    for k in range(7):
        a=k*math.tau/7
        rod('PROP_PlantStem_'+str((x,k)),(x,-4.7,.48),(x+.28*math.cos(a),-4.7+.28*math.sin(a),1.05+.13*(k%3)),.012,'leaf',architecture)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=(x+.25*math.cos(a),-4.7+.25*math.sin(a),1.05+.13*(k%3)))
        o=bpy.context.object
        for v in o.data.vertices:v.co.x*=.105;v.co.y*=.055;v.co.z*=.26
        o.rotation_euler=(.45*math.sin(a),.45*math.cos(a),a);finish(o,'PROP_PlantLeaf_'+str((x,k)),'leaf',architecture)

# Import the genuine textured character, not an approximation made from primitives.
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(SOURCE));imported=[o for o in bpy.data.objects if o not in before]
arm=next(o for o in imported if o.type=='ARMATURE')
root=arm
while root.parent:root=root.parent
character=[root]+list(root.children_recursive)
source_meshes=[o for o in character if o.type=='MESH']
if len(source_meshes)!=7:raise RuntimeError('Unexpected genuine Remy hierarchy')
for o in imported:
    if o not in character:bpy.data.objects.remove(o,do_unlink=True)
for o in character:move(o,students)
arm.animation_data_clear()
for p in arm.pose.bones:
    p.rotation_mode='QUATERNION';p.rotation_quaternion=(1,0,0,0);p.location=(0,0,0);p.scale=(1,1,1)
bpy.context.view_layer.update()
world_rot=arm.matrix_world.to_3x3();inv_rot=world_rot.inverted()
def bone(name):return arm.pose.bones['mixamorig:'+name]
def aim(name,child,desired_world):
    """Rotate a real joint using child joint origins, never its oversized FBX tail."""
    bpy.context.view_layer.update();p=bone(name);ch=bone(child)
    current=(ch.matrix.translation-p.matrix.translation).normalized()
    desired=(inv_rot@Vector(desired_world)).normalized()
    q=current.rotation_difference(desired)
    orientation=q.to_matrix()@p.matrix.to_3x3()
    matrix=orientation.to_4x4();matrix.translation=p.matrix.translation;p.matrix=matrix
    bpy.context.view_layer.update()

for side,sign in [('Left',1),('Right',-1)]:
    aim(side+'UpLeg',side+'Leg',(sign*.035,-1,-.09))
    aim(side+'Leg',side+'Foot',(sign*.01,.018,-1))
    aim(side+'Foot',side+'ToeBase',(0,-1,-.045))
    aim(side+'Arm',side+'ForeArm',(sign*.10,-.22,-1))
    aim(side+'ForeArm',side+'Hand',(-sign*.12,-.55,-.83))
hip_world=arm.matrix_world@bone('Hips').matrix.translation
root.location+=Vector((0,.018,.55))-hip_world
bpy.context.view_layer.update()
def evaluated_bounds(objects):
    deps=bpy.context.evaluated_depsgraph_get();points=[]
    for o in objects:
        if o.type!='MESH':continue
        e=o.evaluated_get(deps);m=e.to_mesh()
        points.extend(e.matrix_world@v.co for v in m.vertices);e.to_mesh_clear()
    return Vector(tuple(min(p[i] for p in points) for i in range(3))),Vector(tuple(max(p[i] for p in points) for i in range(3)))
lo,hi=evaluated_bounds(source_meshes)
root.location.z+=.012-lo.z
bpy.context.view_layer.update()
lo,hi=evaluated_bounds(source_meshes)
if hi.z-lo.z>1.6 or lo.z<-.002:raise RuntimeError('Seated pose has unexpected bounds')
base_position=root.location.copy();template=character
rigs=[];npc_records=[]
for index,(x,y) in enumerate(positions,1):
    if index==1:copies={o:o for o in template}
    else:
        copies={}
        for o in template:
            n=o.copy()
            if o.type=='ARMATURE':n.data=o.data.copy()
            students.objects.link(n);copies[o]=n
        for original,n in copies.items():
            n.parent=copies.get(original.parent)
            if n.type=='MESH':
                for mod in n.modifiers:
                    if mod.type=='ARMATURE':mod.object=copies[arm]
    r=copies[root];a=copies[arm];r.name='NPC_Classroom_Remy_%02d'%index
    r.location=base_position+Vector((x,y,0));r['pose']='Seated classroom student';r['role']='student';r['source']='Genuine Adobe Mixamo Remy'
    a.name='RIG_Classroom_Remy_%02d'%index;a['pose_name']='Seated_Classroom_20261007'
    for original,n in copies.items():
        if n.type=='MESH':n.name='NPC_Remy_%02d_%s'%(index,original.data.name)
    rigs.append(a)
    bpy.context.view_layer.update()
    hips=a.matrix_world@a.pose.bones['mixamorig:Hips'].matrix.translation
    k=a.matrix_world@a.pose.bones['mixamorig:LeftLeg'].matrix.translation
    f=a.matrix_world@a.pose.bones['mixamorig:LeftFoot'].matrix.translation
    npc_records.append({'student':index,'rig':a.name,'bones':len(a.data.bones),'hipsWorldBlender':list(hips),'kneeWorldBlender':list(k),'ankleWorldBlender':list(f)})

# Save the complete editable scene before slower exports and rendering.
scene['authorship']='Romario Vicente Amaro';scene['source_remy_sha256']=source_sha
scene['notes']='Twelve linked genuine Remy students; manually authored seated skeletal pose. Original textures/UV/skin unchanged.'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print('CLASSROOM_BLEND_SAVED '+str(BLEND),flush=True)
def export(path,objects,skinned=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    if not objects:raise RuntimeError('Nothing selected')
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,
      export_extras=True,export_animations=False,export_current_frame=True,export_rest_position_armature=False,
      export_apply=not skinned,export_materials='EXPORT',export_cameras=False,export_lights=False)
arch_objects=[o for c in (architecture,furniture,education) for o in c.objects]
export(ARCH,arch_objects);print('CLASSROOM_ARCH_GLB_SAVED',flush=True)
export(NPC,list(students.objects),True);print('CLASSROOM_NPC_GLB_SAVED',flush=True)
collection_names=[c.name for c in (architecture,furniture,education,students)]
def glb_doc(path):
    raw=path.read_bytes();length,kind=struct.unpack_from('<II',raw,12)
    if kind!=0x4e4f534a or struct.unpack_from('<I',raw,8)[0]!=len(raw):raise RuntimeError('Invalid generated GLB')
    return json.loads(raw[20:20+length])
validations=[]
for path,expected_arms in ((ARCH,0),(NPC,12)):
    # A genuinely clean reimport avoids dependency-graph references to the
    # twelve original rigs, whose linked source data have identical bone names.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    check=bpy.context.scene;check.name='VALIDATION_'+path.stem
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
    objects=[o for o in bpy.data.objects if o not in before];arms=[o for o in objects if o.type=='ARMATURE']
    # Blender creates display-only bone Icospheres while importing each rig.
    # They are not GLB nodes or character geometry and are excluded explicitly.
    shape_objects={p.custom_shape for arm in arms for p in arm.pose.bones if p.custom_shape}
    meshes=[o for o in objects if o.type=='MESH' and o not in shape_objects]
    finite=all(math.isfinite(c) for o in meshes for v in o.data.vertices for c in v.co)
    triangles=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
    if not finite or not triangles or len(arms)!=expected_arms:raise RuntimeError('Actual GLB reimport failed')
    a,b=evaluated_bounds(meshes);doc=glb_doc(path)
    validation={'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'gltfNodes':len(doc['nodes']),'gltfMeshes':len(doc['meshes']),'gltfSkins':len(doc.get('skins',[])),
      'gltfMaterials':len(doc.get('materials',[])),'embeddedImages':len(doc.get('images',[])),'actualReimport':{'passed':True,'meshObjects':len(meshes),'armatures':len(arms),'triangles':triangles,'allVerticesFinite':finite,'evaluatedBoundsMinBlender':list(a),'evaluatedBoundsMaxBlender':list(b),'importerBoneDisplayShapesExcluded':len(shape_objects)}}
    if expected_arms:
        print('NPC_REIMPORT_TOTAL_BOUNDS '+json.dumps({'min':list(a),'max':list(b),'meshNames':[o.name for o in meshes]}),flush=True)
        if a.z<-.015 or b.z>1.65:raise RuntimeError('GLB lost seated pose')
        validation['seatedPosePreservedOnReimport']=True
        validation['skinWeightsPresent']=all(len(o.vertex_groups)>0 for o in meshes)
    validations.append(validation)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene;review=bpy.data.collections['PREP_CLASSROOM_REVIEW_LIGHTS']
if sha(SOURCE)!=source_sha:raise RuntimeError('Source unexpectedly changed')
report={'date':'2026-10-07','blenderVersion':bpy.app.version_string,'authorship':'Romario Vicente Amaro',
 'blend':{'path':str(BLEND),'bytes':BLEND.stat().st_size,'sha256':sha(BLEND)},'source':{'path':str(SOURCE),'sha256':source_sha,'unchanged':True},
 'roomSizeMeters':[14,12,3.84],'collections':collection_names,
 'students':12,'desks':12,'chairs':12,'rigPoseMethod':'Real Mixamo joint direction rotations using child bone origins, preserving skin/UV/materials. No primitive humanoids.',
 'studentPoseRecords':npc_records,'assets':validations,'render':{'path':str(PREVIEW),'visualReviewPending':True},
 'limitations':['All twelve students use the same licensed Remy character; distinct people/clothing not claimed.','The seated pose is a static skeletal pose, not a new Mixamo sitting animation.','Central roof skylight is open for an interior view; classroom doorway interaction metadata does not implement game controls.','JARVIS educational panel is geometry and Portuguese text; backend knowledge connection is handled by the game.'],
 'liveBlenderTouched':False,'frontendCodeChanged':False}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('CLASSROOM_REIMPORT_VALIDATED '+str(REPORT),flush=True)
world=bpy.data.worlds.new('Classroom_Review_World');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.38,.47,.58,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45;scene.world=world
for name,pos,energy,size in [('Key',(0,0,7),2400,7),('Front',(-2,-4,4),1300,5),('Rim',(4,4,5),1500,4)]:
    data=bpy.data.lights.new('REVIEW_'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(data.name,data);review.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('REVIEW_Classroom_Camera');data.lens=35
camera=bpy.data.objects.new(data.name,data);review.objects.link(camera);camera.location=(5.6,5.0,3.3);data.lens=22
camera.rotation_euler=(Vector((0,-1.2,1.1))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=576;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.render.filepath=str(PREVIEW)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
report['blend'].update(bytes=BLEND.stat().st_size,sha256=sha(BLEND));REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
bpy.ops.render.render(write_still=True)
print('CLASSROOM_RENDER_SAVED '+str(PREVIEW),flush=True)
