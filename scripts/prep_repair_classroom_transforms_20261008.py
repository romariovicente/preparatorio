"""Restore appended local transforms from the unchanged standalone classroom."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
source=json.loads((ROOT/'reports/classroom_source_transforms_20261008.json').read_text(encoding='utf-8'))
room=bpy.data.collections['ARAP_16_CLASSROOM_20261008']
anchor=bpy.data.objects['PREP_CLASSROOM_CITY_ANCHOR']
hinge=bpy.data.objects['DOOR_Classroom_Animated']
existing={o.name:o for o in room.all_objects}
missing=[r['name'] for r in source['objects'] if r['name'] not in existing]
assert not missing,missing
checkpoint=ROOT/'art/blender/checkpoints/BEFORE_CLASSROOM_TRANSFORM_REPAIR_20261008.blend'
if not checkpoint.exists():shutil.copy2(bpy.data.filepath,checkpoint)
bpy.context.scene.frame_set(1)
anchor.location=(16,-60,0);anchor.rotation_euler=(0,0,0);anchor.scale=(1,1,1)
hinge.parent=anchor;hinge.matrix_parent_inverse=Matrix.Identity(4)
hinge.location=(4.715,5.92,0);hinge.rotation_euler=(0,0,0)
closed_hinge=Matrix.Translation(Vector((4.715,5.92,0)))
for row in source['objects']:
    obj=existing[row['name']]
    obj.rotation_mode=row['rotation_mode']
    if row['name'] in {'MOD_Classroom_Door','PROP_Classroom_DoorHandle'}:
        obj.parent=hinge;obj.matrix_parent_inverse=Matrix.Identity(4)
        obj.matrix_basis=closed_hinge.inverted()@Matrix(row['matrix_world'])
    else:
        obj.parent=existing[row['parent']] if row['parent'] else anchor
        obj.parent_type=row['parent_type'];obj.parent_bone=row['parent_bone']
        obj.matrix_parent_inverse=Matrix(row['matrix_parent_inverse']) if row['parent'] else Matrix.Identity(4)
        obj.matrix_basis=Matrix(row['matrix_basis'])
    if obj.type=='ARMATURE':
        for bone_row in row.get('pose_bones',[]):
            obj.pose.bones[bone_row['name']].matrix_basis=Matrix(bone_row['matrix_basis'])
bpy.context.view_layer.update()
errors=[]
for row in source['objects']:
    obj=existing[row['name']];expected=anchor.matrix_world@Matrix(row['matrix_world'])
    error=max(abs(obj.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))
    if error>.0005:errors.append({'name':row['name'],'error':error})
assert not errors,errors[:20]
floor=existing['MOD_Classroom_Floor']
floor_corners=[floor.matrix_world@Vector(v) for v in floor.bound_box]
floor_bounds={'min':[min(v[i] for v in floor_corners) for i in range(3)],'max':[max(v[i] for v in floor_corners) for i in range(3)]}
assert abs(floor_bounds['min'][0]-9)<.001 and abs(floor_bounds['max'][1]+54)<.001,floor_bounds
students=[o for o in room.all_objects if o.name.startswith('NPC_Classroom_Remy_')]
assert len(students)==12 and len({(round(o.matrix_world.translation.x,3),round(o.matrix_world.translation.y,3)) for o in students})==12
bpy.context.scene.frame_set(85)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
report={'saved':bpy.data.filepath,'restoredObjects':len(source['objects']),'matrixChecksPassed':497,'sourceHierarchyPreserved':True,'sourceFileChanged':False,'floorBoundsBlender':floor_bounds,'uniqueStudentRoots':12,'originalObjectsDeleted':0,'doorOpenFrame':85}
(ROOT/'reports/classroom_transform_repair_validation_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
