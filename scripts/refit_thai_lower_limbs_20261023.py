"""Stage a regional leg binding correction; NOT a neutralized/playable character.

The old scan rig places the right leg in front of the actual mesh. Refit only
observable knee/ankle/boot landmarks, keeping the mesh completely stationary.
Pelvis, torso, arms, hair and fingers require a subsequent anatomical pass.
No legacy procedural clips are exported or accepted as validated locomotion.
"""
import bpy,hashlib,json,math
import numpy as np
from datetime import datetime,timezone
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REFIT_V2_20261023.blend'
OUT=ROOT/'art/character_refit_20261023/CHR_Thai_Leg_Bind_Review_V2_20261023.glb'
REPORT=ROOT/'reports/CHARACTER_THAI_LEG_BIND_V2_20261023.json'
assert Path(bpy.data.filepath).resolve()==WORK.resolve()
scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=scene
arm=next(o for o in scene.objects if o.type=='ARMATURE');mesh=next(o for o in scene.objects if o.type=='MESH')
assert not OUT.exists() and not REPORT.exists()
assert len(arm.data.bones)==20 and len(mesh.data.vertices)==31726
arm.animation_data.action=None
for t in list(arm.animation_data.nla_tracks):arm.animation_data.nla_tracks.remove(t)
for b in arm.pose.bones:b.matrix_basis.identity()
scene.frame_set(1);bpy.context.view_layer.update()
def points(evaluated=True):
    obj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else mesh
    data=obj.to_mesh() if evaluated else obj.data
    v=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',v)
    mat=np.array(obj.matrix_world);result=v.reshape(-1,3)@mat[:3,:3].T+mat[:3,3]
    if evaluated:obj.to_mesh_clear()
    return result
def uv_hash():
    values=np.empty(len(mesh.data.loops)*2,dtype=np.float32);mesh.data.uv_layers.active.data.foreach_get('uv',values)
    return hashlib.sha256(values.tobytes()).hexdigest()
def weights():return [{mesh.vertex_groups[g.group].name:float(g.weight) for g in v.groups} for v in mesh.data.vertices]
baseline=points(False);old_weights=weights();old_uv=uv_hash()
old_bones={b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in arm.data.bones}
indices=np.empty(len(mesh.data.loops),dtype=np.int32);mesh.data.loops.foreach_get('vertex_index',indices)
old_topology=hashlib.sha256(indices.tobytes()).hexdigest()
assert np.max(np.linalg.norm(points()-baseline,axis=1))<1e-5
landmarks={
 # V2 preserves the already-close left ankle depth (.06); V1's .08
 # increased the surface-section depth error and was not accepted.
 'L':{'knee':(.21,.05,.48),'ankle':(.23,.06,.12),'toe':(.29,-.10,.04)},
 'R':{'knee':(-.24,.18,.45),'ankle':(-.36,.31,.12),'toe':(-.31,.14,.04)},
}
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
for side,p in landmarks.items():
    thigh=arm.data.edit_bones[side+'_thigh'];shin=arm.data.edit_bones[side+'_shin'];foot=arm.data.edit_bones[side+'_foot']
    # Do not move the old, as-yet-unreviewed pelvis attachments in this pass.
    thigh.tail=p['knee'];shin.head=p['knee'];shin.tail=p['ankle'];foot.head=p['ankle'];foot.tail=p['toe']
    for bone in [thigh,shin,foot]:bone.align_roll(Vector((0,-1,0)))
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
assert np.max(np.linalg.norm(points()-baseline,axis=1))<1e-5,'Refit moved rest mesh'
changed=[];regional={};sole_ids={};landmark_errors={}
group_ids={g.name:g.index for g in mesh.vertex_groups}
for side,sign in [('L',1),('R',-1)]:
    names=[side+'_'+part for part in ['thigh','shin','foot']]
    ids=np.flatnonzero((baseline[:,0]*sign>0)&(baseline[:,2]<.66))
    sole_ids[side]=np.flatnonzero((baseline[:,0]*sign>0)&(baseline[:,2]<.10)).tolist()
    regional[side]={'vertices':len(ids),'geometricSoleVertices':len(sole_ids[side])}
    segments=[(np.array(arm.data.bones[n].head_local),np.array(arm.data.bones[n].tail_local)) for n in names]
    for i in ids:
        point=baseline[i];dist=[]
        for a,b in segments:
            d=b-a;t=np.clip(np.dot(point-a,d)/np.dot(d,d),0,1);dist.append(np.linalg.norm(point-(a+t*d)))
        values=(1/(np.array(dist)**2+.0016)**3);values/=values.sum()
        # Shoe soles are a single rigid region; blend through the boot shaft.
        boot=float(np.clip((.22-point[2])/.10,0,1))
        values*=1-boot;values[2]+=boot
        alpha=float(np.clip((.66-point[2])/.08,0,1))
        combined={n:(1-alpha)*w for n,w in old_weights[i].items()}
        for n,w in zip(names,values):combined[n]=combined.get(n,0)+alpha*float(w)
        keep=sorted(combined.items(),key=lambda x:x[1],reverse=True)[:4];total=sum(w for n,w in keep)
        for group in list(mesh.data.vertices[i].groups):mesh.vertex_groups[group.group].remove([int(i)])
        for n,w in keep:
            if w/total>1e-8:mesh.vertex_groups[n].add([int(i)],w/total,'REPLACE')
        changed.append(int(i))
    band=baseline[(baseline[:,0]*sign>0)&(np.abs(baseline[:,2]-.11)<.012)]
    median=np.median(band,axis=0)
    before=np.array(old_bones[side+'_foot']['head']);after=np.array(landmarks[side]['ankle'])
    landmark_errors[side]={'observedBootSectionMedian':median.tolist(),
       'oldAnkleDepthError':float(abs(before[1]-median[1])),'refitAnkleDepthError':float(abs(after[1]-median[1])),
       'note':'Surface-section proximity only; not clinical/anatomical approval.'}
new_weights=weights()
assert all(len(w)<=4 and abs(sum(w.values())-1)<2e-6 for w in new_weights)
outside=set(range(len(baseline)))-set(changed)
assert all(old_weights[i]==new_weights[i] for i in outside),'Nonregional weights changed'
max_rest=float(np.max(np.linalg.norm(points()-baseline,axis=1)));assert max_rest<1e-5
probe=[]
upper=baseline[:,2]>1.05
for side in ['L','R']:
    for degrees in [-10,10]:
        bone=arm.pose.bones[side+'_shin'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((1,0,0),math.radians(degrees))
        bpy.context.view_layer.update();posed=points();delta=np.linalg.norm(posed-baseline,axis=1)
        ids=sole_ids[side]
        # Rigid sole distances must survive a local knee articulation.
        ref=baseline[ids]-baseline[ids[0]];now=posed[ids]-posed[ids[0]]
        rigidity=float(np.max(np.abs(np.linalg.norm(ref,axis=1)-np.linalg.norm(now,axis=1))))
        upper_error=float(np.max(delta[upper]));assert rigidity<1e-5 and upper_error<1e-5
        assert np.isfinite(posed).all() and np.max(delta[ids])>.005
        probe.append({'side':side,'shinDegrees':degrees,'upperBodyMaxDisplacement':upper_error,'soleMaxDistanceError':rigidity,'soleMaxMovement':float(np.max(delta[ids]))})
        bone.matrix_basis.identity();bpy.context.view_layer.update()
assert uv_hash()==old_uv
scene['PREP_role']='partial-binding-review-not-runtime-not-neutral'
scene['PREP_pending']='Pelvis/torso/head/arms refit, separation of hair/hand weights, neutralization, native motion, full visual QA.'
scene['PREP_source_runtime']='Unchanged: CHR_thai_student_v9_Actions_v3.glb'
OUT.parent.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,
    export_animations=False,export_skins=True,export_image_format='AUTO',export_cameras=False,export_lights=False,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'partial-leg-bind-corrected-awaiting-independent-reimport',
 'scope':'Rest binding and weights below 0.66m only. Original casual pose retained; NOT neutral/playable motion.',
 'sourceRuntimeSha256':'e8c0255021d828b368888c99b272e33071e1c4186d49fe8c4e481e1670e6a638',
 'sourceVertices':31726,'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),'uvSha256':old_uv,'topologySha256':old_topology,
 'maxRestMeshDisplacement':max_rest,'regionalWeights':regional,'changedWeightVertices':len(changed),'unmodifiedWeightVertices':len(outside),
 'landmarkEvidence':landmark_errors,'landmarks':landmarks,'oldRestBones':old_bones,
 'newRestBones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in arm.data.bones},
 'articulationProbes':probe,'glb':{'path':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'bytes':OUT.stat().st_size},
 'library':str(WORK),'runtimeChanged':False,'masterChanged':False,'visualReview':'pending','nativeWalkValidated':False,
 'pending':['Review/refit pelvis, torso, head and both arms.','Separate raised hand/hair skin weights.','Lower arms and straighten body without stretching limb lengths.','Retarget Anime Idle/Walk and verify both soles.']}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','maxRestMeshDisplacement','changedWeightVertices','landmarkEvidence','glb']}))
