import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
for area in bpy.context.window.screen.areas:
    if area.type=='VIEW_3D':
        rv=area.spaces.active.region_3d;rv.view_rotation=Vector((0,1,0)).to_track_quat('Z','Y');rv.view_perspective='ORTHO';rv.view_location=(0,.08,1.28);rv.view_distance=.93;area.tag_redraw()
print(json.dumps({'navigationOnly':True,'geometryOrSourceEdited':False,'viewSavedIntoLibrary':False,'windowFocusedOrMoved':False,'desktopSwitched':False}))
