"""Fit editable humanoid FK rigs to supplied scans, re-pose and export game clips.

These are prototype skin weights, not a claim of production-quality scan retopology.
Original GLBs and prepared static derivatives are preserved.
"""
import bpy,json,math,struct,hashlib,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'frontend/public/assets/characters';OUT.mkdir(parents=True,exist_ok=True)
REPORTS=ROOT/'reports/rigs';REPORTS.mkdir(parents=True,exist_ok=True)

def base():
    p={'hip':(0,0,.86),'spine':(0,0,1.05),'chest':(0,0,1.28),'neck':(0,0,1.43),'head':(0,-.015,1.5),'crown':(0,0,1.67)}
    for side,s in [('L',1),('R',-1)]:
        for key,v in {'shoulder':(.2,0,1.32),'elbow':(.28,0,1.05),'wrist':(.33,-.02,.82),'hand':(.34,-.04,.73),'hip':(.1,0,.86),'knee':(.11,-.015,.46),'ankle':(.11,0,.1),'toe':(.11,-.17,.05)}.items():p[side+'_'+key]=(v[0]*s,v[1],v[2])
    return p

def fit(name):
    p=base()
    if name=='doctor_horror_hospital':
        for side,s in [('L',1),('R',-1)]:
            for key,v in {'shoulder':(.24,0,1.32),'elbow':(.54,0,1.32),'wrist':(.82,0,1.31),'hand':(.94,0,1.30)}.items():p[side+'_'+key]=(v[0]*s,v[1],v[2])
    elif name=='bone_seraph_skeletal_angel':
        p.update(hip=(0,.02,.78),spine=(0,.02,.99),chest=(0,0,1.2),neck=(0,0,1.31),head=(0,-.04,1.4),crown=(0,0,1.57))
        for side,s in [('L',1),('R',-1)]:
            for key,v in {'shoulder':(.18,.02,1.23),'elbow':(.23,0,.98),'wrist':(.27,-.03,.78),'hand':(.26,-.03,.67),'hip':(.09,.02,.78),'knee':(.09,0,.43),'ankle':(.09,0,.1),'toe':(.09,-.16,.04),'wing':(.65,.12,.83)}.items():p[side+'_'+key]=(v[0]*s,v[1],v[2])
    elif name.startswith('plague_doctor'):
        p.update(neck=(0,0,1.35),head=(0,-.035,1.47),crown=(0,0,1.61))
        if 'bone_mask' in name:p.update(R_elbow=(-.30,-.06,1.08),R_wrist=(-.44,-.11,.96),R_hand=(-.45,-.12,.88),cane=(-.42,-.12,.06))
    elif name=='school_girl_v21':
        p.update(L_shoulder=(.16,0,1.29),L_elbow=(.23,-.015,1.03),L_wrist=(.42,-.05,1.22),L_hand=(.48,-.055,1.25),R_shoulder=(-.17,0,1.30),R_elbow=(-.27,-.02,1.13),R_wrist=(-.31,-.02,1.35),R_hand=(-.34,-.02,1.38),L_knee=(.13,.01,.47),L_ankle=(.15,.03,.11),R_knee=(-.17,-.03,.48),R_ankle=(-.32,-.06,.09),R_toe=(-.36,-.17,.03))
    elif name=='thai_student_v9':
        p.update(hip=(0,.13,.79),spine=(0,.05,1.0),chest=(0,-.12,1.24),neck=(0,-.19,1.4),head=(0,-.22,1.51),crown=(0,-.2,1.65),L_shoulder=(.16,-.1,1.29),L_elbow=(.25,0,1.11),L_wrist=(.32,-.05,.91),L_hand=(.37,-.10,.88),R_shoulder=(-.18,-.14,1.3),R_elbow=(-.28,-.37,1.28),R_wrist=(-.3,-.47,1.52),R_hand=(-.3,-.52,1.65),L_hip=(.1,.13,.79),R_hip=(-.1,.13,.79),L_knee=(.19,-.08,.45),R_knee=(-.20,-.14,.40),L_ankle=(.22,.06,.11),R_ankle=(-.29,.03,.1),L_toe=(.27,-.09,.045),R_toe=(-.3,-.13,.04))
    elif name=='japanese_school_girl_v25':
        p.update(hip=(0,.16,.34),spine=(0,.14,.69),chest=(0,.12,1.09),neck=(0,.06,1.30),head=(0,.01,1.48),crown=(0,.03,1.68))
        for side,s in [('L',1),('R',-1)]:
            for key,v in {'shoulder':(.28,.13,1.11),'elbow':(.31,.15,.60),'wrist':(.34,.14,.14),'hand':(.42,.04,.08),'hip':(.15,.13,.3),'knee':(.19,-.59,.12),'ankle':(.65,-.24,.08),'toe':(.82,-.25,.07)}.items():p[side+'_'+key]=(v[0]*s,v[1],v[2])
    elif name=='woman_seated_v15':
        p.update(hip=(0,.2,.67),spine=(0,.18,.87),chest=(0,.17,1.19),neck=(0,.14,1.39),head=(0,.10,1.52),crown=(0,.10,1.68),L_shoulder=(.20,.18,1.24),R_shoulder=(-.20,.18,1.24),L_elbow=(.25,.15,.95),R_elbow=(-.25,.15,.95),L_wrist=(.37,.17,.69),R_wrist=(-.32,.10,.76),L_hand=(.44,.17,.61),R_hand=(-.40,.10,.73),L_hip=(.12,.2,.67),R_hip=(-.12,.2,.67),L_knee=(.12,-.41,.65),R_knee=(-.44,-.34,.61),L_ankle=(.05,-.29,.1),R_ankle=(-.25,-.25,.12),L_toe=(.02,-.46,.025),R_toe=(-.28,-.42,.04))
    elif name=='woman_standing_v33':
        p.update(hip=(0,.38,1.34),spine=(0,.16,1.42),chest=(0,-.14,1.41),neck=(0,-.38,1.43),head=(0,-.56,1.39),crown=(0,-.60,1.58))
        for side,s in [('L',1),('R',-1)]:
            for key,v in {'shoulder':(.22,-.23,1.35),'elbow':(.23,-.14,.87),'wrist':(.18,-.17,.40),'hand':(.16,-.19,.28),'hip':(.14,.38,1.31),'knee':(.15,.16,.69),'ankle':(.18,.05,.11),'toe':(.18,-.17,.035)}.items():p[side+'_'+key]=(v[0]*s,v[1],v[2])
    elif name=='woman_standing_v38__eko':
        p.update(hip=(0,.27,1.15),spine=(0,.13,1.25),chest=(0,-.12,1.33),neck=(0,-.3,1.47),head=(0,-.43,1.5),crown=(0,-.4,1.66),L_shoulder=(.2,-.15,1.33),R_shoulder=(-.2,-.15,1.33),L_elbow=(.15,-.25,.92),R_elbow=(-.18,-.30,.91),L_wrist=(.11,-.38,.50),R_wrist=(-.1,-.41,.49),L_hand=(.08,-.45,.43),R_hand=(-.10,-.47,.42),L_hip=(.11,.27,1.15),R_hip=(-.11,.27,1.15),L_knee=(.14,.06,.63),R_knee=(-.13,-.22,.89),L_ankle=(.13,.22,.14),R_ankle=(-.08,-.39,.45),L_toe=(.12,.01,.055),R_toe=(-.08,-.61,.41))
    if name=='dark_necromancer___corrupted_staff__':p.update(R_elbow=(-.25,-.03,1.08),R_wrist=(-.27,-.22,1.2),R_hand=(-.27,-.27,1.18),cane=(-.27,-.27,.05))
    return {k:Vector(v) for k,v in p.items()}

def definitions(p):
    bones=[('root',Vector((0,0,0)),Vector((0,0,.12)),None),('hips',p['hip'],p['spine'],'root'),('spine',p['spine'],p['chest'],'hips'),('chest',p['chest'],p['neck'],'spine'),('neck',p['neck'],p['head'],'chest'),('head',p['head'],p['crown'],'neck')]
    for s in ['L','R']:
        bones += [(s+'_clavicle',p['chest'],p[s+'_shoulder'],'chest'),(s+'_upper_arm',p[s+'_shoulder'],p[s+'_elbow'],s+'_clavicle'),(s+'_forearm',p[s+'_elbow'],p[s+'_wrist'],s+'_upper_arm'),(s+'_hand',p[s+'_wrist'],p[s+'_hand'],s+'_forearm'),(s+'_thigh',p[s+'_hip'],p[s+'_knee'],'hips'),(s+'_shin',p[s+'_knee'],p[s+'_ankle'],s+'_thigh'),(s+'_foot',p[s+'_ankle'],p[s+'_toe'],s+'_shin')]
        if s+'_wing' in p:bones.append((s+'_wing',p[s+'_shoulder'],p[s+'_wing'],'chest'))
    if 'cane' in p:bones.append(('cane',p['R_hand'],p['cane'],'R_hand'))
    return bones

def process(scene):
    name=scene.name[4:];dest=OUT/('CHR_'+name+'_Rig_v2.glb')
    if (REPORTS/(name+'.json')).exists():return
    if dest.exists():return
    bpy.context.window.scene=scene;obj=next(o for o in scene.objects if o.type=='MESH')
    src=fit(name);defs=definitions(src)
    data=bpy.data.armatures.new('ARM_'+name);arm=bpy.data.objects.new('CHR_'+name+'_Rig',data);scene.collection.objects.link(arm)
    arm.show_in_front=True;data.display_type='OCTAHEDRAL';bpy.context.view_layer.objects.active=arm;arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n,a,b,parent in defs:
        bone=data.edit_bones.new(n);bone.head=a;bone.tail=b;bone.use_deform=n!='root';bone.align_roll(Vector((0,-1,0)))
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    # Distance-to-bone skinning with four normalized influences per vertex.
    vertices=np.array([tuple(v.co) for v in obj.data.vertices]);deform=defs[1:]
    distances=[]
    for n,a,b,parent in deform:
        a=np.array(a);direction=np.array(b)-a;t=np.clip(((vertices-a)@direction)/(direction@direction),0,1)
        distances.append(np.linalg.norm(vertices-(a+t[:,None]*direction),axis=1))
    distances=np.stack(distances,axis=1);nearest=np.argsort(distances,axis=1)[:,:4]
    values=1/(np.take_along_axis(distances,nearest,axis=1)**2+.0025)**3;values/=values.sum(axis=1)[:,None]
    groups=[obj.vertex_groups.new(name=d[0]) for d in deform]
    for i in range(len(vertices)):
        for j,w in zip(nearest[i],values[i]):groups[int(j)].add([i],float(w),'REPLACE')
    obj.parent=arm;mod=obj.modifiers.new('PREP_Skin','ARMATURE');mod.object=arm
    # Only the neutral T-pose doctor passed standing re-pose visual review.
    if name=='doctor_horror_hospital':
        # Repose scans to a common standing rest pose. Meshes and weights remain editable.
        target=base()
        for s in ['L','R']:
            if s+'_wing' in src:target[s+'_wing']=(s=='L' and 1 or -1)*Vector((.65,0,0))+Vector((0,.12,.9))
        if 'cane' in src:target['cane']=Vector((-.34,-.08,.03))
        target={k:Vector(v) for k,v in target.items()};target_defs=definitions(target);target_matrices={}
        for n,a,b,parent in target_defs:
            old=data.bones[n];delta=(old.tail_local-old.head_local).rotation_difference(b-a)
            matrix=Matrix.Translation(a)@delta.to_matrix().to_4x4()@old.matrix_local.to_quaternion().to_matrix().to_4x4()
            target_matrices[n]=matrix
            ratio=(b-a).length/old.length
            arm.pose.bones[n].matrix=matrix@Matrix.Diagonal((1,ratio,1,1))
            bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
        for bone in arm.pose.bones:bone.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
        for n,a,b,parent in target_defs:
            bone=data.edit_bones[n];bone.matrix=target_matrices[n];bone.length=(b-a).length
        bpy.ops.object.mode_set(mode='OBJECT');mod=obj.modifiers.new('PREP_Skin','ARMATURE');mod.object=arm
    limited=name in ['japanese_school_girl_v25','woman_seated_v15','woman_standing_v33','woman_standing_v38__eko','dark_necromancer___corrupted_staff__']
    motion='Gesture' if limited else 'Walk'
    actions={}
    arm.animation_data_create()
    for clip,length in [('Idle',60),(motion,32)]:
        arm.animation_data.action=bpy.data.actions.new(name+'_'+clip)
        for frame in ([1,16,31,46,61] if clip=='Idle' else [1,5,9,13,17,21,25,29,33]):
            phase=(frame-1)/length*2*math.pi
            for bone in arm.pose.bones:bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
            if clip=='Idle':arm.pose.bones['spine'].rotation_euler.x=.015*math.sin(phase);arm.pose.bones['head'].rotation_euler.y=.02*math.sin(phase)
            elif clip=='Gesture':
                arm.pose.bones['head'].rotation_euler.x=.08*math.sin(phase)
                arm.pose.bones['L_forearm'].rotation_euler.x=.08*math.sin(phase)
            else:
                for s,offset in [('L',0),('R',math.pi)]:
                    cycle=math.sin(phase+offset);arm.pose.bones[s+'_thigh'].rotation_euler.x=.38*cycle
                    arm.pose.bones[s+'_shin'].rotation_euler.x=-max(0,-cycle)*.62
                    arm.pose.bones[s+'_upper_arm'].rotation_euler.x=-.25*cycle
                    arm.pose.bones[s+'_forearm'].rotation_euler.x=-.12
                arm.pose.bones['hips'].location.y=.018*abs(math.sin(phase*2))
            for bone in arm.pose.bones:
                for prop in ['rotation_euler','location','scale']:bone.keyframe_insert(data_path=prop,frame=frame,group=bone.name)
        actions[clip]=arm.animation_data.action
    arm.animation_data.action=None
    for clip,action in actions.items():
        track=arm.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action)
    scene.frame_start=1;scene.frame_end=60;scene.render.fps=30
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,
        export_animations=True,export_skins=True,export_animation_mode='NLA_TRACKS',export_image_format='JPEG',export_jpeg_quality=88,export_cameras=False,export_lights=False,export_extras=True)
    raw=dest.read_bytes();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
    assert doc.get('skins') and len(doc.get('animations',[]))==2,[(a.get('name')) for a in doc.get('animations',[])]
    # Verify a real mesh deformation and complete normalized skinning.
    for track in arm.animation_data.nla_tracks:track.mute=True
    arm.animation_data.action=actions[motion];scene.frame_set(1);bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();one=np.array([tuple(v.co) for v in obj.evaluated_get(dg).data.vertices])
    scene.frame_set(9);bpy.context.view_layer.update();two=np.array([tuple(v.co) for v in obj.evaluated_get(dg).data.vertices])
    movement=np.linalg.norm(two-one,axis=1);assert np.isfinite(two).all() and movement.max()>.01
    assert all(abs(sum(g.weight for g in v.groups)-1)<.0001 for v in obj.data.vertices)
    # Reimport independently and verify bones, weights and modifiers survive.
    validation=bpy.data.scenes.new('VALIDATE_'+name);bpy.context.window.scene=validation
    bpy.ops.import_scene.gltf(filepath=str(dest))
    imported_arm=next(o for o in validation.objects if o.type=='ARMATURE')
    imported_meshes=[o for o in validation.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
    assert imported_meshes and len(imported_arm.data.bones)>=len(defs)-1
    assert all(v.groups for o in imported_meshes for v in o.data.vertices)
    bpy.context.window.scene=scene;arm.animation_data.action=actions['Idle'];scene.frame_set(1)
    scene.camera.location=(2.5,-5,2);scene.camera.rotation_euler=(Vector((0,0,.85))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=2.3
    scene.render.filepath=str(REPORTS/(name+'_rig.png'));bpy.ops.render.render(write_still=True)
    report={'id':scene['source_id'],'url':'/assets/characters/'+dest.name,'bones':len(data.bones),'skinnedVertices':len(obj.data.vertices),'weightCoverage':1,'maxInfluences':4,'clips':[a['name'] for a in doc['animations']],'maxWalkDeformation':float(movement.max()),'reimportValidated':True,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'quality':'prototype','playable':not limited,'needsRepose':limited,'notes':'Editable fitted FK rig. Original pose preserved except the approved doctor T-pose conversion. Procedural clips; limited-pose characters need retopology/repose before locomotion.'}
    (REPORTS/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))

chosen=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else None
for scene in list(bpy.data.scenes):
    if scene.name.startswith('RIG_') and (not chosen or scene.name=='RIG_'+chosen):process(scene)
records=[json.loads(p.read_text(encoding='utf-8')) for p in REPORTS.glob('*.json')]
(ROOT/'frontend/src/config/riggedAssets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
