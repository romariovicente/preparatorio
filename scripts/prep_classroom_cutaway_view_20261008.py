import bpy,json
from pathlib import Path
from mathutils import Vector
room=bpy.data.collections['ARAP_16_CLASSROOM_20261008']
hidden=[]
for obj in room.all_objects:
    if obj.name.startswith(('BLD_Classroom_RearWallLeft','BLD_Classroom_RearWallRight','BLD_Classroom_DoorLintel','MOD_CeilingSide_')):
        obj.hide_set(True);hidden.append(obj.name)
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            target=Vector((16,-60,1.2));view=area.spaces.active.region_3d
            view.view_location=target;view.view_distance=18
            view.view_rotation=Vector((9,13,11)).to_track_quat('Z','Y')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report={'saved':bpy.data.filepath,'inspectionCutawayOnly':hidden,'allRenderGeometryPreserved':True,'sceneObjects':len(bpy.context.scene.objects)}
Path(bpy.data.filepath).parents[2].joinpath('reports/blender_inspection_view_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
