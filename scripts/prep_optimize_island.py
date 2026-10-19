"""Derive web/mobile meshes and textures; source GLB remains archived unmodified."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['PREP_ISLAND_SOURCE']; bpy.context.window.scene=scene
source=bpy.data.objects['MAP_Island_Source']; out=ROOT/'frontend/public/assets/models'
records=[]; generated=[]
for name,ratio,texture_size in [('MAP_Preparatorio_Island_Web',.06,2048),('MAP_Preparatorio_Island_Mobile',.018,1024)]:
    path=out/(name+'.glb'); assert not path.exists(),str(path)
    duplicate=source.copy(); duplicate.data=source.data.copy(); duplicate.name=name; scene.collection.objects.link(duplicate)
    modifier=duplicate.modifiers.new('PREP_Web_Decimate','DECIMATE'); modifier.ratio=ratio; modifier.use_collapse_triangulate=True
    dg=bpy.context.evaluated_depsgraph_get(); ev=duplicate.evaluated_get(dg)
    reduced=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
    old=duplicate.data; duplicate.modifiers.clear(); duplicate.data=reduced; bpy.data.meshes.remove(old)
    duplicate['prep_map']=True; duplicate['variant']='web' if texture_size==2048 else 'mobile'
    for index,mat in enumerate(list(duplicate.data.materials)):
        m=mat.copy(); m.name='MAT_'+name; duplicate.data.materials[index]=m
        for node in m.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:
                image=node.image.copy(); image.name=name+'_'+node.image.name
                image.scale(texture_size,texture_size); image.pack(); node.image=image
    for o in bpy.context.selected_objects:o.select_set(False)
    duplicate.select_set(True); bpy.context.view_layer.objects.active=duplicate
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_image_format='JPEG',export_jpeg_quality=88)
    tris=sum(len(p.vertices)-2 for p in reduced.polygons)
    records.append({'name':name,'triangles':tris,'vertices':len(reduced.vertices),'texture_size':texture_size,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dimensions_blender_m':list(duplicate.dimensions)})
    generated.append(duplicate)
# Original import is superseded by the derived meshes, while the exact original remains in art/source.
source_mesh=source.data; bpy.data.objects.remove(source,do_unlink=True); bpy.data.meshes.remove(source_mesh)
scene.name='PREP_ISLAND'; generated[1].hide_render=True; generated[1].hide_set(True)
scene['source_archive']='art/source/Meshy_Island_Original.glb'
scene['game_scale_note']='400 m maximum extent; design scale, not real cartographic distance'
with bpy.data.libraries.load(str(ROOT/'art/blender/PREPARATORIO_CITY_KIT_01.blend'),link=False) as (available,target):
    target.scenes=[n for n in available.scenes if n=='PREP_CITY']
scene.render.filepath=str(ROOT/'reports/island_optimized_preview.png'); scene.cycles.samples=16
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
path=ROOT/'art/blender/PREPARATORIO_ISLAND.blend'; assert not path.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
(ROOT/'reports/island_optimization.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
# Top view supports explicit landmark placement without assuming the reference image is georeferenced.
cam=scene.camera; original=cam.matrix_world.copy(); cam.location=(0,0,500); cam.rotation_euler=(0,0,0); cam.data.ortho_scale=440
scene.render.resolution_x=1000; scene.render.resolution_y=1100; scene.render.filepath=str(ROOT/'reports/island_top_view.png')
bpy.ops.render.render(write_still=True)
cam.matrix_world=original; cam.data.ortho_scale=470; scene.render.resolution_x=1100; scene.render.resolution_y=900
scene.render.filepath=str(ROOT/'reports/island_optimized_preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print(json.dumps(records))
