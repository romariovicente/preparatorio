"""Persist the staged scene rename without changing geometry or source files."""
import bpy, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
report=ROOT/'reports/CHARACTER_THAI_SKIRT_V33_STAGE_20261028.json'
data=json.loads(report.read_text())
assert Path(bpy.data.filepath)==Path(data['working'])
window=bpy.context.window or bpy.context.window_manager.windows[0]
assert window.scene.name==data['scene']=='REVIEW_THAI_SKIRT_RECONSTRUCTION_V33'
with bpy.context.temp_override(window=window):
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
data['workingSha256']=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
data['sceneRenamePersisted']=True
report.write_text(json.dumps(data,indent=2))
print(json.dumps({'working':bpy.data.filepath,'sha256':data['workingSha256'],'dirty':bpy.data.is_dirty}))
