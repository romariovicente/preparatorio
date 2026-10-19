import bpy,shutil
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
p=ROOT/'frontend/public/assets/additions20261016/FAUNA_FOX_20261016.glb';dst=ROOT/'art/blender/checkpoints/FAUNA_FOX_SECOND_EXPORT_SKIN_MISMATCH_20261016.glb'
assert p.exists() and not dst.exists()
shutil.copy2(p,dst);assert p.read_bytes()==dst.read_bytes();p.unlink()
for name in ['PREP_FAUNA_FOX_20261016','PREP_FAUNA_QA_FOX_20261016']:
 s=bpy.data.scenes[name];s.name='FAILED2_'+name
 s['purpose']='Preserved trial skin re-export; evaluated pose mismatch. Not a published runtime asset.'
print('Second trial preserved. Delivery will retain verified source GLB bytes and skin inverse binds.')
