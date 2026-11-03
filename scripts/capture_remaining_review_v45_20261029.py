"""Capture only the already-open Blender window, without activating it."""
import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
out=ROOT/'reports/thai_remaining_review_v45_20261029/blender_window_remaining_back_v45.png';assert not out.exists()
window=bpy.context.window or bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=window):assert bpy.ops.screen.screenshot(filepath=str(out))=={'FINISHED'}
meta={'path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source':'existing Blender window buffer','file':bpy.data.filepath,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'humanClicksClaimed':False}
(out.parent/'window_capture_back_v45.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');print(json.dumps(meta))
