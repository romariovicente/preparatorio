"""Resume from the latest saved hospital master without losing an open scene."""
import bpy,json
from pathlib import Path
from datetime import datetime
ROOT=Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
source=ROOT/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
target=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert not target.exists(),'Inspect the existing Oct16 master before making another.'
assert not bpy.data.filepath and len(bpy.data.objects)==3,'Another scene is open; preserve and inspect it before replacing.'
checkpoint=ROOT/('art/blender/checkpoints/BEFORE_ASSETS_RESUME_20261016_'+datetime.now().strftime('%H%M%S_%f')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
assert checkpoint.exists()
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
assert 'PREP_HOSPITAL_RECEPTION_20261015' in bpy.data.scenes
assert 'PREP_HOSPITAL_GLB_QA_20261015' in bpy.data.scenes
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False)
report={'source':str(source),'master':str(target),'checkpoint':str(checkpoint),'bytes':target.stat().st_size,
        'scenes':len(bpy.data.scenes),'objects':len(bpy.data.objects),'timeLocal':datetime.now().astimezone().isoformat(timespec='seconds')}
(ROOT/'reports/BLENDER_RESUME_20261016.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
