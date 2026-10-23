"""Visual large-range binding probes, never exported as accepted game motion."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(globals().get('PREP_WORK',ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_REFIT_20261023.blend'))
assert Path(bpy.data.filepath).resolve()==WORK.resolve() and not bpy.data.is_dirty
input_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023']
old_mesh=next(o for o in input_scene.objects if o.type=='MESH')
report=json.loads(Path(globals().get('PREP_BIND_REPORT',ROOT/'reports/CHARACTER_THAI_UPPER_BIND_20261023.json')).read_text())
path=Path(report['glb']['path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==report['glb']['sha256']
before={s.name:set(o.name for o in s.objects) for s in bpy.data.scenes}
scene=bpy.data.scenes.new('VALIDATE_THAI_UPPER_BIND_20261023');bpy.context.window.scene=scene
with bpy.context.temp_override(scene=scene,view_layer=scene.view_layers[0],collection=scene.collection):bpy.ops.import_scene.gltf(filepath=str(path))
for name,names in before.items():
    for obj in list(bpy.data.scenes[name].objects):
        if obj.name not in names:
            assert obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa'))
            for col in list(obj.users_collection):col.objects.unlink(obj)
    assert set(o.name for o in bpy.data.scenes[name].objects)==names
for obj in list(scene.objects):
    if obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa')) and not any(m.type=='ARMATURE' for m in obj.modifiers):
        for col in list(obj.users_collection):col.objects.unlink(obj)
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==len(meshes)==1;arm=arms[0];mesh=meshes[0];assert len(arm.data.bones)==20
BASE=ROOT/'reports/thai_upper_refit_20261023'
folder=Path(globals().get('PREP_FOLDER',BASE));masks=np.load(BASE/'head_hand_graph_masks.npz');base=np.load(BASE/'baseline_mesh.npz')['vertices']
semantic=np.load(folder/'texture_region_candidates.npz') if (folder/'texture_region_candidates.npz').exists() else None
coords=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
assert coords.shape==base.shape and np.max(np.linalg.norm(coords-base,axis=1))<1e-5,'Need remap masks before using this reimport'
def depth(b):return 0 if not b.parent else depth(b.parent)+1
bones=sorted(arm.pose.bones,key=depth);ref={b.name:b.bone.matrix_local.copy() for b in bones}
def apply(desired):
    for b in bones:
        kw={'parent_matrix':desired[b.parent.name],'parent_matrix_local':b.parent.bone.matrix_local} if b.parent else {}
        b.matrix_basis=b.bone.convert_local_to_pose(desired[b.name],b.bone.matrix_local,invert=True,**kw)
    bpy.context.view_layer.update()
def points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh();a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a);ev.to_mesh_clear();return a.reshape(-1,3)
def lower_arm(side,desired):
    sign=1 if side=='L' else -1
    position=ref[side+'_upper_arm'].translation.copy()
    for part,direction in [('upper_arm',(sign*.10,0,-1)),('forearm',(sign*.03,-.08,-1)),('hand',(0,-.12,-1))]:
        name=side+'_'+part;bone=arm.data.bones[name];old=bone.tail_local-bone.head_local;direction=Vector(direction).normalized()
        swing=old.normalized().rotation_difference(direction);rotation=swing@ref[name].to_quaternion()
        desired[name]=Matrix.LocRotScale(position,rotation,Vector((1,1,1)));position+=direction*bone.length
scene.world=bpy.data.worlds.new('Thai_Upper_Probe_World');scene.world.color=(.055,.055,.055)
for location,energy,size in [((2.4,-3.4,3),850,3),((-2.4,-1,2),500,2.5),((0,2.5,2.8),650,2)]:
    data=bpy.data.lights.new('Thai_Upper_Probe_Light','AREA');data.energy=energy;data.size=size
    light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=location;light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Thai_Upper_Probe_Camera');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=1.95
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=560;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
records=[]
for sample in ['rest','head_turn_15','right_arm_lowered','both_arms_lowered']:
    desired={n:m.copy() for n,m in ref.items()}
    if sample=='head_turn_15':
        rotation=Quaternion((0,0,1),math.radians(15))@ref['head'].to_quaternion();desired['head']=Matrix.LocRotScale(ref['head'].translation,rotation,Vector((1,1,1)))
    elif sample in ['right_arm_lowered','both_arms_lowered']:
        lower_arm('R',desired)
        if sample=='both_arms_lowered':lower_arm('L',desired)
    apply(desired);posed=points();delta=np.linalg.norm(posed-base,axis=1)
    evidence={k:float(delta[masks[k]].max()) for k in ['head','faceFrontCandidate','hairRearCandidate','rightHand153']}
    if semantic is not None:
        for name in ['faceJawCandidate','rigidHeadCandidate','lowerHairCollarReview']:evidence[name]=float(delta[semantic[name]].max())
    renders=[]
    for name,offset in [('front',(0,-5,0)),('side',(5,0,0))]:
        center=Vector((0,0,.85));cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        path=folder/f'upper_{sample}_{name}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
    records.append({'sample':sample,'protectedRegionDisplacements':evidence,'renders':renders,'acceptedAsGameAnimation':False})
apply(ref)
scene['PREP_role']='upper-binding-large-range-probes-not-neutral-or-runtime'
out=Path(globals().get('PREP_OUT',ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_PROBES_20261023.blend'))
assert not out.exists();bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
report={'status':'independent-reimport-probe-renders-written-awaiting-visual-review','library':str(out),'samples':records,'source':report['glb'],'reimportGeometryMaxError':float(np.max(np.linalg.norm(coords-base,axis=1))),
 'scene':scene.name,'runtimeChanged':False,'neutralPoseValidated':False,'nativeWalkValidated':False}
Path(globals().get('PREP_REPORT',ROOT/'reports/CHARACTER_THAI_UPPER_VISUAL_PROBES_20261023.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'samples':len(records),'library':str(out)}))
