"""Create a standalone organized overview of validated delivery collections.

This never opens or changes the live Blender project. Each component library keeps
its original source scene separately; the overview contains game derivatives only.
"""
from pathlib import Path
import bpy,json
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
records=json.loads((ROOT/'frontend/src/config/newDeliveryAssets.json').read_text(encoding='utf-8'))
dest=ROOT/'art/blender/PREPARATORIO_NEW_DELIVERY_20261006.blend'
assert not dest.exists(),f'Inspect existing overview before replacing: {dest}'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.name='PREP_NEW_DELIVERY_20261006';scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
positions={'BLD_Bus_Terminal_20261006':(0,0,0),'VEH_Bus_City_20261006':(33,-7,0),'VEH_Bus_BRT_20261006':(33,18,0),'MOD_Bus_Stop_20261006':(33,-21,0),'CHAR_Student_XVIII_20261006':(0,-26,0),'EDU_Anatomy_XRay_20261006':(-4,-26,0)}
for record in records:
 assert record['status']=='validated'
 with bpy.data.libraries.load(record['blend'],link=False) as (available,loaded):
  assert record['collection'] in available.collections
  loaded.collections=[record['collection']]
 collection=loaded.collections[0];scene.collection.children.link(collection)
 offset=Matrix.Translation(Vector(positions[record['id']]))
 for obj in collection.all_objects:
  if obj.parent is None:obj.matrix_world=offset@obj.matrix_world
 collection['asset_id']=record['id'];collection['source_status']=record['licenseStatus'];collection['delivered_glb']=record['url']
 scene['delivery_'+record['id']]=record['sha256']
data=bpy.data.cameras.new('CAM_Delivery_Overview');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
camera.location=(85,-90,82);camera.rotation_euler=(Vector((8,0,1))-camera.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=105;scene.camera=camera
scene.world=bpy.data.worlds.new('WORLD_Delivery_Overview');scene.world.color=(.15,.2,.25)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL';area.spaces.active.clip_end=2000
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
print(json.dumps({'saved':str(dest),'collections':[r['collection'] for r in records],'objects':len(scene.objects),'liveBlenderChanged':False},ensure_ascii=False))
