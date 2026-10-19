"""Save a clear classroom inspection view without deleting the surrounding city."""
import bpy,json
from pathlib import Path
from mathutils import Vector
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
room=bpy.data.collections['ARAP_16_CLASSROOM_20261008']
for window in bpy.context.window_manager.windows:
    window.scene=scene
    for area in window.screen.areas:
        if area.type!='VIEW_3D':continue
        region=next(r for r in area.regions if r.type=='WINDOW')
        with bpy.context.temp_override(window=window,area=area,region=region):
            if area.spaces.active.local_view:bpy.ops.view3d.localview(frame_selected=False)
            bpy.ops.object.select_all(action='DESELECT')
            for obj in room.all_objects:obj.select_set(True)
            bpy.context.view_layer.objects.active=bpy.data.objects['PREP_CLASSROOM_CITY_ANCHOR']
            bpy.ops.view3d.localview(frame_selected=False)
        space=area.spaces.active
        space.overlay.show_overlays=False
        space.shading.type='MATERIAL'
        space.shading.use_scene_world=False
        target=Vector((16,-60,1.6))
        space.region_3d.view_location=target
        space.region_3d.view_distance=20
        space.region_3d.view_rotation=(Vector((27,-75,9))-target).to_track_quat('Z','Y')
        space.region_3d.view_perspective='PERSP'
scene.frame_set(85)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report={'saved':bpy.data.filepath,'cityObjects':len(scene.objects),'focusedObjects':len(room.all_objects),'preview':'Material Preview in local classroom view; exit local view to inspect the whole city','frame':85,'door':'open','originalObjectsDeleted':0}
Path(bpy.data.filepath).parents[2].joinpath('reports/blender_classroom_focus_final_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
