"""Anatomical neutral-reference corrections before retargeting real motion."""
from mathutils import Matrix, Vector


def fit_leg_motion(desired, reference, source, bones):
    """Fit anatomical segment directions, not incompatible rig joint axes."""
    before={name:matrix.copy() for name,matrix in desired.items()}
    overrides=set()
    hip_ratio=(reference['CC_Base_L_Thigh_04'].translation-reference['CC_Base_R_Thigh_018'].translation).length/(source['mixamorig:LeftUpLeg'].translation-source['mixamorig:RightUpLeg'].translation).length
    for side,code,ids in (('Left','L',('04','05','06','00')),('Right','R',('018','019','021','022'))):
        names=[f'CC_Base_{code}_{part}_{suffix}' for part,suffix in zip(('Thigh','Calf','Foot','ToeBase'),ids)]
        sources=['mixamorig:'+side+part for part in ('UpLeg','Leg','Foot','ToeBase')]
        position=desired['CC_Base_Hip_02'].translation+(source[sources[0]].translation-source['mixamorig:Hips'].translation)*hip_ratio
        for index,name in enumerate(names[:3]):
            ref_direction=reference[names[index+1]].translation-reference[name].translation
            direction=source[sources[index+1]].translation-source[sources[index]].translation
            previous_rotation=before[name].to_quaternion()
            previous_direction=previous_rotation @ reference[name].to_quaternion().inverted() @ ref_direction
            swing=previous_direction.normalized().rotation_difference(direction.normalized())
            desired[name]=Matrix.LocRotScale(position,swing @ previous_rotation,reference[name].to_scale())
            position=position+direction.normalized()*ref_direction.length
        desired[names[3]]=desired[names[2]] @ before[names[2]].inverted() @ before[names[3]]
        desired[names[3]].translation=position
        overrides.update(names)
    descendants=set(overrides)
    for bone in bones:
        if bone.name not in overrides and bone.parent and bone.parent.name in descendants:
            desired[bone.name]=desired[bone.parent.name] @ before[bone.parent.name].inverted() @ before[bone.name]
            descendants.add(bone.name)
    return desired


def corrected_reference(reference, source):
    result={name:matrix.copy() for name,matrix in reference.items()}
    report={}
    neck1='CC_Base_NeckTwist01_036'
    neck2='CC_Base_NeckTwist02_037'
    head='CC_Base_Head_038'
    eye_l='CC_Base_L_Eye_046'
    eye_r='CC_Base_R_Eye_045'
    right=(reference[eye_l].translation-reference[eye_r].translation).normalized()
    approximate_up=(reference[head].translation-reference[neck1].translation).normalized()
    front=right.cross(approximate_up).normalized()
    up=front.cross(right).normalized()
    basis=Matrix((right,-front,up)).transposed()
    correction=basis.inverted().to_4x4()
    center=(reference['CC_Base_L_Upperarm_050'].translation+reference['CC_Base_R_Upperarm_078'].translation)*.5
    old_base=reference[neck1].translation
    new_base=Vector((center.x,old_base.y,old_base.z))
    head_transform=Matrix.Translation(new_base) @ correction @ Matrix.Translation(-old_base)
    lengths=[(reference[neck2].translation-reference[neck1].translation).length,
             (reference[head].translation-reference[neck2].translation).length]
    for name,z in ((neck1,new_base.z),(neck2,new_base.z+lengths[0]),(head,new_base.z+sum(lengths))):
        result[name]=head_transform @ reference[name]
        result[name].translation=Vector((center.x,new_base.y,z))
    report['head']={'oldNeckBase':list(old_base),'newNeckBase':list(new_base),
                    'segmentLengths':lengths,'oldHead':list(reference[head].translation),
                    'newHead':list(result[head].translation),
                    'eyeFrameCorrectionQuaternion':list(correction.to_quaternion())}

    # Correct the complete hand: the original right finger reference still held
    # the removed gun even after the main arm bones had been lowered.
    reflection=Matrix.Diagonal((-1.,1.,1.,1.))
    finger_pairs={}
    for finger,left_ids,right_ids in (
        ('Index',('065','066','067'),('093','094','095')),
        ('Mid',('062','063','064'),('087','088','089')),
        ('Ring',('059','060','061'),('084','085','086')),
        ('Pinky',('056','057','058'),('096','097','098')),
        ('Thumb',('068','069','070'),('090','091','092')),
    ):
        for index,(left_id,right_id) in enumerate(zip(left_ids,right_ids),1):
            left=f'CC_Base_L_{finger}{index}_{left_id}'
            right_name=f'CC_Base_R_{finger}{index}_{right_id}'
            finger_pairs[right_name]=reflection @ reference[left] @ reflection
    result.update(finger_pairs)
    report['hand']={'mirroredFingerBones':len(finger_pairs),'method':'all five relaxed left-hand fingers mirrored to right in world X'}

    # Match each target segment's anatomical direction to Remy Idle, preserving
    # its length. Real Remy Walk deltas then reproduce a walking stance instead
    # of retaining the wide, outward-turned tactical stance of the source.
    legs={}
    hip_ratio=(reference['CC_Base_L_Thigh_04'].translation-reference['CC_Base_R_Thigh_018'].translation).length/(source['mixamorig:LeftUpLeg'].translation-source['mixamorig:RightUpLeg'].translation).length
    for side,code,ids in (
        ('Left','L',('04','05','06','00')),
        ('Right','R',('018','019','021','022')),
    ):
        names=[f'CC_Base_{code}_{part}_{suffix}' for part,suffix in zip(('Thigh','Calf','Foot','ToeBase'),ids)]
        source_names=['mixamorig:'+side+part for part in ('UpLeg','Leg','Foot','ToeBase')]
        position=reference['CC_Base_Hip_02'].translation+(source[source_names[0]].translation-source['mixamorig:Hips'].translation)*hip_ratio
        for index,name in enumerate(names[:3]):
            old_direction=reference[names[index+1]].translation-reference[name].translation
            new_direction=source[source_names[index+1]].translation-source[source_names[index]].translation
            swing=old_direction.normalized().rotation_difference(new_direction.normalized())
            matrix=Matrix.LocRotScale(position,swing @ reference[name].to_quaternion(),reference[name].to_scale())
            result[name]=matrix
            position=position+new_direction.normalized()*old_direction.length
        toe_transform=result[names[2]] @ reference[names[2]].inverted()
        result[names[3]]=toe_transform @ reference[names[3]]
        result[names[3]].translation=position
        legs[side]={'oldFoot':list(reference[names[2]].translation),'newFoot':list(result[names[2]].translation)}
    report['legs']=legs
    # Other descendants are propagated by the caller through their complete
    # parent-relative reference matrix (face, hair, twist, toe and share bones).
    overrides=set(finger_pairs)|{neck1,neck2,head}
    for code,ids in (('L',('04','05','06','00')),('R',('018','019','021','022'))):
        overrides.update(f'CC_Base_{code}_{part}_{suffix}' for part,suffix in zip(('Thigh','Calf','Foot','ToeBase'),ids))
    return result,overrides,report
