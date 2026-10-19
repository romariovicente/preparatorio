import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['PREP_CITY']; bpy.context.window.scene=scene
if bpy.data.objects.get('PREP_DisplayBase'): raise RuntimeError('Presentation base already exists; render current scene instead')
mesh=bpy.data.meshes.new('PREP_DisplayBase'); mesh.from_pydata([(-8,-8,-.035),(78,-8,-.035),(78,50,-.035),(-8,50,-.035)],[],[(0,1,2,3)]); mesh.update()
obj=bpy.data.objects.new('PREP_DisplayBase',mesh); bpy.data.collections['PREP_Presentation'].objects.link(obj); mesh.materials.append(bpy.data.materials['MAT_PREP_Plaster'])
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(root/'reports/CITY_KIT_01_overview.png')
scene.cycles.samples=16
bpy.ops.wm.save_as_mainfile(filepath=str(root/'art/blender/PREPARATORIO_CITY_KIT_01.blend'))
bpy.ops.render.render(write_still=True)
print(scene.render.filepath)
