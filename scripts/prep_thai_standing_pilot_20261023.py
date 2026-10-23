"""Editable standing-pose pilot; never promoted as a validated avatar or Walk."""
import bpy, json, math, hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(globals().get('PREP_WORK',ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_STANDING_PILOT_20261023.blend'))
F=Path(globals().get('PREP_FOLDER',ROOT/'reports/thai_standing_pilot_20261023'))
assert Path(bpy.data.filepath).resolve()==WORK.resolve() and not bpy.data.is_dirty
assert not F.exists();F.mkdir()
scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=scene
arm=next(o for o in scene.objects if o.type=='ARMATURE');mesh=next(o for o in scene.objects if o.type=='MESH')
assert len(arm.data.bones)==20 and len(mesh.data.vertices)==31726
assert np.max(np.abs(np.array(arm.matrix_world)-np.eye(4)))<1e-5
assert np.max(np.abs(np.array(mesh.matrix_world)-np.eye(4)))<1e-5
if arm.animation_data:arm.animation_data_clear()
for b in arm.pose.bones:b.matrix_basis.identity()
scene.frame_set(1);bpy.context.view_layer.update()
def depth(b):return 0 if not b.parent else depth(b.parent)+1
bones=sorted(arm.pose.bones,key=depth)
ref={b.name:b.bone.matrix_local.copy() for b in bones}
lengths={b.name:b.bone.length for b in bones}
raw=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',raw);raw=raw.reshape(-1,3)
raw_hash=hashlib.sha256(raw.tobytes()).hexdigest()
weight_report=None
if globals().get('PREP_WEIGHTS'):
    prepared=np.load(globals()['PREP_WEIGHTS']);W=prepared['weights'];names=prepared['group_names'].tolist()
    assert np.array_equal(raw,prepared['vertices'])
    old=np.zeros_like(W)
    for v in mesh.data.vertices:
        for g in v.groups:old[v.index,g.group]=g.weight
    changed=np.flatnonzero(np.max(np.abs(W-old),axis=1)>0)
    helper=ROOT/'work/thai_bmesh_weight_helper_20261023.py';ns={'__file__':str(helper),'__name__':'_thai_standing_weights'}
    exec(compile(helper.read_text(encoding='utf-8'),str(helper),'exec'),ns)
    candidate,weight_report=ns['build_weighted_mesh_copy'](mesh,W,names,changed_indices=changed)
    assert weight_report['geometryUVAndCornerNormalsByteIdentical'] and weight_report['outsideWeightsExact']
    mesh.data=candidate
    if globals().get('PREP_BIND_OUTPUT'):
        output=Path(globals()['PREP_BIND_OUTPUT']);library=Path(globals()['PREP_BIND_LIBRARY'])
        assert not output.exists() and not library.exists()
        bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=arm
        bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_image_format='AUTO',export_cameras=False,export_lights=False,export_extras=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(library),compress=True)
        weight_report['bindingGlb']={'path':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size}
        weight_report['bindingLibrary']={'path':str(library),'sha256':hashlib.sha256(library.read_bytes()).hexdigest(),'bytes':library.stat().st_size}
def points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a);m=np.array(ev.matrix_world);ev.to_mesh_clear()
    return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def apply(desired):
    for b in bones:
        kw={'parent_matrix':desired[b.parent.name],'parent_matrix_local':b.parent.bone.matrix_local} if b.parent else {}
        b.matrix_basis=b.bone.convert_local_to_pose(desired[b.name],b.bone.matrix_local,invert=True,**kw)
    bpy.context.view_layer.update()
def align(name,start,direction):
    direction=Vector(direction).normalized();old=arm.data.bones[name].tail_local-arm.data.bones[name].head_local
    rotation=old.normalized().rotation_difference(direction)@ref[name].to_quaternion()
    return Matrix.LocRotScale(start,rotation,Vector((1,1,1))),Vector(start)+direction*lengths[name]
leg_length={s:lengths[s+'_thigh']+lengths[s+'_shin'] for s in ('L','R')}
pelvis_height=.12+min(leg_length.values())-.02
ankle_z={'L':.12,'R':.12}
def solve():
    desired={n:m.copy() for n,m in ref.items()};position=Vector((0,0,pelvis_height))
    for name,direction in [('hips',(0,0,1)),('spine',(0,0,1)),('chest',(0,0,1)),('neck',(0,-.02,1)),('head',(0,-.04,1))]:
        desired[name],position=align(name,position,direction)
    chest=desired['chest'].translation.copy()
    for side,sign in [('L',1),('R',-1)]:
        clavicle=side+'_clavicle';rise=.065
        vector=Vector((sign*math.sqrt(lengths[clavicle]**2-rise**2),0,rise))
        desired[clavicle],position=align(clavicle,chest,vector)
        arm_splay=globals().get('PREP_ARM_SPLAY',.14);arm_forward=globals().get('PREP_FOREARM_FORWARD',.06)
        for part,direction in [('upper_arm',(sign*arm_splay,0,-1)),('forearm',(sign*.02,-arm_forward,-1)),('hand',(0,-.08,-1))]:
            name=side+'_'+part;desired[name],position=align(name,position,direction)
        hip=desired['hips'].translation+Vector((sign*.11,0,0));ankle=Vector((sign*.135,-.01,ankle_z[side]))
        delta=ankle-hip;distance=delta.length;axis=delta.normalized();a=lengths[side+'_thigh'];b=lengths[side+'_shin']
        assert abs(a-b)<distance<a+b,('Unreachable ankle',side,distance,a+b)
        along=(a*a-b*b+distance*distance)/(2*distance)
        pole=Vector((0,-1,0));pole=(pole-axis*pole.dot(axis)).normalized()
        knee=hip+axis*along+pole*math.sqrt(max(0,a*a-along*along))
        desired[side+'_thigh'],_=align(side+'_thigh',hip,knee-hip)
        desired[side+'_shin'],_=align(side+'_shin',knee,ankle-knee)
        desired[side+'_foot'],_=align(side+'_foot',ankle,(sign*.06,-1,-.45))
    return desired
boot_masks={s:np.flatnonzero((raw[:,2]<.22)&(raw[:,0]*sign>.02)) for s,sign in [('L',1),('R',-1)]}
history=[]
for iteration in range(5):
    desired=solve();apply(desired);co=points();floors={s:float(co[ids,2].min()) for s,ids in boot_masks.items()}
    history.append({'iteration':iteration,'soleMinimum':floors.copy(),'ankleZ':ankle_z.copy()})
    if max(abs(v) for v in floors.values())<.0001:break
    for side in ('L','R'):ankle_z[side]-=floors[side]
co=points();factor=1.7/float(np.ptp(co[:,2]));root=arm
while root.parent:root=root.parent
root.scale=tuple(v*factor for v in root.scale);bpy.context.view_layer.update()
co=points();root.location.z-=float(co[:,2].min());bpy.context.view_layer.update();co=points()
segment_errors={b.name:abs((b.tail-b.head).length-lengths[b.name]) for b in arm.pose.bones}
assert max(segment_errors.values())<2e-6
assert np.isfinite(co).all() and abs(float(np.ptp(co[:,2]))-1.7)<1e-5
floors={s:float(co[ids,2].min()) for s,ids in boot_masks.items()};assert max(abs(v) for v in floors.values())<.02
after=np.empty(raw.size,dtype=np.float32);mesh.data.vertices.foreach_get('co',after)
assert hashlib.sha256(after.tobytes()).hexdigest()==raw_hash
np.savez_compressed(F/'posed_surface.npz',source=raw,posed=co,**{s+'_boot':ids for s,ids in boot_masks.items()})
scene['PREP_role']='standing-pose-pilot-awaiting-visual-review-not-runtime'
scene['PREP_pending']='Visual acceptance, hand/finger geometry, garment seams, native Idle/Walk and independent reimport.'
scene.world=bpy.data.worlds.new('Thai_Standing_Pilot_World');scene.world.color=(.055,.055,.055)
for location,energy,size in [((2.4,-3.4,3),850,3),((-2.4,-1,2),500,2.5),((0,2.5,2.8),650,2)]:
    data=bpy.data.lights.new('Thai_Standing_Pilot_Light','AREA');data.energy=energy;data.size=size
    light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=location;light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Thai_Standing_Pilot_Camera');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=1.95
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=560;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
renders=[]
for label,offset in [('front',(0,-5,0)),('side',(5,0,0)),('back',(0,5,0)),('three_quarter',(3,-5,0))]:
    center=Vector((0,0,.85));cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    path=F/('standing_'+label+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
record={'status':'standing-pilot-saved-awaiting-visual-review','library':str(WORK),'librarySha256':hashlib.sha256(WORK.read_bytes()).hexdigest(),
 'source':globals().get('PREP_SOURCE_DESCRIPTION','PREP_CHARACTER_THAI_UPPER_V5_20261023.blend'),'height':float(np.ptp(co[:,2])),'soleMinimum':floors,
 'uniformScaleFactor':factor,'maxLocalBoneLengthError':max(segment_errors.values()),'boneLengthErrors':segment_errors,
 'sourceGeometryUnchanged':True,'geometrySha256':raw_hash,'weightCopyPreservation':weight_report,'legLengthsBeforeNormalization':leg_length,'contactIterations':history,
 'posedMatrices':{n:list(map(list,m)) for n,m in desired.items()},'sourceBoneLengths':lengths,'renders':renders,
 'runtimeChanged':False,'masterChanged':False,'neutralPoseValidated':False,'nativeWalkValidated':False,
 'limits':['Hand/fingers are still the original source gesture.','Pilot only: no native Idle/Walk yet.','Garment/hair seams need visual review.']}
Path(globals().get('PREP_REPORT',ROOT/'reports/CHARACTER_THAI_STANDING_PILOT_20261023.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:record[k] for k in ['status','library','height','soleMinimum','uniformScaleFactor','maxLocalBoneLengthError']}))
