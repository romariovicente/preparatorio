"""Articulate the supplied Kawasaki in an independent Blender process.

Keep every source triangle, material and UV. Identify whole disconnected
wheel components and original metal brake rotors, not box-cut body regions.
Correct the supplied leaning pose by rear-axle geometry and the wheelbase.
"""
from pathlib import Path
import bpy,json,math,hashlib,struct,importlib.util
import numpy as np
from mathutils import Vector,Matrix,Quaternion

ROOT=Path(__file__).resolve().parents[1]
SOURCE_ID='SUP_cyberpunk_kawasaki_ninja'
ASSET='VEH_Kawasaki_Interactive_20261007'
SOURCE=ROOT/'frontend/public/assets/supplied'/(SOURCE_ID+'.glb')
GLB=ROOT/'frontend/public/assets/vehicles'/(ASSET+'.glb')
BLEND=ROOT/'art/blender/PREPARATORIO_MOTORCYCLE_INTERACTIVE_20261007.blend'
REPORT=ROOT/'reports/motorcycle_interactive_validation_20261007.json'
CATALOG=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
record=next(a for a in CATALOG if a['id']==SOURCE_ID)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=record['sha256']:raise RuntimeError('Supplied source hash changed')
for path in (GLB,BLEND,REPORT):
    if path.exists():raise FileExistsError('Preserve existing motorcycle revision '+str(path))
spec=importlib.util.spec_from_file_location('car_topology',ROOT/'scripts/prep_articulate_cars.py')
topology=importlib.util.module_from_spec(spec);spec.loader.exec_module(topology)
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene=bpy.context.scene;scene.name='PREP_KAWASAKI_INTERACTIVE'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
collection=bpy.data.collections.new('PREP_KAWASAKI_REAL_PARTS');scene.collection.children.link(collection)
bpy.ops.import_scene.gltf(filepath=str(SOURCE));bpy.context.view_layer.update()
source=next(o for o in scene.objects if o.type=='MESH')
components,coords=topology.islands(source)
rubber=[c for c in components if c['materials']=={'1004'}]
tires=[c for c in rubber if 600<=len(c['polys'])<1000]
if len(tires)!=2:raise RuntimeError('Exactly two original whole tire components required')
front=max(tires,key=lambda c:c['center'].y);rear=min(tires,key=lambda c:c['center'].y)
front_center=front['center'].copy();rear_center=rear['center'].copy()
def plane_axis(comp):
    points=np.asarray([list(coords[i]) for i in comp['verts']]);center=points.mean(axis=0)
    _,vectors=np.linalg.eigh(np.cov((points-center).T));axis=Vector(vectors[:,0].tolist()).normalized()
    if axis.x<0:axis=-axis
    return axis
# Brake rotors are actual disconnected planar circles centered at each axle.
rear_rotor=next(c for c in components if c['materials']=={'1003'} and 3100<len(c['polys'])<3300 and c['center'].y<-.02)
axle=plane_axis(rear_rotor)
forward=(front_center-rear_center);forward=(forward-axle*forward.dot(axle)).normalized()
up=axle.cross(forward).normalized()
if up.z<0:up=-up;axle=-axle
rotation=Matrix((-axle,-forward,up))
if abs(rotation.determinant()-1)>.001:raise RuntimeError('Frame must preserve handedness')
rotated=[rotation@p for p in coords]
lo=Vector(tuple(min(p[i] for p in rotated) for i in range(3)));hi=Vector(tuple(max(p[i] for p in rotated) for i in range(3)))
scale=1.3/(hi.z-lo.z);origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
normalize=lambda p:(rotation@p-origin)*scale
def empty(name,parent=None,pos=(0,0,0),q=None):
    obj=bpy.data.objects.new(name,None);collection.objects.link(obj);obj.parent=parent;obj.location=pos
    obj.rotation_mode='QUATERNION'
    if q:obj.rotation_quaternion=q
    obj['asset_node_name']=name
    return obj
root=empty(ASSET);root['source_id']=SOURCE_ID;root['canonical_forward_gltf']='+Z'
root['source_credit']=json.dumps(record['credits'],ensure_ascii=False)
body=empty('Motorcycle_Body',root)
fork_components=[c for c in components if c['materials']=={'1003'} and c['min'].y>.01 and c['max'].z>.033 and c['max'].z-c['min'].z>.019 and 300<len(c['polys'])<500]
if len(fork_components)!=4:raise RuntimeError('Four natural fork tube components required')
fork_top=Vector(tuple(sum(c['max'][i] if i==2 else c['center'][i] for c in fork_components)/len(fork_components) for i in range(3)))
head=normalize(fork_top)
steering_axis=(head-normalize(front_center)).normalized()
steering=empty('Steering_F',root,head,Vector((0,0,1)).rotation_difference(steering_axis))
steering['steering_axis_local_gltf']='Y';steering['steering_limit_radians']=.42
steering['steering_method']='Whole source fork tubes and connected handlebar/control components, rotating around the sloped steering head'
bpy.context.view_layer.update()
wheel_groups={};wheel_centers={'F':front_center,'R':rear_center}
for side,tire in [('F',front),('R',rear)]:
    parent=steering if side=='F' else root
    axis=rotation@plane_axis(tire)
    if axis.x<0:axis=-axis
    local_axis=parent.matrix_world.to_quaternion().inverted()@axis
    q=Vector((1,0,0)).rotation_difference(local_axis)
    wheel=empty('Wheel_'+side,parent,parent.matrix_world.inverted()@normalize(wheel_centers[side]),q)
    wheel['rotation_axis_local_gltf']='X';wheel['radius_m']=max(tire['max'].y-tire['min'].y,tire['max'].z-tire['min'].z)*scale/2
    wheel_groups[side]=wheel
    bpy.context.view_layer.update()
labels={i:'Motorcycle_Body' for i in range(len(source.data.polygons))}
wheel_components={side:[] for side in ('F','R')};steering_components=[]
for comp in components:
    label='Motorcycle_Body';center=comp['center']
    if comp['materials']=={'1004'}:
        side=min(wheel_centers,key=lambda side:(center-wheel_centers[side]).length)
        label='Wheel_'+side;wheel_components[side].append(comp)
    elif comp['materials']=={'1003'} and 1300<len(comp['polys'])<3700 and (comp['max'].z-comp['min'].z)<.014 and (center.y<-.02 or center.y>.025):
        side=min(wheel_centers,key=lambda side:(center-wheel_centers[side]).length)
        label='Wheel_'+side;wheel_components[side].append(comp)
    elif comp in fork_components or (comp['materials']=={'1003'} and comp['min'].y>.01 and comp['min'].z>.033):
        label='Steering_F';steering_components.append(comp)
    for index in comp['polys']:labels[index]=label
groups={'Motorcycle_Body':body,'Steering_F':steering,'Wheel_F':wheel_groups['F'],'Wheel_R':wheel_groups['R']}
stats={}
source_normals=source.data.corner_normals
for name,parent in groups.items():
    polygon_indices=[i for i,label in labels.items() if label==name]
    polygons=[source.data.polygons[i] for i in polygon_indices]
    old_vertices=sorted({v for p in polygons for v in p.vertices});remap={old:new for new,old in enumerate(old_vertices)}
    inverse=parent.matrix_world.inverted();positions=[inverse@normalize(coords[i]) for i in old_vertices]
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(positions,[],[tuple(remap[i] for i in p.vertices) for p in polygons]);mesh.update()
    for mat in source.data.materials:mesh.materials.append(mat)
    for new,old in zip(mesh.polygons,polygons):new.material_index=old.material_index;new.use_smooth=old.use_smooth
    loop_indices=[i for p in polygons for i in p.loop_indices]
    for old_uv in source.data.uv_layers:
        uv=mesh.uv_layers.new(name=old_uv.name)
        for new,old in enumerate(loop_indices):uv.data[new].uv=old_uv.data[old].uv
    normal_matrix=inverse.to_3x3()@rotation@source.matrix_world.to_3x3().inverted().transposed()
    mesh.normals_split_custom_set([(normal_matrix@source_normals[i].vector).normalized() for i in loop_indices])
    obj=bpy.data.objects.new(name+'_Geometry',mesh);collection.objects.link(obj);obj.parent=parent
    obj['source_faces']=len(polygons);obj['materials_uv_preserved']=True
    stats[name]={'triangles':sum(len(p.vertices)-2 for p in polygons),'vertices':len(old_vertices),'sourceConnectedComponents':sum(1 for c in components if labels[c['polys'][0]]==name)}
bpy.data.objects.remove(source,do_unlink=True)
bpy.context.view_layer.update()
total=sum(row['triangles'] for row in stats.values())
if total!=record['triangles']:raise RuntimeError('Every original triangle must occur exactly once')
for image in bpy.data.images:
    if image.type!='RENDER_RESULT' and image.has_data:
        try:image.pack()
        except RuntimeError:pass
GLB.parent.mkdir(parents=True,exist_ok=True);BLEND.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in collection.objects:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,
    export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_materials='EXPORT',export_draco_mesh_compression_enable=False)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
validation=bpy.data.scenes.new('VERIFY_REAL_MOTORCYCLE');bpy.context.window.scene=validation
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(GLB));bpy.context.view_layer.update()
imported=[o for o in bpy.data.objects if o not in before];meshes=[o for o in imported if o.type=='MESH']
actual=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
finite=all(math.isfinite(value) for o in meshes for v in o.data.vertices for value in v.co)
points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
vlo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
vhi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
if actual!=total or not finite or abs(vlo.z)>.002:raise RuntimeError('Actual GLB reimport geometry validation failed')
wheel_tests={}
for side in ('F','R'):
    wheel=next(o for o in imported if o.get('asset_node_name')=='Wheel_'+side)
    child=next(o for o in wheel.children_recursive if o.type=='MESH');pivot=wheel.matrix_world.translation.copy()
    points_before=[child.matrix_world@v.co for v in child.data.vertices]
    axis_before=wheel.matrix_world.to_quaternion()@Vector((1,0,0))
    radial_before=max((p-pivot).cross(axis_before).length for p in points_before)
    old=wheel.rotation_quaternion.copy();wheel.rotation_quaternion=old@Quaternion(Vector((1,0,0)),math.pi/2)
    bpy.context.view_layer.update();points_after=[child.matrix_world@v.co for v in child.data.vertices]
    center_delta=(wheel.matrix_world.translation-pivot).length
    radial_after=max((p-pivot).cross(axis_before).length for p in points_after)
    displacement=max((a-b).length for a,b in zip(points_after,points_before))
    if center_delta>1e-5 or abs(radial_before-radial_after)>.002 or displacement<.1:raise RuntimeError('Wheel rotation must actually move vertices around its stationary axle')
    wheel_tests[side]={'passed':True,'triangles':stats['Wheel_'+side]['triangles'],'centerDisplacementMeters':center_delta,
      'radiusBeforeAfter':[radial_before,radial_after],'maxVertexDisplacementAt90Degrees':displacement,'rotationAxis':'local X','radiusMeters':wheel['radius_m']}
    wheel.rotation_quaternion=old
blob=GLB.read_bytes();n,_=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+n])
report={'date':'2026-10-07','blenderVersion':bpy.app.version_string,'source':{'id':SOURCE_ID,'sha256':record['sha256'],'unchanged':sha(SOURCE)==record['sha256'],'credits':record['credits']},
  'glb':{'path':str(GLB),'url':'/assets/vehicles/'+GLB.name,'bytes':GLB.stat().st_size,'sha256':sha(GLB),'scenes':len(doc['scenes']),'meshes':len(doc['meshes']),'embeddedImages':len(doc.get('images',[]))},
  'blend':{'path':str(BLEND),'bytes':BLEND.stat().st_size,'sha256':sha(BLEND)},'parts':stats,'sourceTriangles':record['triangles'],'derivedTriangles':total,
  'allSourceFacesPreservedOnce':True,'heightMeters':1.3,'dimensionsBlenderXYZ':list(vhi-vlo),'feetZ':vlo.z,'canonicalForwardGltf':'+Z','forwardSign':1,
  'actualReimport':{'passed':True,'meshes':len(meshes),'triangles':actual,'allVerticesFinite':finite},'wheelRotationValidation':wheel_tests,
  'steering':{'node':'Steering_F','localRotationAxisGltf':'Y','headBlenderXYZ':list(head),'axisBlenderXYZ':list(steering_axis),'forkWholeComponents':len(fork_components),'additionalOriginalComponents':len(steering_components)},
  'render':{'closed':str(ROOT/'reports'/(ASSET+'_neutral.png')),'steeringWheels90':str(ROOT/'reports'/(ASSET+'_steering_wheels90.png')),'visualReviewPending':True},
  'liveBlenderTouched':False,'frontendConfigChanged':False}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('MOTORCYCLE_FILES_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
bpy.context.window.scene=scene
world=bpy.data.worlds.new('Motorcycle_Review_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.27,.3,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;scene.world=world
for name,pos,energy in [('Key',(3,-3,5),900),('Fill',(-3,-2,3),600),('Rim',(2,3,4),1000)]:
    light=bpy.data.lights.new('REVIEW_'+name,'AREA');light.energy=energy;light.size=4
    obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,0,.6))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('REVIEW_Motorcycle_Camera');camera.lens=52
cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);cam.location=(3.2,-4.3,2.1);cam.rotation_euler=(Vector((0,0,.65))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=576;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.render.filepath=report['render']['closed'];bpy.ops.render.render(write_still=True)
steering.rotation_quaternion=steering.rotation_quaternion@Quaternion(Vector((0,0,1)),.38)
for wheel in wheel_groups.values():wheel.rotation_quaternion=wheel.rotation_quaternion@Quaternion(Vector((1,0,0)),math.pi/2)
scene.render.filepath=report['render']['steeringWheels90'];bpy.ops.render.render(write_still=True)
print('MOTORCYCLE_VISUAL_PROOF_SAVED',flush=True)
