"""Append the independently validated retarget scene to the checkpointed master."""
import bpy
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
CHECKPOINT=ROOT/'art/blender/checkpoints/BEFORE_CYBERPUNK_REMY_INTEGRATION_20261022.blend'
LIBRARY=ROOT/'art/blender/libraries/PREP_CHARACTER_CYBERPUNK_REMY_REIMPORT_20261022_v2.blend'
REPORT=ROOT/'reports/CHARACTER_CYBERPUNK_REMY_MASTER_20261022.json'
EXPECTED='86c54359f4d521b2a797e06c299952ea3fbcc3e5abb689acceabd2ba426226e8'
SCENE='VALIDATE_CYBERPUNK_REMY_20261022'
FINAL_SCENE='PREP_CHARACTER_CYBERPUNK_WALK_VALIDATED_20261022'

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()

assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
assert not bpy.data.is_dirty
assert sha(MASTER)==sha(CHECKPOINT)==EXPECTED
qa=json.loads((ROOT/'reports/CHARACTER_CYBERPUNK_REMY_REIMPORT_20261022_v2.json').read_text(encoding='utf-8'))
assert all(qa['checks'].values()) and qa['visualReview'].startswith('passed')
assert FINAL_SCENE not in bpy.data.scenes
before={scene.name:len(scene.objects) for scene in bpy.data.scenes}
with bpy.data.libraries.load(str(LIBRARY),link=False) as (source,target):
    assert SCENE in source.scenes
    target.scenes=[SCENE]
scene=target.scenes[0]
scene.name=FINAL_SCENE
bpy.context.window.scene=scene
armatures=[obj for obj in scene.objects if obj.type=='ARMATURE']
meshes=[obj for obj in scene.objects if obj.type=='MESH']
assert len(armatures)==1 and len(meshes)==35
arm=armatures[0]
clips=[]
for track in arm.animation_data.nla_tracks:
    clip=track.name.rsplit('|',1)[-1]
    clips.append(clip)
    track.mute=clip!='Idle'
assert sorted(clips)==['Idle','Walk']
scene.frame_set(1)
scene['PREP_role']='validated-playable-character-retarget'
scene['PREP_runtime_asset']='/assets/characters/CHR_Cyberpunk_Remy_Retarget_20261022_v2.glb'
scene['PREP_runtime_sha256']=qa['source']['sha256']
scene['PREP_validation_report']='reports/CHARACTER_CYBERPUNK_REMY_REIMPORT_20261022_v2.json'
scene['PREP_motion_origin']='Retargeted from genuine Remy Mixamo Idle and Walk'
scene['PREP_updated_at']=datetime.now(timezone.utc).isoformat()
assert all(bpy.data.scenes[name] and len(bpy.data.scenes[name].objects)==count for name,count in before.items())
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'validated-retarget-appended-and-master-saved',
        'master':{'path':str(MASTER),'bytes':MASTER.stat().st_size,'sha256':sha(MASTER)},
        'checkpoint':{'path':str(CHECKPOINT),'sha256':EXPECTED},'scene':scene.name,'meshes':len(meshes),
        'armatures':1,'clips':clips,'preexistingSceneObjectCountsPreserved':True,
        'preexistingScenes':len(before),'totalScenes':len(bpy.data.scenes),'runtimeAssetHash':qa['source']['sha256']}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
