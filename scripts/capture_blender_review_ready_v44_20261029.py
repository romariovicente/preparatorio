import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
out=ROOT/'reports/pose_review_controller_v44_20261029/blender_window_review_v44_final.png'
assert not out.exists()
window=bpy.context.window or bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=window):assert bpy.ops.screen.screenshot(filepath=str(out))=={'FINISHED'}
meta={'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source':'existing Blender window buffer via bpy.ops.screen.screenshot','BlenderFile':bpy.data.filepath,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'geometryEdited':False,'humanClicksClaimed':False}
(out.parent/'window_capture_final_v44.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta))
