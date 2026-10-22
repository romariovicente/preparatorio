"""Adapt native Anime CyberStyle motion to the preserved Alchemist FK rig.

The supplied Anime asset is read-only; Remy's 1.70 m is the scale reference.
Only this staged library and new derivative GLB are written.
"""
from pathlib import Path
from datetime import datetime, timezone
import bpy, hashlib, json, math
import numpy as np
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(__file__).resolve().parents[1]
WORKING=ROOT/'art/blender/libraries/PREP_CHARACTER_ALCHEMIST_RETARGET_20261022.blend'
OUTPUT=ROOT/'art/character_retarget_20261022/CHR_Alchemist_Anime_Retarget_20261022.glb'
REPORT=ROOT/'reports/CHARACTER_ALCHEMIST_ANIME_RETARGET_20261022.json'
assert Path(bpy.data.filepath).resolve()==WORKING.resolve()
assert not OUTPUT.exists(), 'Inspect existing derivative before replacing it.'
target_scene=bpy.data.scenes['PREP_CHARACTER_ALCHEMIST_RETARGET_20261022']
source_scene=bpy.data.scenes['SOURCE_ANIME_NATIVE_20261022']
target_arm=next(o for o in target_scene.objects if o.type=='ARMATURE')
source_arm=next(o for o in source_scene.objects if o.type=='ARMATURE')
meshes=[o for o in target_scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==target_arm for m in o.modifiers)]
assert len(meshes)==1 and len(target_arm.data.bones)==20

def depth(b):return 0 if b.parent is None else 1+depth(b.parent)
bones=sorted(target_arm.pose.bones,key=depth)
mapping={'hips':'mixamorig:Hips_02','spine':'mixamorig:Spine_03','chest':'mixamorig:Spine2_05','neck':'mixamorig:Neck_06','head':'mixamorig:Head_07'}
for side,label,ids in [('L','Left',('045','046','047','048','092','093','094')),('R','Right',('069','070','071','072','097','098','099'))]:
    for part,mix,id_ in zip(('clavicle','upper_arm','forearm','hand','thigh','shin','foot'),('Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot'),ids):
        mapping[side+'_'+part]='mixamorig:'+label+mix+'_'+id_
toes={'L':'mixamorig:LeftToeBase_095','R':'mixamorig:RightToeBase_0100'}
assert all(n in source_arm.data.bones for n in [*mapping.values(),*toes.values()])

def activate(clip,frame):
    bpy.context.window.scene=source_scene
    source_arm.animation_data.action=None
    for track in source_arm.animation_data.nla_tracks:track.mute=track.name.rsplit('|',1)[-1]!=clip
    source_scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {b.name:source_arm.matrix_world@b.matrix.copy() for b in source_arm.pose.bones}

def points():
    arrays=[]
    dg=bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        ev=obj.evaluated_get(dg);mesh=ev.to_mesh()
        try:
            co=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',co)
            mat=np.array(ev.matrix_world)
            arrays.append(co.reshape(-1,3)@mat[:3,:3].T+mat[:3,3])
        finally:ev.to_mesh_clear()
    result=np.concatenate(arrays);assert np.isfinite(result).all()
    return result

def apply(desired):
    inv=target_arm.matrix_world.inverted();pose={k:inv@v for k,v in desired.items()}
    for b in bones:
        kw={'parent_matrix':pose[b.parent.name],'parent_matrix_local':b.parent.bone.matrix_local} if b.parent else {}
        b.matrix_basis=b.bone.convert_local_to_pose(pose[b.name],b.bone.matrix_local,invert=True,**kw)
        b.rotation_mode='QUATERNION'
    bpy.context.view_layer.update()

source_ref=activate('Idle',1)
up=source_ref[mapping['head']].translation-source_ref[mapping['hips']].translation
assert up.z>abs(up.x)+abs(up.y),tuple(up)
bpy.context.window.scene=target_scene
target_arm.animation_data_clear()
for b in bones:b.matrix_basis=Matrix.Identity(4)
target_scene.frame_set(1);bpy.context.view_layer.update()
reference={b.name:target_arm.matrix_world@b.matrix.copy() for b in bones}
reference_tails={b.name:target_arm.matrix_world@b.tail for b in bones}

def fit_legs(desired,ref,source):
    # Anatomical vectors avoid carrying the source rig's local axes or wide stance.
    # Feet have no ToeBase child in this 20-bone rig; their saved terminal vector
    # supplies the reference direction. No bone length is scaled during motion.
    ratio=(ref['L_thigh'].translation-ref['R_thigh'].translation).length/(source[mapping['L_thigh']].translation-source[mapping['R_thigh']].translation).length
    for side in ('L','R'):
        names=[side+'_'+p for p in ('thigh','shin','foot')]
        sources=[mapping[n] for n in names]+[toes[side]]
        anchor=source[sources[0]].translation-source[mapping['hips']].translation
        # Preserve hip-to-thigh target anatomy while following the source pelvis.
        original=(ref[names[0]].translation-ref['hips'].translation).length
        anchor=anchor.normalized()*original
        position=desired['hips'].translation+anchor
        for i,name in enumerate(names[:2]):
            old_direction=(ref[names[i+1]].translation-ref[name].translation) if i<2 else reference_tails[name]-ref[name].translation
            direction=source[sources[i+1]].translation-source[sources[i]].translation
            rot=desired[name].to_quaternion()
            current=rot@ref[name].to_quaternion().inverted()@old_direction
            swing=current.normalized().rotation_difference(direction.normalized())
            desired[name]=Matrix.LocRotScale(position,swing@rot,ref[name].to_scale())
            position+=direction.normalized()*old_direction.length
        # glTF does not encode a terminal bone's tail. Blender guesses it on
        # import; treating that guessed axis as a toe direction tilted the shoe.
        # Keep its actual neutral orientation and transfer native ankle rotation.
        foot=names[2]
        desired[foot]=Matrix.LocRotScale(position,desired[foot].to_quaternion(),ref[foot].to_scale())
    return desired

# Normalize the relaxed, corrected initial standing pose once, before baking.
desired=fit_legs({n:m.copy() for n,m in reference.items()},reference,source_ref)
apply(desired)
model_root=target_arm
while model_root.parent:model_root=model_root.parent
co=points();factor=1.7/float(np.ptp(co[:,2]))
model_root.scale=tuple(v*factor for v in model_root.scale)
bpy.context.view_layer.update();co=points();model_root.location.z-=float(co[:,2].min())
bpy.context.view_layer.update()
reference={b.name:target_arm.matrix_world@b.matrix.copy() for b in bones}
reference_tails={b.name:target_arm.matrix_world@b.tail for b in bones}
local={b.name:reference[b.parent.name].inverted()@reference[b.name] if b.parent else reference[b.name] for b in bones}
target_hip=reference['hips'].translation.copy()
source_hip=source_ref[mapping['hips']].translation.copy()
leg=lambda matrices,names:sum((matrices[a].translation-matrices[b].translation).length for a,b in zip(names,names[1:]))
scale=leg(reference,['L_thigh','L_shin','L_foot'])/leg(source_ref,[mapping[n] for n in ['L_thigh','L_shin','L_foot']])
target_scene.render.fps=24
created=[]
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'baking','mapping':mapping,
 'retargetSourceId':'SUP_lowpoly_anime_character_cyberstyle','sourceHash':'d470f6653b7407f5324c6df1500f7ada05fd8e6df2e4709d9d7aa3bbfc27dba8',
 'scaleReferenceId':'CHR_Remy_Mixamo_20261005','targetHeight':1.7,'initialScaleCorrection':factor,'translationScale':scale,
 'preservedTargetHash':'00f175ce2210df98d8ad4fa1fb3538ceabe6e9b62a5896e7f14ccdf9ac4e9265',
 'method':'Native source motion, per-clip upper-body reference offset preserves lowered original arms; anatomical leg vectors, in-place navigation and evaluated-mesh ground correction',
 'clips':[],'runtimeChanged':False,'masterChanged':False}

for clip in ('Idle','Walk'):
    source_track=next(t for t in source_arm.animation_data.nla_tracks if t.name.rsplit('|',1)[-1]==clip)
    end=round(source_track.strips[0].frame_end)
    source_poses=[activate(clip,f) for f in range(1,end+1)]
    # Center upper-body deltas across each native clip. This removes the Anime
    # idle's hand-raised rest offset without replacing her rhythmic sway.
    centered={}
    for name in mapping.values():
        quats=[p[name].to_quaternion() for p in source_poses]
        initial=quats[0]
        aligned=np.array([tuple(-q if q.dot(initial)<0 else q) for q in quats])
        values=aligned.mean(axis=0);values/=np.linalg.norm(values)
        centered[name]=Quaternion(tuple(values))
    bpy.context.window.scene=target_scene
    target_arm.animation_data_create()
    for t in target_arm.animation_data.nla_tracks:t.mute=True
    action=bpy.data.actions.new('PREP_Alchemist_Anime_'+clip+'_20261022');action.use_fake_user=True
    target_arm.animation_data.action=action
    rows=[];previous={}
    for frame,source in enumerate(source_poses,1):
        target_scene.frame_set(frame)
        bpy.context.view_layer.update()
        delta=(source[mapping['hips']].translation-source_hip)*scale
        delta.x=delta.y=0
        desired={}
        for b in bones:
            ref=reference[b.name]
            inherited=desired[b.parent.name]@local[b.name] if b.parent else ref.copy()
            if b.name in mapping:
                name=mapping[b.name]
                source_rotation_reference=source_ref[name].to_quaternion() if b.name.endswith('_foot') else centered[name]
                rotation=source[name].to_quaternion()@source_rotation_reference.inverted()@ref.to_quaternion()
                position=target_hip+delta if b.name=='hips' else inherited.translation
                desired[b.name]=Matrix.LocRotScale(position,rotation,ref.to_scale())
            else:desired[b.name]=inherited
        desired=fit_legs(desired,reference,source)
        apply(desired);co=points();floor=-float(co[:,2].min())
        for m in desired.values():m.translation.z+=floor
        apply(desired);co=points()
        error=max(((target_arm.matrix_world@b.matrix).translation-desired[b.name].translation).length for b in bones)
        assert error<.001,(clip,frame,error)
        for b in bones:
            q=b.rotation_quaternion
            if b.name in previous and q.dot(previous[b.name])<0:q.negate()
            previous[b.name]=q.copy()
            for path in ('location','rotation_quaternion','scale'):b.keyframe_insert(data_path=path,frame=frame,group=b.name)
        rows.append({'frame':frame,'floor':float(co[:,2].min()),'height':float(np.ptp(co[:,2]))})
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    slot=target_arm.animation_data.action_slot;target_arm.animation_data.action=None
    track=target_arm.animation_data.nla_tracks.new();track.name=clip
    strip=track.strips.new(clip,1,action);strip.action_slot=slot
    strip.action_frame_start=strip.frame_start=1;strip.action_frame_end=strip.frame_end=end;strip.extrapolation='NOTHING'
    track.mute=True;created.append(track)
    report['clips'].append({'name':clip,'frames':end,'duration':(end-1)/24,'sourceAction':source_track.strips[0].action.name,'groundSamples':rows})
    print('Baked',clip,end)

bpy.context.window.scene=target_scene
for track in created:track.mute=False
bpy.ops.object.select_all(action='DESELECT')
for obj in [model_root,*model_root.children_recursive]:obj.select_set(True)
bpy.context.view_layer.objects.active=target_arm
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
assert 'FINISHED' in bpy.ops.export_scene.gltf(filepath=str(OUTPUT),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',export_cameras=False,export_lights=False,export_extras=True)
for track in created:track.mute=track.name!='Idle'
target_scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(WORKING),compress=True)
report['status']='baked-awaiting-reimport-and-visual-review'
report['glb']={'path':str(OUTPUT),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),'bytes':OUTPUT.stat().st_size}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['glb']))
