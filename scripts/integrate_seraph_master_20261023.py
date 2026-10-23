"""Append only the accepted Seraph review scene to the preserved master."""
import bpy,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
CHECKPOINT=ROOT/'art/blender/checkpoints/BEFORE_SERAPH_NATIVE_MOTION_20261023.blend'
LIBRARY=ROOT/'art/blender/libraries/PREP_CHARACTER_SERAPH_REIMPORT_20261023.blend'
EXPECTED='0fb41499127f71e4a110c9849c9c3ec3aee28dcd7c4cc6a2d4c6b8262f030114'
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert Path(bpy.data.filepath).resolve()==MASTER.resolve() and not bpy.data.is_dirty
assert sha(MASTER)==sha(CHECKPOINT)==EXPECTED
qa=json.loads((ROOT/'reports/CHARACTER_SERAPH_REIMPORT_20261023.json').read_text(encoding='utf-8'))
assert all(qa['checks'].values()) and qa['visualReview'].startswith('passed')
runtime=ROOT/'frontend/public/assets/characters/CHR_Seraph_Anime_Retarget_20261023.glb'
assert sha(runtime)==qa['source']['sha256']
before={s.name:len(s.objects) for s in bpy.data.scenes}
name='PREP_CHARACTER_SERAPH_ANIME_VALIDATED_20261023'
assert name not in bpy.data.scenes
with bpy.data.libraries.load(str(LIBRARY),link=False) as (source,target):
    assert qa['scene'] in source.scenes
    target.scenes=[qa['scene']]
scene=target.scenes[0];scene.name=name
bpy.context.window.scene=scene
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==len(meshes)==1 and len(arms[0].data.bones)==22
for t in arms[0].animation_data.nla_tracks:t.mute=t.name.rsplit('|',1)[-1]!='Idle'
scene.frame_set(1)
scene['PREP_role']='validated-playable-character-locomotion'
scene['PREP_runtime_asset']='/assets/characters/'+runtime.name
scene['PREP_runtime_sha256']=qa['source']['sha256']
scene['PREP_motion_origin']='Anime CyberStyle native Idle/Walk adapted to FK22; wings inherit chest, halo inherits head'
scene['PREP_validation_report']='reports/CHARACTER_SERAPH_REIMPORT_20261023.json'
scene['PREP_scale_reference']='Remy 1.70m total height, including halo'
scene['PREP_desktop_rule']='Project windows remain on Desktop 1; Desktop 2 is reserved for other students.'
assert all(len(bpy.data.scenes[n].objects)==count for n,count in before.items())
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'validated-scene-integrated-master-saved',
 'master':{'path':str(MASTER),'sha256':sha(MASTER),'bytes':MASTER.stat().st_size},
 'checkpoint':{'path':str(CHECKPOINT),'sha256':EXPECTED},'scene':name,'preexistingScenes':len(before),
 'totalScenes':len(bpy.data.scenes),'preexistingSceneObjectCountsPreserved':True,'runtimeHash':qa['source']['sha256'],
 'windowsDesktopChanged':False,'newWindowOpened':False}
(ROOT/'reports/CHARACTER_SERAPH_MASTER_20261023.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
