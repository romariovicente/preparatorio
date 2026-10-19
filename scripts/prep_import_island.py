"""Import supplied map into a separate scene; preserve current session and kit files."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
assert not bpy.data.scenes.get('PREP_ISLAND_SOURCE'), 'Already imported: inspect current scene'
checkpoint=ROOT/'art/blender/checkpoints/SESSION_BEFORE_ISLAND.blend'
assert not checkpoint.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),copy=True)
scene=bpy.data.scenes.new('PREP_ISLAND_SOURCE'); bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/source/Meshy_Island_Original.glb'))
meshes=[o for o in scene.objects if o.type=='MESH']; assert len(meshes)==1
obj=meshes[0]; obj.name='MAP_Island_Source'; obj.data.name='MESH_Island_Source'
bpy.context.view_layer.update()
points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
low=[min(p[i] for p in points) for i in range(3)]; high=[max(p[i] for p in points) for i in range(3)]
scale=400/max(high[0]-low[0],high[1]-low[1])
# Bake only the new independent import, preserving all prior assets and hierarchies.
assert not obj.parent and not obj.children
matrix=obj.matrix_world.copy()
for v in obj.data.vertices:
    p=matrix@v.co
    v.co=((p.x-(low[0]+high[0])/2)*scale,(p.y-(low[1]+high[1])/2)*scale,(p.z-low[2])*scale)
obj.matrix_world.identity(); obj.data.update(); bpy.context.view_layer.update()
obj['source_sha256_report']='reports/island_source.json'; obj['game_scale_m']=400
obj['map_role']='Generated island relief reference; not traversable interiors'
world=bpy.data.worlds.new('PREP_Island_World'); world.use_nodes=True
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.8; scene.world=world
camera=bpy.data.cameras.new('PREP_Island_Camera'); cam=bpy.data.objects.new('PREP_Island_Camera',camera); scene.collection.objects.link(cam)
cam.location=(0,-330,430); cam.rotation_euler=(Vector((0,0,10))-cam.location).to_track_quat('-Z','Y').to_euler(); camera.type='ORTHO'; camera.ortho_scale=470; scene.camera=cam
light=bpy.data.lights.new('PREP_Island_Sun','SUN'); lo=bpy.data.objects.new('PREP_Island_Sun',light); scene.collection.objects.link(lo); lo.rotation_euler=(.2,-.4,-.3); light.energy=2
scene.render.engine='CYCLES'; scene.cycles.samples=8; scene.render.resolution_x=1100; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'; scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(ROOT/'reports/island_source_preview.png')
images=[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE' and i.size[0]>0]
report={'source_vertices':len(obj.data.vertices),'source_triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'dimensions_blender_m':list(obj.dimensions),'scale_factor':scale,'images':images}
(ROOT/'reports/island_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print(json.dumps(report))
