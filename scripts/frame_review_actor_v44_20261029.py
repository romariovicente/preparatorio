import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_20261029.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])
rows=[]
for name in ['V28_Clinical_Standard_Rig','V35_Local_Pose_Clearance_Rig']:
    bpy.data.objects[name].hide_set(True)
for window in bpy.context.window_manager.windows:
    if window.scene.name!='REVIEW_THAI_POSE_CONTROLS_V44':continue
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active;old=space.lens;space.lens=50
            selection=list(bpy.context.selected_objects);active=window.view_layer.objects.active
            for obj in selection:obj.select_set(False)
            for name in ['V44_Interactive_Pose_Study_Actor','V28_Thai_Face_And_Hair_Preserved']:bpy.data.objects[name].select_set(True)
            window.view_layer.objects.active=bpy.data.objects['V44_Interactive_Pose_Study_Actor']
            region=next(x for x in area.regions if x.type=='WINDOW')
            with bpy.context.temp_override(window=window,area=area,region=region):
                result=bpy.ops.view3d.view_axis(type='FRONT',align_active=False)
                assert result=={'FINISHED'}
                assert bpy.ops.view3d.view_selected(use_all_regions=False)=={'FINISHED'}
            for obj in bpy.context.selected_objects:obj.select_set(False)
            for obj in selection:obj.select_set(True)
            window.view_layer.objects.active=active
            area.tag_redraw()
            rows.append({'previousLens':old,'currentLens':space.lens,'distance':space.region_3d.view_distance,'viewLocation':list(space.region_3d.view_location),'lockObject':None if space.lock_object is None else space.lock_object.name})
print(json.dumps({'viewports':rows,'UIOnly':True,'windowFocusedOrMoved':False,'desktopSwitched':False}))
