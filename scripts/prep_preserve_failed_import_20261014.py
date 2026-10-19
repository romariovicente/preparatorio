"""Preserve the incomplete additive import before repairing its shader lookup."""
import bpy
from pathlib import Path
from datetime import datetime
root=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
master=root/'art/blender/PREPARATORIO_PROJETO_20261014.blend'
if Path(bpy.data.filepath)!=master or bpy.context.scene.name!='PREP_JALECO_QA_20261014':
    raise RuntimeError('Unexpected state; refusing to restore')
checkpoint=root/f'art/blender/checkpoints/PARTIAL_JALECO_IMPORT_20261014_{datetime.now().strftime("%H%M%S_%f")}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
if not checkpoint.is_file():
    raise RuntimeError('Partial import was not preserved')
bpy.ops.wm.open_mainfile(filepath=str(master),load_ui=False,use_scripts=False)
print('Partial import preserved at '+str(checkpoint)+'; verified working master reopened for repair.')
