"""Create a separate editable Blender asset gallery without replacing the island file."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
records=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
assert len(records)==20,'Finish validation before building the gallery'
dest=ROOT/'art/blender/PREPARATORIO_ACERVO_01.blend'
assert not dest.exists(),'Inspect existing gallery before replacing it'
previous=bpy.context.window.scene
scene=bpy.data.scenes.new('PREP_ACERVO_01');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.world=bpy.data.worlds.new('PREP_ACERVO_WORLD');scene.world.color=(.25,.25,.25)
scene['credits']='See THIRD_PARTY_ASSETS.md; original metadata copied to each root'
scene['notice']='Gallery scales are display scales; building models are not georeferenced.'
for i,r in enumerate(records):
    existing=set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/r['url'].lstrip('/')))
    imported={o for o in set(scene.objects)-existing if not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)}
    collection=bpy.data.collections.new(r['id']);scene.collection.children.link(collection)
    for obj in imported:
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj)
    root=bpy.data.objects.new(r['id']+'_ROOT',None);collection.objects.link(root)
    points=[o.matrix_world@Vector(c) for o in imported if o.type=='MESH' for c in o.bound_box]
    low=Vector([min(p[k] for p in points) for k in range(3)])
    high=Vector([max(p[k] for p in points) for k in range(3)])
    center=(low+high)/2;center.z=low.z
    scale=(6 if r['category']=='Edifícios' else 3)/max(high-low)
    for obj in imported:
        if obj.parent not in imported:
            world=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=world
    x=(i%5)*8;y=(i//5)*9
    root.matrix_world=Matrix.Translation((x,y,0))@Matrix.Scale(scale,4)@Matrix.Translation(-center)
    root['source_sha256']=r['sourceSha256'];root['source']=r['sourceRelative'];root['credits']=json.dumps(r['credits'],ensure_ascii=False)
    root['static_pose']=not r['animated']
    curve=bpy.data.curves.new(r['id']+'_Label','FONT');curve.body=r['name'];curve.size=.32;curve.align_x='CENTER'
    label=bpy.data.objects.new(r['id']+'_Label',curve);collection.objects.link(label);label.location=(x,y-2.2,.02)
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
center=Vector((16,13,0));bpy.ops.object.camera_add(location=(42,-43,55))
camera=bpy.context.object;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=53;scene.camera=camera
bpy.ops.object.light_add(type='AREA',location=(16,-10,30));light=bpy.context.object;light.data.energy=18000;light.data.size=40
light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/'reports/SUPPLIED_ASSETS_overview.png')
bpy.ops.render.render(write_still=True)
# The standalone file contains only this scene and its dependencies, not the user's island/kit.
bpy.data.libraries.write(str(dest),{scene},fake_user=True,compress=True)
with bpy.data.libraries.load(str(dest),link=False) as (available,target):
    assert 'PREP_ACERVO_01' in available.scenes
(ROOT/'reports/supplied_gallery.json').write_text(json.dumps({'file':str(dest.relative_to(ROOT)),'scene':scene.name,'assetCollections':len(records),'meshes':sum(o.type=='MESH' for o in scene.objects),'bytes':dest.stat().st_size,'libraryReadValidated':True},indent=2),encoding='utf-8')
bpy.context.window.scene=previous
print('Saved independent gallery',dest)
