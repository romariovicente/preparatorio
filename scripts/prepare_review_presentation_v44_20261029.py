"""Arrange the existing Blender review viewport; never activate an OS window."""
import bpy,json,math,sys
from mathutils import Quaternion,Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
module=sys.modules['preparatorio_review_v44']
module._verify_bind(module.actor(bpy.context.scene),module._candidate())
assert [bpy.context.scene.get('PREP_review_last_clip'),bpy.context.scene.get('PREP_review_last_frame'),bpy.context.scene.get('PREP_review_last_branch'),bpy.context.scene.get('PREP_review_last_variant')]==['Idle',101,'corrected','study']
views=[]
for window in bpy.context.window_manager.windows:
    if window.scene.name!=r['scene']:continue
    for area in window.screen.areas:
        if area.type!='VIEW_3D':continue
        space=area.spaces.active
        space.show_region_ui=True
        space.clip_start=.01;space.clip_end=1000
        rv=space.region_3d
        rv.view_perspective='ORTHO';rv.view_rotation=Quaternion((math.sqrt(.5),math.sqrt(.5),0,0))
        rv.view_location=Vector((0,0,.86));rv.view_distance=2.8
        region=next(x for x in area.regions if x.type=='UI')
        region.active_panel_category='Preparatório'
        area.tag_redraw()
        views.append({'activeCategory':region.active_panel_category,'viewLocation':list(rv.view_location),'viewDistance':rv.view_distance,'viewRotation':list(rv.view_rotation),'perspective':rv.view_perspective})
assert views and all(x['activeCategory']=='Preparatório' for x in views)
print(json.dumps({'viewports':views,'geometryEdited':False,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False}))
