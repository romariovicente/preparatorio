"""Root integration of the accepted white uniform and surface identity QA scene."""
import bpy,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
CHECKPOINT=ROOT/'art/blender/checkpoints/BEFORE_REMY_SURFACE_IDENTITY_20261022.blend'
LIBRARY=ROOT/'art/blender/libraries/PREP_REMY_WHITE_UNIFORM_SURFACE_VALIDATED_FINAL_20261022.blend'
EXPECTED='9ffe79e1399809aeeff6d62e2843de063067303bb268b314df2f3e248f498928'
SCENE='PREP_REMY_WHITE_UNIFORM_SURFACE_REIMPORT_FINAL_20261022'
FINAL='PREP_REMY_WHITE_UNIFORM_IDENTITY_VALIDATED_20261022'
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert Path(bpy.data.filepath).resolve()==MASTER.resolve() and not bpy.data.is_dirty
assert sha(MASTER)==sha(CHECKPOINT)==EXPECTED
qa=json.loads((ROOT/'reports/costumes/REMY_WHITE_UNIFORM_SURFACE_REIMPORT_20261022.json').read_text())
assert all(qa['checks'].values()) and qa['visualReview'].startswith('passed')
asset=ROOT/'frontend/public/assets/characters/runtime/CHR_Remy_White_Uniform_Surface_Web_20261022.glb'
assert sha(asset)==qa['sha256']
assert FINAL not in bpy.data.scenes
before={scene.name:len(scene.objects) for scene in bpy.data.scenes}
with bpy.data.libraries.load(str(LIBRARY),link=False) as (source,target):
    assert SCENE in source.scenes;target.scenes=[SCENE]
scene=target.scenes[0];scene.name=FINAL;bpy.context.window.scene=scene
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==1 and len(arms[0].data.bones)==55 and len(meshes)==27
decals=[o for o in meshes if o.get('uniformSurfaceAttachment')]
assert len(decals)==6
for obj in decals:
    preview=obj.modifiers.get('QA_preview_depth_separation_only')
    if preview:preview.show_viewport=True;preview.show_render=True
for track in arms[0].animation_data.nla_tracks:track.mute=not track.name.endswith('Idle')
scene.frame_set(1)
scene['PREP_role']='white-uniform-surface-identity-qa'
scene['PREP_runtime_asset']='/assets/characters/runtime/CHR_Remy_White_Uniform_Surface_Web_20261022.glb'
scene['PREP_runtime_sha256']=qa['sha256']
scene['PREP_scrub_color']='white'
scene['PREP_demo_names_only']=True
scene['PREP_preview_only_depth_separation_meters']=.00035
scene['PREP_runtime_identity']='coplanar garment triangles; material polygon offset; individual player profile name'
assert all(len(bpy.data.scenes[name].objects)==count for name,count in before.items())
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'integrated-and-master-saved',
        'master':str(MASTER),'masterSha256':sha(MASTER),'masterBytes':MASTER.stat().st_size,
        'checkpoint':str(CHECKPOINT),'checkpointSha256':EXPECTED,'scene':FINAL,'runtimeSha256':qa['sha256'],
        'preexistingScenes':len(before),'totalScenes':len(bpy.data.scenes),'preexistingSceneCountsPreserved':True,
        'meshes':27,'bones':55,'attachedIdentityMeshes':6,'scrubColor':'white',
        'demoNamesInReviewOnly':True,'runtimeUsesIndividualPlayerName':True}
(ROOT/'reports/costumes/REMY_WHITE_UNIFORM_MASTER_20261022.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
