"""Finish an interrupted generated revision after checking its actual files."""
from pathlib import Path
import bpy,json,struct,re,hashlib,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
BLEND=ROOT/'art/blender/PREPARATORIO_CARS_INTERACTIVE_20261005.blend'
REPORT=ROOT/'reports/cars_interactive_validation_20261005.json'
cat=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(name):return re.sub(r'\.\d+$','',name)
def bounds(objects):
    bpy.context.view_layer.update()
    pts=[o.matrix_world@Vector(v) for o in objects if o.type=='MESH' for v in o.bound_box]
    return Vector(tuple(min(v[i] for v in pts) for i in range(3))),Vector(tuple(max(v[i] for v in pts) for i in range(3)))
def tris(objects):return sum(len(p.vertices)-2 for o in objects if o.type=='MESH' for p in o.data.polygons)
if BLEND.exists() or REPORT.exists():raise FileExistsError('Completed revision already exists; preserve it')
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
initial=bpy.context.scene
scenes=[];results=[]
for source_id,asset_id,height,rotation in [
    ('SUP_2010_mercedes_sls_amg','VEH_SLS_Interactive_20261005',1.260,0),
    ('SUP_volkswagen_atlas_teramont_cross_sport_2025','VEH_Atlas_Interactive_20261005',1.733,180)]:
    file=ROOT/'frontend/public/assets/vehicles'/(asset_id+'.glb')
    if not file.exists():raise FileNotFoundError(str(file))
    data=file.read_bytes();n,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+n])
    existing_sha=sha(file)
    for node in doc['nodes']:
        if re.match(r'^(Wheel|Door|Glass)_(FL|FR|RL|RR)(\.\d+)?$',node.get('name','')) or node.get('name','').startswith('Windshield'):
            node['name']=canonical(node['name']);node.setdefault('extras',{})['asset_node_name']=node['name']
    required=['Wheel_'+s for s in ('FL','FR','RL','RR')]+['Glass_'+s for s in (('FL','FR') if source_id.endswith('sls_amg') else ('FL','FR','RL','RR'))]
    if not all(name in {node.get('name') for node in doc['nodes']} for name in required):raise RuntimeError('Missing required part in generated file')
    checkpoint=ROOT/'art/blender/checkpoints/CARS_BEFORE_CANONICAL_NAME_REPAIR_20261005'
    checkpoint.mkdir(parents=True,exist_ok=True)
    original=checkpoint/file.name
    if original.exists():raise FileExistsError(str(original))
    original.write_bytes(data)
    js=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4)
    tail=data[20+n:];blob=struct.pack('<4sII',b'glTF',2,20+len(js)+len(tail))+struct.pack('<II',len(js),kind)+js+tail
    file.write_bytes(blob)
    scene=bpy.data.scenes.new(asset_id);bpy.context.window.scene=scene;scenes.append(scene)
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(file));bpy.context.view_layer.update()
    objects=[o for o in bpy.data.objects if o not in before];meshes=[o for o in objects if o.type=='MESH']
    groups={o.get('asset_node_name',canonical(o.name)):o for o in objects if o.type=='EMPTY'}
    for name,group in groups.items():group['asset_node_name']=name
    catalog=next(a for a in cat if a['id']==source_id)
    source=ROOT/'frontend/public'/catalog['url'].lstrip('/')
    if sha(source)!=catalog['sha256']:raise RuntimeError('Original source changed')
    total=tris(meshes);lo,hi=bounds(meshes)
    finite=all(math.isfinite(value) for o in meshes for v in o.data.vertices for value in v.co)
    if total!=catalog['triangles'] or abs(lo.z)>.002 or abs(hi.z-height)>.002 or not finite:raise RuntimeError('Reimport failed real geometry checks')
    wheel_tests={}
    for side in ('FL','FR','RL','RR'):
        wheel=groups['Wheel_'+side];children=list(wheel.children_recursive)
        a,b=bounds(children);center=(a+b)/2
        wheel.rotation_euler.x+=math.pi/2;c,d=bounds(children);after=(c+d)/2
        delta=(after-center).length;wheel.rotation_euler.x-=math.pi/2
        if delta>.015 or not children:raise RuntimeError('Actual reimported wheel pivot invalid')
        wheel_tests[side]={'triangles':tris(children),'centerErrorAfter90Degrees':delta,'radiusMeters':wheel.get('radius_m'),'pivotBlenderXYZ':list(wheel.location),'passed':True}
    result={'assetId':asset_id,'source':{'id':source_id,'url':catalog['url'],'sha256':catalog['sha256'],'unchanged':True,'credits':catalog['credits']},
      'glb':{'path':str(file),'url':'/assets/vehicles/'+file.name,'sha256':sha(file),'bytes':len(blob),'scenes':len(doc['scenes']),'meshes':len(doc['meshes']),'embeddedImages':len(doc.get('images',[]))},
      'geometry':{'sourceTriangles':catalog['triangles'],'derivedTriangles':total,'allSourceFacesPreservedOnce':True},
      'dimensionsBlenderXYZ':list(hi-lo),'heightMeters':height,'feetZ':lo.z,'canonicalForwardGltf':'+Z','forwardSign':1,'sourceAppliedRotationDegrees':rotation,
      'windowNames':[name for name in required if name.startswith('Glass_')],'wheelNames':['Wheel_'+s for s in ('FL','FR','RL','RR')],
      'doorNames':['Door_'+s for s in (('FL','FR') if source_id.endswith('sls_amg') else ('FL','FR','RL','RR'))],
      'parts':{'wheelCount':4,'windowCount':2 if source_id.endswith('sls_amg') else 4,'doorSplitApproximate':source_id.endswith('sls_amg'),
        'rearAndFrontWindshieldFixed':True,'doorMethod':'SLS adapted connected hull' if source_id.endswith('sls_amg') else 'Atlas original authored interior/exterior components'},
      'actualReimport':{'passed':True,'triangles':total,'meshes':len(meshes),'allVerticesFinite':finite},'wheelRotationValidation':wheel_tests,
      'render':{'closed':str(ROOT/'reports'/(asset_id+'_closed.png')),'open':str(ROOT/'reports'/(asset_id+'_open_wheels90.png')),'visualReviewPending':True},
      'checkpointBeforeNames':str(original),'liveBlenderTouched':False,'frontendConfigChanged':False}
    if source_id.endswith('sls_amg'):
        result['visualDoorValidation']={'passed':False,'limitation':'Door hull adaptation has visibly jagged triangle boundaries when opened. Wheels and side windows are true isolated parts. Use Atlas for fully opening playable car until SLS doors are reauthored.'}
        result['readyForPlayableDoorUse']=False
    else:result['readyForPlayableDoorUse']=True
    results.append(result)

bpy.data.scenes.remove(initial)
bpy.context.window.scene=scenes[0]
BLEND.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
report={'date':'2026-10-05','blenderVersion':bpy.app.version_string,'blend':{'path':str(BLEND),'sha256':sha(BLEND),'bytes':BLEND.stat().st_size},'assets':results,'status':'Both real GLBs saved and actually reimported; SLS door geometry explicitly needs refinement.'}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SAVED_CAR_CHECKPOINT '+json.dumps(report,ensure_ascii=False),flush=True)

# Only the correct authored Atlas doors require a new visual proof. The save
# above ensures all real files remain safe even if rendering is interrupted.
scene=scenes[1];bpy.context.window.scene=scene
asset_id=scene.name
root=next(o for o in scene.objects if o.name.startswith(asset_id) and o.type=='EMPTY')
groups={o.get('asset_node_name',canonical(o.name)):o for o in scene.objects if o.type=='EMPTY'}
world=bpy.data.worlds.new('Atlas_Review_World');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.25,.3,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;scene.world=world
for name,pos,energy in [('Key',(3,-3,6),1100),('Fill',(-4,-2,4),800),('Rim',(2,4,5),1400)]:
    data=bpy.data.lights.new('REVIEW_'+name,'AREA');data.energy=energy;data.size=4
    o=bpy.data.objects.new(data.name,data);scene.collection.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,0,.9))-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('REVIEW_Atlas_Camera');data.lens=52
cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);cam.location=(6,-7,4.3)
cam.rotation_euler=(Vector((0,0,.8))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.cycles.use_denoising=True
scene.render.resolution_x=1024;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.render.filepath=results[1]['render']['closed'];bpy.ops.render.render(write_still=True)
for name,group in groups.items():
    if name.startswith('Wheel_'):group.rotation_euler.x=math.pi/2
    if name.startswith('Door_'):group.rotation_euler.z=(-1 if name.endswith('L') else 1)*1.05
    if name.startswith('Glass_'):group.location.z=-group.get('window_drop_m',.46)
scene.render.filepath=results[1]['render']['open'];bpy.ops.render.render(write_still=True)
print('ATLAS_VISUAL_PROOF_SAVED',flush=True)
