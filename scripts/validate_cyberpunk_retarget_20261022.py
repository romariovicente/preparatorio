"""Independently reimport the retarget GLB and measure skin/motion/ground contact."""
import bpy
import hashlib
import json
import math
import struct
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
VERSION = str(globals().get('PREP_RETARGET_VERSION',''))
assert VERSION in ('','_v2','_v3','_v4','_v5')
GLB = ROOT / f'art/character_retarget_20261022/CHR_Cyberpunk_Remy_Retarget_20261022{VERSION}.glb'
REPORT = ROOT / f'reports/CHARACTER_CYBERPUNK_REMY_REIMPORT_20261022{VERSION}.json'
BLEND = ROOT / f'art/blender/libraries/PREP_CHARACTER_CYBERPUNK_REMY_REIMPORT_20261022{VERSION}.blend'
raw = GLB.read_bytes()
length, kind = struct.unpack_from('<II',raw,12)
doc = json.loads(raw[20:20+length])
assert sorted(a['name'] for a in doc.get('animations',[])) == ['Idle','Walk']
assert len(doc['skins']) == 1
assert all('bufferView' in image for image in doc['images'])

scene = bpy.data.scenes.new('VALIDATE_CYBERPUNK_REMY_20261022')
bpy.context.window.scene = scene
bpy.ops.import_scene.gltf(filepath=str(GLB))
arms = [obj for obj in scene.objects if obj.type == 'ARMATURE']
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
assert len(arms) == 1
arm = arms[0]
assert meshes and arm.animation_data
clip_tracks = {}
for track in arm.animation_data.nla_tracks:
    suffix = track.name.rsplit('|',1)[-1]
    if suffix in ('Idle','Walk'):
        clip_tracks[suffix] = track
assert set(clip_tracks) == {'Idle','Walk'}, list(clip_tracks)

def points():
    graph = bpy.context.evaluated_depsgraph_get()
    arrays=[]
    for obj in meshes:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            coords=np.empty(len(mesh.vertices)*3,dtype=np.float32)
            mesh.vertices.foreach_get('co',coords)
            coords=coords.reshape(-1,3)
            matrix=np.array(evaluated.matrix_world)
            arrays.append(coords @ matrix[:3,:3].T + matrix[:3,3])
        finally:
            evaluated.to_mesh_clear()
    result=np.concatenate(arrays)
    assert np.isfinite(result).all()
    return result

max_influences=0
max_sum_error=0
unweighted=0
foot_indices={'L':[],'R':[]}
vertex_offset=0
for obj in meshes:
    bone_groups={group.index for group in obj.vertex_groups if group.name in arm.data.bones}
    # The sole also binds to individual toe bones, not only Foot/ToeBase.
    foot_bones={side:{bone.name for bone in arm.data.bones
                      if f'CC_Base_{side}_Foot_' in bone.name or
                      any(f'CC_Base_{side}_Foot_' in parent.name for parent in bone.parent_recursive)}
                for side in foot_indices}
    foot_groups={side:{group.index for group in obj.vertex_groups if group.name in names}
                 for side,names in foot_bones.items()}
    for vertex in obj.data.vertices:
        weights=[g.weight for g in vertex.groups if g.group in bone_groups and g.weight>1e-8]
        max_influences=max(max_influences,len(weights))
        max_sum_error=max(max_sum_error,abs(sum(weights)-1))
        unweighted+=not weights
        for side,group_indices in foot_groups.items():
            if sum(g.weight for g in vertex.groups if g.group in group_indices)>.5:
                foot_indices[side].append(vertex_offset+vertex.index)
    vertex_offset+=len(obj.data.vertices)
assert max_influences<=4 and max_sum_error<.003 and unweighted==0
assert all(foot_indices.values()), 'No independently weighted foot region found.'

rows=[]
for clip,track in clip_tracks.items():
    arm.animation_data.action=None
    for other in arm.animation_data.nla_tracks:
        other.mute=other!=track
    frames=[1,32.5,63,94.5,126,157.5,188,219.5,251] if clip=='Idle' else [1,4.5,9,12.5,17,20.5,25,28.5,32]
    samples=[]
    first=None
    for frame in frames:
        scene.frame_set(int(frame), subframe=frame-int(frame))
        bpy.context.view_layer.update()
        posed=points()
        if first is None:
            first=posed.copy()
        low,high=posed.min(axis=0),posed.max(axis=0)
        foot_minima={side:float(posed[indices,2].min()) for side,indices in foot_indices.items()}
        samples.append({'frame':frame,'min':low.tolist(),'max':high.tolist(),
                        'floorError':abs(float(low[2])), 'height':float(high[2]-low[2]),
                        'footMinima':foot_minima,
                        'maxVertexDisplacementFromFirst':float(np.linalg.norm(posed-first,axis=1).max())})
    rows.append({'clip':clip,'samples':samples})

max_floor=max(sample['floorError'] for row in rows for sample in row['samples'])
max_support_foot_error=max(abs(min(sample['footMinima'].values())) for row in rows for sample in row['samples'])
walk_displacement=max(sample['maxVertexDisplacementFromFirst'] for row in rows if row['clip']=='Walk' for sample in row['samples'])
checks={'freshBlenderReimport':True,'clipsIdleWalk':True,'maximumFourInfluences':max_influences<=4,
        'normalizedWeights':max_sum_error<.003,'fullWeightCoverage':unweighted==0,
        'floorContactWithin2cm':max_floor<=.02,'actualWalkDeformation':walk_displacement>.08,
        'supportingFootWithin2cm':max_support_foot_error<=.02,
        'idleHeightWithin2cm':abs(next(row for row in rows if row['clip']=='Idle')['samples'][0]['height']-1.7)<=.02}

# Review cameras and lights belong only to the validation scene.
scene.world=bpy.data.worlds.new('PREP_Cyberpunk_Retarget_Review_World')
scene.world.color=(.025,.035,.05)
for location,energy,size in (((2.4,-3.4,3),850,3),((-2.4,-1,2),500,2.5),((0,2.5,2.8),650,2)):
    bpy.ops.object.light_add(type='AREA',location=location)
    light=bpy.context.object
    light.data.energy=energy
    light.data.size=size
    light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add()
camera=bpy.context.object
scene.camera=camera
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=480
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
renders=[]
for clip,frame in [('Idle',1),('Walk',1),('Walk',9),('Walk',17),('Walk',25)]:
    for track in arm.animation_data.nla_tracks:
        track.mute=track!=clip_tracks[clip]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    posed=points()
    center=Vector(((posed.min(axis=0)+posed.max(axis=0))*.5).tolist())
    for name,offset in [('front',(0,-5,0)),('side',(5,0,0))]:
        camera.location=center+Vector(offset)
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type='ORTHO'
        camera.data.ortho_scale=1.98
        image=ROOT/f'reports/cyberpunk_reimport_20261022{VERSION}/{clip}_{frame:03d}_{name}.png'
        image.parent.mkdir(parents=True,exist_ok=True)
        scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        renders.append(str(image))

    if VERSION in ('_v3','_v4','_v5') and (clip,frame) in [('Idle',1),('Walk',9)]:
        for name,center,offset,scale in (
            ('head_front',Vector((0,-.02,1.49)),Vector((0,-3,0)),.55),
            ('hands_front',Vector((0,0,.93)),Vector((0,-3,0)),.83),
        ):
            camera.location=center+offset
            camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.ortho_scale=scale
            image=ROOT/f'reports/cyberpunk_reimport_20261022{VERSION}/{clip}_{frame:03d}_{name}.png'
            scene.render.filepath=str(image)
            bpy.ops.render.render(write_still=True)
            renders.append(str(image))

for track in arm.animation_data.nla_tracks:
    track.mute=track!=clip_tracks['Idle']
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'reimport-passed' if all(checks.values()) else 'reimport-failed',
        'source':{'path':str(GLB),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},
        'blend':str(BLEND),'checks':checks,'maxFloorError':max_floor,'walkDeformation':walk_displacement,
        'maxInfluences':max_influences,'maxWeightSumError':max_sum_error,'unweightedVertices':unweighted,
        'maxSupportingFootError':max_support_foot_error,'clipSamples':rows,'renders':renders,'visualReview':'pending','runtimeChanged':False}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:report[key] for key in ('status','checks','maxFloorError','walkDeformation','source')}))
assert all(checks.values()), checks
