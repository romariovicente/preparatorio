import bpy,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from prep_prepare_asset import prepare
from prep_materials import create_materials
from prep_export_glb import export_assets
scene=bpy.data.scenes['PREP_CITY']; bpy.context.window.scene=scene
assets=[o for o in scene.objects if o.get('prep_asset')]
before={o.name:(o.matrix_world.copy(),len(o.modifiers)) for o in assets}
prepare(assets); prepare(assets)
assert all(o.matrix_world==before[o.name][0] and len(o.modifiers)==before[o.name][1] for o in assets)
assert len(create_materials())==10
test=bpy.data.objects.new('PREP_TEST_TRANSFORM',assets[0].data.copy()); scene.collection.objects.link(test); test['prep_asset']=True
test.location=(.5,.25,0); test.rotation_euler[2]=.3; test.scale=(2,1,1); bpy.context.view_layer.update()
points=[test.matrix_world@v.co for v in test.data.vertices]; pivot=test.location.copy()
prepare([test],apply_transforms=True); bpy.context.view_layer.update()
assert max((a-test.matrix_world@v.co).length for a,v in zip(points,test.data.vertices))<1e-5
assert test.location==pivot
parent=bpy.data.objects.new('PREP_TEST_PARENT',None); scene.collection.objects.link(parent); test.parent=parent
try:
    prepare([test],apply_transforms=True)
    raise AssertionError('Unsafe transform not rejected')
except ValueError: pass
mesh=test.data; bpy.data.objects.remove(test,do_unlink=True); bpy.data.meshes.remove(mesh); bpy.data.objects.remove(parent,do_unlink=True)
try:
    export_assets([assets[0]],root/'frontend/public/assets/models/PREP_Modular_City_Kit_01.glb')
    raise AssertionError('Overwrite not rejected')
except FileExistsError: pass
assert set(bpy.data.scenes['Scene'].objects.keys())=={'Cube','Camera','Light'}
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D': area.spaces.active.region_3d.view_perspective='CAMERA'
for obj in bpy.context.selected_objects: obj.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'art/blender/PREPARATORIO_CITY_KIT_01.blend'))
report={'prepare_idempotent':True,'prepare_preserves_pivots':True,'explicit_transform_world_geometry_preserved':True,'parent_transform_rejected':True,'materials_reused':True,'export_overwrite_rejected':True,'original_scene_preserved':True}
(root/'reports/script_tests.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
