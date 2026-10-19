"""Stage the preserved hospital and two independent fitted actors at runtime scale."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
SCENE='PREP_HOSPITAL_CITY_20261019'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert SCENE not in bpy.data.scenes, 'Inspect the existing stage instead of rebuilding it'
checkpoint=json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())
assert Path(checkpoint['checkpoint']).is_file()
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
original=json.loads(Path(checkpoint['stateSnapshot']).read_text())
assert state_hash(object_state([o for o in bpy.data.objects if o.name in original]))==checkpoint['stateHash']
source=bpy.data.scenes['PREP_HOSPITAL_RECEPTION_20261015']
scene=bpy.data.scenes.new(SCENE)
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.fps=30;scene.frame_start=1;scene.frame_end=450
scene['author']='Romario Vicente Amaro'
scene['purpose']='Hospital placement and independent uniform QA; demonstration actors are not multiplayer identities'
scene['runtime_position_three_xyz']=[48,0,-38]
scene['original_city_preserved']=True
for window in bpy.context.window_manager.windows:window.scene=scene
def collection(name):
    col=bpy.data.collections.new('HSC19_'+name);scene.collection.children.link(col);return col
architecture=collection('ARCHITECTURE');actors=collection('ACTORS_QA');studio=collection('STUDIO')
anchor=bpy.data.objects.new('HSC19_HOSPITAL_ANCHOR',None);architecture.objects.link(anchor)
anchor.location=(48,38,0);anchor['runtime_building_id']='hospital';anchor['reference_only_not_macro']=True
sources=[o for o in source.objects if o.type in ('MESH','EMPTY','LIGHT') and not o.get('preview_reference')
         and not o.name.startswith('HSP15_CHAIR_COLLIDER_')]
clones={}
for obj in sources:
    copy=obj.copy();copy.name='HSC19_'+obj.name
    if obj.type=='LIGHT':copy.data=obj.data.copy()
    architecture.objects.link(copy);clones[obj]=copy
for obj,copy in clones.items():
    copy.parent=clones.get(obj.parent,anchor)
    copy.matrix_parent_inverse=obj.matrix_parent_inverse.copy()
    copy.matrix_basis=obj.matrix_basis.copy()
    copy['source_object']=obj.name
    copy['runtime_architecture_reference']=True

scene.world=source.world.copy()
actor_records=[]
def actor(source_name,key,position,angle=0,walk=False):
    root=bpy.data.objects[source_name]
    tree=[root]+[o for o in root.children_recursive if o.name in original];mapped={}
    for obj in tree:
        copy=obj.copy();copy.name='HSC19_'+key+'_'+obj.name
        copy.parent=None
        if obj.type=='ARMATURE':copy.data=obj.data.copy()
        actors.objects.link(copy);mapped[obj]=copy
    for obj,copy in mapped.items():
        copy.parent=mapped.get(obj.parent)
        copy.matrix_parent_inverse=obj.matrix_parent_inverse.copy()
        copy.matrix_basis=obj.matrix_basis.copy()
        for modifier in copy.modifiers:
            if modifier.type=='ARMATURE' and modifier.object in mapped:modifier.object=mapped[modifier.object]
        for constraint in copy.constraints:
            if hasattr(constraint,'target') and constraint.target in mapped:constraint.target=mapped[constraint.target]
        if copy.type=='ARMATURE':
            for bone in copy.pose.bones:
                for constraint in bone.constraints:
                    if hasattr(constraint,'target') and constraint.target in mapped:constraint.target=mapped[constraint.target]
        if obj.hide_render or obj.get('character_helper_hidden'):
            copy.hide_render=True;copy.hide_set(True)
        if 'NAME_Remy_Player' in obj.name:
            for slot in copy.material_slots:
                if slot.material:
                    material=slot.material
                    slot.link='OBJECT';slot.material=material.copy()
    result=mapped[root];result.rotation_mode='XYZ';result.rotation_euler.z=angle
    rig=next(o for o in mapped.values() if o.type=='ARMATURE')
    assert len(rig.data.bones)==55 and rig.data!=next(o for o in tree if o.type=='ARMATURE').data
    assert rig.animation_data
    for track in rig.animation_data.nla_tracks:
        track.mute=track.name!=('Walk' if walk else 'Idle')
        if not track.mute:
            for strip in track.strips:
                strip.repeat=24
                strip.extrapolation='HOLD'
    scene.frame_set(1);bpy.context.view_layer.update()
    visible=[o for o in mapped.values() if o.type=='MESH' and not o.hide_render]
    points=[o.matrix_world@Vector(v) for o in visible for v in o.bound_box]
    low=Vector([min(p[i] for p in points) for i in range(3)])
    high=Vector([max(p[i] for p in points) for i in range(3)])
    result.location+=Vector((position[0]-(low.x+high.x)/2,position[1]-(low.y+high.y)/2,position[2]-low.z))
    result['demo_name']='Ana Clara' if key=='ANA' else 'Romario Vicente Amaro'
    result['purpose']='Uniform fit QA, not a universal player name'
    record={'name':result['demo_name'],'root':result.name,'rig':rig.name,'bones':len(rig.data.bones),
            'sourceRoot':source_name,'objects':len(mapped),'scale':list(result.scale),
            'independentNameMaterials':[slot.material.name for o in mapped.values() if 'NAME_Remy_Player' in o.name
                                        for slot in o.material_slots if slot.material],
            'activeClip':'Walk' if walk else 'Idle'}
    actor_records.append(record)
    return result,rig,visible

receptionist,_,_=actor('CHAR_ROMARIO_DEMO_ROOT','ROMARIO',(37,33,.014))
walker,walkrig,walkmeshes=actor('CHAR_ANA_DEMO_ROOT','ANA',(48,24,.014),math.pi,True)
walker.animation_data_clear()
base_z=walker.location.z
route=[(1,48,24,math.pi),(31,48,24,math.pi),(331,48,38,math.pi),
       (352,48,38,math.pi*1.5),(416,45,38,math.pi*1.5),(450,45,38,math.pi*1.5)]
for frame,x,y,angle in route:
    walker.location=(x,y,base_z);walker.rotation_euler.z=angle
    walker.keyframe_insert(data_path='location',frame=frame)
    walker.keyframe_insert(data_path='rotation_euler',frame=frame)
action=walker.animation_data.action;action.name='HSC19_ANA_Entrance_To_Triage_01'
for layer in action.layers:
    for strip in layer.strips:
        for channelbag in strip.channelbags:
            for curve in channelbag.fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
# Correct only the new actor root's vertical placement from evaluated shoe/body bounds.
# This prevents imported gait root height from putting a foot beneath the tiled floor.
foot_samples=[]
for frame in range(1,451):
    scene.frame_set(frame);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    low=min((o.evaluated_get(dg).matrix_world@Vector(v)).z for o in walkmeshes for v in o.evaluated_get(dg).bound_box)
    walker.location.z+=.014-low
    walker.keyframe_insert(data_path='location',index=2,frame=frame)
    if frame%30==1:
        foot_samples.append({'frame':frame,'rootZ':walker.location.z,'uncorrectedMinZ':low})

def camera(name,location,target,lens):
    data=bpy.data.cameras.new('HSC19_'+name);obj=bpy.data.objects.new(data.name,data);studio.objects.link(obj)
    obj.location=location;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.lens=lens;data.clip_start=.02;data.clip_end=300
    return obj
overview=camera('CAM_RECEPTION',(60,27.2,2.15),(42,32.9,1.3),25)
closeup=camera('CAM_UNIFORM',(38.0,30.1,1.45),(37,33,1.13),65)
entrance=camera('CAM_ENTRANCE',(53,19,2.05),(47.8,27.2,1.3),32)
for local,target,name in [((6,-5,3.7),(-7,-5,1),'RECEPTION'),((0,-4,3.8),(0,1,0),'CORRIDOR')]:
    data=bpy.data.lights.new('HSC19_SOFT_'+name,'AREA');data.energy=450;data.shape='DISK';data.size=4
    obj=bpy.data.objects.new(data.name,data);studio.objects.link(obj)
    obj.location=Vector(local)+anchor.location
    obj.rotation_euler=(Vector(target)+anchor.location-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1440;scene.render.resolution_y=960
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX';scene.camera=overview;scene.frame_set(180)
bpy.context.view_layer.update()
after=object_state([o for o in bpy.data.objects if o.name in original])
assert state_hash(after)==checkpoint['stateHash'], 'An original object changed; inspect before saving'
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report={'scene':SCENE,'master':str(MASTER),'masterBytes':MASTER.stat().st_size,
        'anchorBlenderXYZ':list(anchor.location),'runtimePositionThreeXYZ':[48,0,-38],
        'architectureObjects':len(clones),'newSceneObjects':len(scene.objects),'actors':actor_records,
        'originalObjectsPreserved':len(original),'originalStateBefore':checkpoint['stateHash'],
        'originalStateAfter':state_hash(after),'sceneFrames':[1,450],'walkRouteBlenderXY':route,
        'footPlacementSamples':foot_samples,'cameras':{'reception':overview.name,'uniform':closeup.name,'entrance':entrance.name},
        'status':'saved-awaiting-render-and-walk-validation',
        'limitations':['QA demonstration actors are not persistent NPCs or multiplayer users',
                       'Original module geometry and uniform asset bytes remain unchanged',
                       'No clinical or architectural compliance certification',
                       'This stage is not the inactive 4 km macro city']}
(ROOT/'reports/HOSPITAL_CITY_STAGE_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'scene':SCENE,'objects':len(scene.objects),'actors':len(actor_records),'originalPreserved':len(original),
                  'masterBytes':report['masterBytes']}))
