"""Append the reviewed Alchemist scene without changing any existing scene."""
import bpy,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
CHECKPOINT=ROOT/'art/blender/checkpoints/BEFORE_ALCHEMIST_NATIVE_MOTION_20261022.blend'
LIBRARY=ROOT/'art/blender/libraries/PREP_CHARACTER_ALCHEMIST_REIMPORT_20261022.blend'
EXPECTED='6dc8685b2a2bccbf3c9a4ceccb9be5c2ff612264aff329b9b37d7e6b9bb2e3cb'
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert not bpy.data.is_dirty
assert sha(CHECKPOINT)==EXPECTED
active=Path(bpy.data.filepath).resolve()
if active==MASTER.resolve():
    assert sha(MASTER)==EXPECTED
else:
    assert active==CHECKPOINT.resolve()
    intermediate=ROOT/'art/blender/checkpoints/BEFORE_ALCHEMIST_FOOT_SUPPORT_FINAL_20261022.blend'
    assert sha(MASTER)==sha(intermediate)=='231fe1ac19dbd1d19cfa78dd6b817267cfb7da29fafd223020fddaf96e9be01b'
qa=json.loads((ROOT/'reports/CHARACTER_ALCHEMIST_REIMPORT_20261022.json').read_text(encoding='utf-8'))
assert all(qa['checks'].values()) and qa['visualReview'].startswith('passed')
runtime=ROOT/'frontend/public/assets/characters/CHR_Alchemist_Anime_Retarget_20261022.glb'
assert sha(runtime)==qa['source']['sha256']
before={s.name:len(s.objects) for s in bpy.data.scenes}
name='PREP_CHARACTER_ALCHEMIST_ANIME_VALIDATED_20261022'
assert name not in bpy.data.scenes
with bpy.data.libraries.load(str(LIBRARY),link=False) as (source,target):
    assert qa['scene'] in source.scenes
    target.scenes=[qa['scene']]
scene=target.scenes[0];scene.name=name
bpy.context.window.scene=scene
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==len(meshes)==1 and len(arms[0].data.bones)==20
for track in arms[0].animation_data.nla_tracks:track.mute=track.name.rsplit('|',1)[-1]!='Idle'
scene.frame_set(1)
scene['PREP_role']='validated-playable-character-locomotion'
scene['PREP_runtime_asset']='/assets/characters/'+runtime.name
scene['PREP_runtime_sha256']=qa['source']['sha256']
scene['PREP_motion_origin']='Anime CyberStyle native Idle/Walk adapted to Alchemist; original source unchanged'
scene['PREP_scale_reference']='Remy 1.70m'
scene['PREP_validation_report']='reports/CHARACTER_ALCHEMIST_REIMPORT_20261022.json'
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
assert all(len(bpy.data.scenes[n].objects)==count for n,count in before.items())
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'validated-scene-integrated-master-saved',
 'master':{'path':str(MASTER),'sha256':sha(MASTER),'bytes':MASTER.stat().st_size},
 'checkpoint':{'path':str(CHECKPOINT),'sha256':EXPECTED},'scene':name,'preexistingScenes':len(before),
 'totalScenes':len(bpy.data.scenes),'preexistingSceneObjectCountsPreserved':True,'runtimeHash':qa['source']['sha256']}
(ROOT/'reports/CHARACTER_ALCHEMIST_MASTER_20261022.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
