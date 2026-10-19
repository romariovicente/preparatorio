"""Reimport generated city/prop GLBs into isolated temporary validation scenes.

Only new validation datablocks are removed; existing scene assets are preserved.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
original=bpy.context.scene
manifest=json.loads((ROOT/'frontend/src/config/cyberWorldManifest.json').read_text(encoding='utf-8'))
urls=[manifest['sceneUrl']]+[a['url'] for a in manifest['props']+manifest['biomes']]
files=sorted({ROOT/'frontend/public'/url.lstrip('/') for url in urls})
records=[]
groups=['meshes','curves','armatures','materials','images','actions','cameras','lights','collections','scenes','worlds']
for path in files:
 before={key:set(getattr(bpy.data,key)) for key in groups}
 test=bpy.data.scenes.new('VALIDATE_CYBER_'+path.stem);bpy.context.window.scene=test
 try:
  bpy.ops.import_scene.gltf(filepath=str(path))
  objs=list(test.objects);meshes=[o for o in objs if o.type=='MESH']
  assert meshes and all(not o.name.startswith('PRIVATE_') for o in objs)
  vertices=triangles=0;points=[]
  for o in meshes:
   assert all(all(math.isfinite(x) for x in v.co) for v in o.data.vertices)
   o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles);vertices+=len(o.data.vertices)
   points += [o.matrix_world@Vector(p) for p in o.bound_box]
  low=[min(p[k] for p in points) for k in range(3)];high=[max(p[k] for p in points) for k in range(3)]
  assert all(math.isfinite(x) for x in low+high)
  assert not any(o.type=='ARMATURE' for o in objs),'These generated files are static props/environments'
  rec={'file':str(path),'objects':len(objs),'meshes':len(meshes),'vertices':vertices,'triangles':triangles,'boundsBlenderMeters':{'min':low,'max':high},'materials':len({m for o in meshes for m in o.data.materials if m}),'finiteVertices':True,'privateNodesAbsent':True,'reimported':True}
  records.append(rec)
 finally:
  bpy.context.window.scene=original
  # Bulk removal avoids repeatedly rebuilding dependencies for thousands of
  # isolated imported objects. Every ID is new relative to the per-file snapshot.
  # This never purges old orphaned source data or removes original scene assets.
  imported=set(test.objects)|{test}
  for key in groups:imported.update(set(getattr(bpy.data,key))-before[key])
  bpy.data.batch_remove(ids=list(imported))
  progress={'completed':len(records),'total':len(files),'lastFile':str(path),'status':'running','files':records}
  (ROOT/'reports/cyber_glb_reimport_progress_20261005.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
report={'count':len(records),'blenderVersion':bpy.app.version_string,'files':records,'originalSceneRestored':bpy.context.scene.name,'sourceScenesPreserved':len(bpy.data.scenes),'scope':'All 22 published Oct5 city/biome/prop GLBs from current manifest; historical exports and character rigs untouched.'}
target=ROOT/'reports/cyber_glb_reimport_validation_20261005.json'
target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'count':len(records),'allReimported':True,'report':str(target),'scene':bpy.context.scene.name}))
