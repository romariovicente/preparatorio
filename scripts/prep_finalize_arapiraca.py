"""Complete and verify generated city geometry and synchronized Blender previews."""
import bpy, json, math, hashlib, datetime
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005'];bpy.context.window.scene=scene
path=ROOT/'frontend/public/assets/cyber/ENV_Arapiraca_Cyber_v2_20261005.glb'
if path.exists():raise FileExistsError('Inspect existing v2 export before replacing it.')
# Checkpoint precedes every scene/material mutation, including existing costumes.
checkpoint=ROOT/'art/blender/checkpoints/ARAPIRACA_BUILD_BEFORE_FINALIZE_20261005.blend'
if not checkpoint.exists():bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
roads=bpy.data.collections['ARAP_02_ROADS_BIKE_LANES'];buildings=bpy.data.collections['ARAP_03_BUILDINGS']
manifest_path=ROOT/'frontend/src/config/cyberWorldManifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))

# New art direction: reduce broad neon surfaces and use plausible dielectric
# roughness/metallic values. Geometry is still a prototype, not photorealistic.
# Clone the generated palette instead of changing materials in retained scenes.
palette={
 'navy':((.035,.045,.055),.75,.32,0),
 'concrete':((.42,.41,.38),0,.84,0),
 'ivory':((.78,.79,.76),0,.57,0),
 'glass':((.13,.22,.26),0,.16,0),
 'cyan':((.035,.4,.51),0,.36,.65),
 'magenta':((.36,.035,.17),0,.42,.6),
 'gold':((.6,.36,.075),.85,.3,0),
 'asphalt':((.055,.056,.052),0,.95,0),
 'foliage':((.08,.19,.075),0,.88,0),
 'water':((.025,.115,.15),0,.2,0),
 'purple':((.18,.12,.21),0,.67,0),
 'bronze':((.38,.21,.085),.85,.4,0),
}
palette_changes=[]
for key,(color,metal,rough,emission) in palette.items():
 source=bpy.data.materials['MAT_ARAP_'+key]
 revision=bpy.data.materials.get('MAT_ARAP_REAL_'+key) or source.copy()
 revision.name='MAT_ARAP_REAL_'+key
 shader=next(n for n in revision.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 shader.inputs['Base Color'].default_value=(*color,1)
 shader.inputs['Metallic'].default_value=metal;shader.inputs['Roughness'].default_value=rough
 shader.inputs['Emission Color'].default_value=(*color,1);shader.inputs['Emission Strength'].default_value=emission
 revision.diffuse_color=(*color,1)
 # Modify only Oct5 scene object material slots with OBJECT links so meshes
 # shared with an earlier prototype retain their original datablocks.
 for obj in scene.objects:
  for slot in obj.material_slots:
   if slot.material==source:slot.link='OBJECT';slot.material=revision
 palette_changes.append({'material':revision.name,'metallic':metal,'roughness':rough,'emission':emission})
scene['visual_target']='Realistic human proportions and materials; city geometry remains a prototype pending art replacement.'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene['realism_material_revision']='Oct5 material copies; original MAT_ARAP materials preserved.'
manifest['visualTarget']='realism';manifest['artStatus']='Prototype geometry with more natural PBR materials; realistic asset replacement in progress.'
def xyz(p):return Vector((p[0],-p[2],p[1]))
def cube(name,p,size,mat,col):
 w,h,d=size;vertices=[(x*w/2,y*d/2,z*h/2) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
 faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces);mesh.materials.append(bpy.data.materials.get('MAT_ARAP_REAL_'+mat) or bpy.data.materials['MAT_ARAP_'+mat])
 o=bpy.data.objects.new(name,mesh);col.objects.link(o);o.location=xyz(p);return o
def line(name,a,b,width,mat='white'):
 delta=xyz(b)-xyz(a);o=cube(name,((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2),(width,.03,delta.length),mat,roads)
 o.rotation_euler=delta.to_track_quat('Y','Z').to_euler();return o
if not scene.get('finalized_arapiraca_v2'):
 # Correct the underground floor to -6 m without modifying any old scene.
 for o in scene.objects:
  if o.name.startswith('BLD_UndergroundGallery'):o.location.z-=6.65
 shaft=scene.objects.get('LIFT_Entrance');shaft.hide_set(True);shaft.hide_render=True
 core=scene.objects.get('BLD_UndergroundGallery_Core');core.hide_set(True);core.hide_render=True
 # The first blockout core was a solid cube; retain it hidden and construct an
 # actual hollow underground interior with a level floor at -6 m.
 cube('BLD_UndergroundInterior_Floor',(-18,-6.15,59),(22,.3,20),'concrete',buildings)
 for x in [-29,-7]:cube('BLD_UndergroundInterior_Wall',(x,-3.6,59),(.25,4.8,20),'ivory',buildings)
 cube('BLD_UndergroundInterior_Back',(-18,-3.6,69),(22,4.8,.25),'ivory',buildings)
 cube('BLD_UndergroundInterior_Ceiling',(-18,-1.05,59),(22,.25,20),'concrete',buildings)
 for x in [-20.5,-13.5]:cube('LIFT_OpenShaftSide',(x,3,56),(1,6,8),'navy',buildings)
 cube('LIFT_OpenShaftBack',(-17,3,52.1),(8,6,.2),'glass',buildings)
 cube('LIFT_OpenShaftRoof',(-17,6.1,56),(8,.25,8),'cyan',buildings)
 # Same-direction dashed markings and physical bicycle symbols at intervals.
 axes=[((-115,-80),(113,58)),((-106,35),(108,35)),((-106,-75),(108,-75)),((-106,80),(108,80)),((-80,-108),(-80,115)),((35,-108),(35,115)),((105,-108),(105,115))]
 for j,(a,b) in enumerate(axes):
  start=Vector(a);end=Vector(b);direction=(end-start).normalized();normal=Vector((-direction.y,direction.x))
  for side in [-1,1]:
   for i in range(18,int((end-start).length)-10,12):
    p=start+direction*i+normal*3*side;q=p+direction*4
    line('MARK_SameDirection_'+str(j)+'_'+str(side)+'_'+str(i),(p.x,.25,p.y),(q.x,.25,q.y),.11)
   for i in range(26,int((end-start).length)-15,36):
    center=start+direction*i+normal*7.3*side
    # A plan-view bike consists of two wheels and a triangular frame.
    for wheeloffset in [-.38,.38]:
     wheelcenter=center+direction*wheeloffset
     points=[wheelcenter+Vector((math.cos(k*math.tau/12),math.sin(k*math.tau/12)))*.25 for k in range(13)]
     for k,(p,q) in enumerate(zip(points,points[1:])):line('MARK_BicycleWheel',(p.x,.29,p.y),(q.x,.29,q.y),.055)
    points=[center-direction*.38,center+normal*.28,center+direction*.38,center-direction*.38]
    for p,q in zip(points,points[1:]):line('MARK_BicycleFrame',(p.x,.29,p.y),(q.x,.29,q.y),.065)
 # Long bays for trucks/reboques and work vehicles.
 cube('PARK_Utility',(93,.19,51),(14,.14,20),'asphalt',roads)
 for x in [87,93,99]:line('PARK_UtilityBayLine',(x,.3,41),(x,.3,61),.12)
 manifest['parking'] += [{'id':'utility-truck','label':'Utilitários e reboques','position':[90,.1,50],'size':[6,18],'heading':0},{'id':'utility-agriculture','label':'Equipamentos agrícolas','position':[96,.1,50],'size':[6,18],'heading':0}]
 scene['finalized_arapiraca_v2']=True

# Animate traffic from the same stage table used in the browser.
cycle=json.loads((ROOT/'frontend/src/config/trafficCycle.json').read_text(encoding='utf-8'))
duration=sum(s['duration'] for s in cycle['stages'])
def signal(seconds,key):
 t=seconds%duration
 for stage in cycle['stages']:
  if t<stage['duration']:
   value=stage[key]
   if value=='flashing-red':return 'red' if int(t/cycle['flashingRedOnSeconds'])%2==0 else 'off'
   return value
  t-=stage['duration']
 return 'red'
signal_nodes=[]
for o in scene.objects:
 if not o.name.startswith('TRAFFIC_J') or o.type!='MESH':continue
 parts=o.name.split('_');ped='PED' in parts;axis=parts[-2];lamp=parts[-1]
 if axis not in ['NS','EW'] or lamp not in ['R','Y','G']:continue
 key=('ped' if ped else '')+axis.title() if ped else axis.lower()
 # API keys are pedNs/pedEw (vehicular keys ns/ew).
 if ped:key='ped'+('Ns' if axis=='NS' else 'Ew')
 m=o.data.materials[0];shader=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 color={'R':(.8,.025,.035,1),'Y':(1,.73,.04,1),'G':(.015,.55,.12,1)}[lamp]
 expected={'R':'red','Y':'yellow','G':'green'}[lamp]
 if m.node_tree.animation_data:m.node_tree.animation_data_clear()
 for step in range(int(duration*2)+1):
  seconds=step/2;active=signal(seconds,key)==expected
  shader.inputs['Base Color'].default_value=color if active else (.008,.012,.016,1)
  shader.inputs['Emission Color'].default_value=color;shader.inputs['Emission Strength'].default_value=3 if active else 0
  for socket in ['Base Color','Emission Strength']:shader.inputs[socket].keyframe_insert(data_path='default_value',frame=1+seconds*60)
 action=m.node_tree.animation_data.action
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='CONSTANT'
     fc.modifiers.new('CYCLES')
 signal_nodes.append(o.name)

# Vehicle heading and route keys now follow the visible road/rail corridors.
def route_animation(prefix,points,frames):
 root=next(o for o in scene.objects if o.name.startswith(prefix) and o.type=='EMPTY')
 if root.animation_data:root.animation_data_clear()
 for i,(p,f) in enumerate(zip(points,frames)):
  nextp=points[(i+1)%len(points)] if i<len(points)-1 else points[1]
  heading=math.atan2(nextp[0]-p[0],nextp[2]-p[2])
  root.location=xyz(p);root.rotation_euler[2]=heading
  root.keyframe_insert(data_path='location',frame=f);root.keyframe_insert(data_path='rotation_euler',frame=f)
 for layer in root.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='CONSTANT' if 'rotation' in fc.data_path else 'LINEAR'
     fc.modifiers.new('CYCLES')
 return root
route_animation('WORLD_bus_PROP_bus_Root',[(0,.2,35),(105,.2,35),(105,.2,-75),(-80,.2,-75),(-80,.2,35),(0,.2,35)],[1,1081,2161,3241,4321,5401])
route_animation('WORLD_train_PROP_train_Root',[(-70,.3,-103),(102,.3,-103),(117,.3,-88),(117,.3,92),(100,.3,114),(-97,.3,114),(-115,.3,96),(-115,.3,-85),(-95,.3,-103),(-70,.3,-103)],[1,1201,1441,2641,2881,4201,4441,5641,6001,6241])

# Export a new revision after inspecting the existing export, never overwrite it.
scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT')
for name in ['ARAP_01_TERRAIN','ARAP_02_ROADS_BIKE_LANES','ARAP_03_BUILDINGS','ARAP_04_KNOWLEDGE_LAB','ARAP_05_PUBLIC_PROPS','ARAP_06_FARM']:
 for o in bpy.data.collections[name].objects:
  if o.name not in {'LIFT_Entrance','BLD_UndergroundGallery_Core'}:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
manifest['sceneUrl']='/assets/cyber/'+path.name
manifest['trafficCycle']='trafficCycle.json';manifest['undergroundBounds']={'minX':-28,'maxX':-8,'minZ':49,'maxZ':69,'floorY':-6}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

# Persist an optional visual clock script as editable Blender text; no auto-run
# preference is changed. Quarter-orbit keyframes remain visible without it.
runtime='''import bpy, math, datetime\nfrom bpy.app.handlers import persistent\n@persistent\ndef prep_visual_clock(scene):\n    if scene.name != '00_ARAPIRACA_CYBER_20261005': return\n    seconds=max(0,(scene.frame_current-1)/60)\n    totalminutes=9*60+seconds/240*24*60\n    clock=f"{int(totalminutes//60)%24:02d}:{int(totalminutes%60):02d}"\n    quarter=int((seconds%120)//30)+1\n    for device in ['BILLBOARD','PHONE']:\n        for q in range(4):\n            obj=scene.objects.get('CLOCK_'+device+'_Q'+str(q))\n            if obj:obj.data.body=f"CHRONOVITAE | {clock} | ORBITA {quarter}/4"\nfor handler in list(bpy.app.handlers.frame_change_post):\n    if handler.__name__=='prep_visual_clock':bpy.app.handlers.frame_change_post.remove(handler)\nbpy.app.handlers.frame_change_post.append(prep_visual_clock)\nprep_visual_clock(bpy.context.scene)\n'''
txt=bpy.data.texts.get('PREP_VISUAL_CLOCK.py') or bpy.data.texts.new('PREP_VISUAL_CLOCK.py');txt.clear();txt.write(runtime);exec(compile(runtime,'PREP_VISUAL_CLOCK.py','exec'))

# Verify quarter-orbit synchrony and non-conflicting Blender traffic phases.
checks=[]
for seconds in [0,18,21,23,41,44,46,56,60,64,90,120]:
 scene.frame_set(1+int(seconds*60));earth=scene.objects['SKY_Earth'].matrix_world.translation
 expected=xyz([14*math.cos(seconds/120*math.tau),55,14*math.sin(seconds/120*math.tau)])
 error=(earth-expected).length
 ns=signal(seconds,'ns');ew=signal(seconds,'ew');assert not(ns=='green' and ew=='green')
 labels=[scene.objects.get('CLOCK_'+device+'_Q'+str(int((seconds%120)//30))).data.body for device in ['BILLBOARD','PHONE']]
 assert labels[0]==labels[1]
 checks.append({'seconds':seconds,'earthErrorMeters':error,'ns':ns,'ew':ew,'phoneEqualsBillboard':True})
# Orbit linear interpolation is necessary to match the runtime exactly.
orbit=scene.objects['SKY_Orbit_Controller']
for layer in orbit.animation_data.action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
    fc.modifiers.new('CYCLES')
for entry in checks:
 s=entry['seconds'];scene.frame_set(1+int(s*60));expected=xyz([14*math.cos(s/120*math.tau),55,14*math.sin(s/120*math.tau)])
 error=(scene.objects['SKY_Earth'].matrix_world.translation-expected).length;entry['earthErrorMeters']=error
 assert error<.001
scene.frame_set(1)
scene['visual_clock_note']='Optional PREP_VISUAL_CLOCK.py text updates clock text while running; baked quarter visibility and orbit/traffic keyframes persist.'
city=ROOT/'art/blender/PREPARATORIO_ARAPIRACA_CYBER_20261005.blend'
# Existing city/master have been generated and inspected in this run; keep a
# revision checkpoint before updating their editable contents.
scenes={scene,bpy.data.scenes['01_ARAPIRACA_PROPS_20261005'],*[s for s in bpy.data.scenes if s.name.startswith('BIOME_')]}
bpy.data.libraries.write(str(city),scenes,fake_user=True,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/PREPARATORIO_PROJETO_20261005.blend'))
scene.render.resolution_x=1440;scene.render.resolution_y=1000;scene.cycles.samples=12
scene.render.filepath=str(ROOT/'reports/ARAPIRACA_CYBER_20261005.png');bpy.ops.render.render(write_still=True)
report={'scene':scene.name,'objects':len(scene.objects),'materialSignalNodes':len(signal_nodes),'geometryRevision':'v2','materialRevision':palette_changes,'realismStatus':'Prototype geometry, natural PBR direction; not photorealistic','checkpoint':str(checkpoint),'environment':{'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'clockChecks':checks,'privateHomeInPublicScene':any(o.name.startswith('PRIVATE_') for o in scene.objects),'undergroundFloorY':-6,'render':scene.render.filepath,'retainedOriginalScenes':len(bpy.data.scenes)}
assert not report['privateHomeInPublicScene']
(ROOT/'reports/arapiraca_finalize_20261005.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
