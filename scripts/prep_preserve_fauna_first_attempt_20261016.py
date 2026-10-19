import bpy,json,shutil
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
p=ROOT/'frontend/public/assets/additions20261016/FAUNA_FOX_20261016.glb';dst=ROOT/'art/blender/checkpoints/FAUNA_FOX_FIRST_EXPORT_WITH_HELPER_20261016.glb'
assert p.exists() and not dst.exists()
shutil.copy2(p,dst)
assert p.read_bytes()==dst.read_bytes()
p.unlink()
for name in ['PREP_FAUNA_FOX_20261016','PREP_FAUNA_QA_FOX_20261016']:
 s=bpy.data.scenes[name];s.name='FAILED_'+name
 s['purpose']='Preserved first import for debugging; importer helper included; excluded from runtime catalog.'
 for o in s.objects:
  if o.type=='MESH' and len(o.data.vertices) in (42,240):o.hide_render=True;o.hide_viewport=True
print('Preserved failed first export and two source scenes; no existing project content removed.')
