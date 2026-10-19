"""Reimport both delivery files, compare triangle counts/bounds, and create editable POI markers."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['PREP_ISLAND'];records=json.loads((ROOT/'reports/island_optimization.json').read_text())
checks=[]
for record in records:
    validation=bpy.data.scenes.new('VALIDATE_'+record['name'])
    bpy.context.window.scene=validation
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public/assets/models'/(record['name']+'.glb')))
    meshes=[o for o in validation.objects if o.type=='MESH'];assert len(meshes)==1
    obj=meshes[0];bpy.context.view_layer.update()
    tris=sum(len(p.vertices)-2 for p in obj.data.polygons)
    assert tris==record['triangles'],(tris,record['triangles'])
    error=max(abs(a-b) for a,b in zip(obj.dimensions,record['dimensions_blender_m']))
    assert error<.002,(obj.name,error)
    assert len(obj.data.uv_layers)==1
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    checks.append({'variant':record['name'],'triangles':tris,'reimported_meshes':1,'dimensions_error_m':error,'uv_present':True,'material_count':len(obj.data.materials)})
bpy.context.window.scene=scene
assert not bpy.data.collections.get('PREP_ISLAND_POI')
pois=bpy.data.collections.new('PREP_ISLAND_POI');scene.collection.children.link(pois)
mesh=bpy.data.objects['MAP_Preparatorio_Island_Web']
landmarks=json.loads((ROOT/'reports/island_landmarks.json').read_text(encoding='utf-8'))
for point in landmarks:
    x,z=point['position'];hit,loc,normal,index=mesh.ray_cast(Vector((x,-z,100)),Vector((0,0,-1)))
    marker=bpy.data.objects.new('POI_'+point['id'],None);pois.objects.link(marker)
    marker.empty_display_type='SPHERE';marker.empty_display_size=2
    marker.location=(x,-z,(loc.z if hit else 12)+5)
    marker['label']=point['name'];marker['category']=point['category'];marker['approximate_game_landmark']=True
(ROOT/'reports/island_validation.json').write_text(json.dumps({'checks':checks,'landmarks':len(landmarks),'source_unchanged':'SHA256 equality in island_source.json'},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/PREPARATORIO_ISLAND.blend'),compress=True)
print(json.dumps(checks))
