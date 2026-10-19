"""Make new single-scene GLBs from generated static assets, preserving originals.

Blender's use_selection flag applied to every scene in its multi-scene master.
This revision keeps the intended first scene and removes unreachable nodes,
skins, meshes, materials and buffer views. It preserves exact vertex attributes
and node transforms, and never edits the source files.
"""
from pathlib import Path
import json,struct,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'frontend/public/assets/cyber'

def read(path):
 raw=path.read_bytes();assert struct.unpack_from('<III',raw)==(0x46546c67,2,len(raw))
 offset=12;doc=None;binary=None
 while offset<len(raw):
  size,kind=struct.unpack_from('<II',raw,offset);chunk=raw[offset+8:offset+8+size]
  if kind==0x4e4f534a:doc=json.loads(chunk)
  elif kind==0x004e4942:binary=chunk
  offset+=8+size
 assert doc and binary is not None
 return doc,binary

def extract(source,target):
 assert not target.exists(),'Preserve existing output: '+str(target)
 doc,binary=read(source);selected=copy.deepcopy(doc['scenes'][doc.get('scene',0)])
 reachable=set()
 def visit(idx):
  if idx in reachable:return
  reachable.add(idx)
  for child in doc['nodes'][idx].get('children',[]):visit(child)
 for idx in selected.get('nodes',[]):visit(idx)
 nodes=sorted(reachable);node_map={old:i for i,old in enumerate(nodes)}
 assert not any('skin' in doc['nodes'][i] for i in nodes),'Selected static scene unexpectedly contains a skin'
 assert not doc.get('animations'),'This extraction is for generated static assets only'
 meshes=sorted({doc['nodes'][i]['mesh'] for i in nodes if 'mesh' in doc['nodes'][i]})
 mesh_map={old:i for i,old in enumerate(meshes)}
 materials=set();accessors=set()
 for idx in meshes:
  for p in doc['meshes'][idx]['primitives']:
   assert 'KHR_draco_mesh_compression' not in p.get('extensions',{})
   accessors.update(p['attributes'].values())
   if 'indices' in p:accessors.add(p['indices'])
   for target_attrs in p.get('targets',[]):accessors.update(target_attrs.values())
   if 'material' in p:materials.add(p['material'])
 materials=sorted(materials);material_map={old:i for i,old in enumerate(materials)}
 texture_ids=set()
 def scan_textures(obj):
  if isinstance(obj,dict):
   if 'index' in obj:texture_ids.add(obj['index'])
   for value in obj.values():scan_textures(value)
  elif isinstance(obj,list):
   for value in obj:scan_textures(value)
 for idx in materials:scan_textures(doc['materials'][idx])
 textures=sorted(texture_ids);texture_map={old:i for i,old in enumerate(textures)}
 image_ids=set();sampler_ids=set()
 for idx in textures:
  t=doc['textures'][idx]
  if 'source' in t:image_ids.add(t['source'])
  if 'sampler' in t:sampler_ids.add(t['sampler'])
  for ext in t.get('extensions',{}).values():
   if 'source' in ext:image_ids.add(ext['source'])
 images=sorted(image_ids);image_map={old:i for i,old in enumerate(images)}
 samplers=sorted(sampler_ids);sampler_map={old:i for i,old in enumerate(samplers)}
 accessors=sorted(accessors);accessor_map={old:i for i,old in enumerate(accessors)}
 views=set()
 for idx in accessors:
  a=doc['accessors'][idx]
  if 'bufferView' in a:views.add(a['bufferView'])
  if 'sparse' in a:views.update([a['sparse']['indices']['bufferView'],a['sparse']['values']['bufferView']])
 for idx in images:
  image=doc['images'][idx];assert 'uri' not in image
  views.add(image['bufferView'])
 views=sorted(views);view_map={old:i for i,old in enumerate(views)}
 out={key:copy.deepcopy(doc[key]) for key in ['asset','extensionsUsed','extensionsRequired'] if key in doc}
 out['scene']=0;selected['nodes']=[node_map[i] for i in selected.get('nodes',[])];out['scenes']=[selected]
 out['nodes']=[]
 for idx in nodes:
  n=copy.deepcopy(doc['nodes'][idx]);assert 'camera' not in n and 'KHR_lights_punctual' not in n.get('extensions',{})
  if 'children' in n:n['children']=[node_map[i] for i in n['children']]
  if 'mesh' in n:n['mesh']=mesh_map[n['mesh']]
  out['nodes'].append(n)
 out['meshes']=[]
 for idx in meshes:
  m=copy.deepcopy(doc['meshes'][idx])
  for p in m['primitives']:
   p['attributes']={key:accessor_map[i] for key,i in p['attributes'].items()}
   if 'indices' in p:p['indices']=accessor_map[p['indices']]
   if 'material' in p:p['material']=material_map[p['material']]
   if 'targets' in p:p['targets']=[{key:accessor_map[i] for key,i in a.items()} for a in p['targets']]
  out['meshes'].append(m)
 def remap_textures(obj):
  if isinstance(obj,dict):
   if 'index' in obj:obj['index']=texture_map[obj['index']]
   for value in obj.values():remap_textures(value)
  elif isinstance(obj,list):
   for value in obj:remap_textures(value)
 if materials:
  out['materials']=[copy.deepcopy(doc['materials'][i]) for i in materials]
  for m in out['materials']:remap_textures(m)
 if textures:
  out['textures']=[copy.deepcopy(doc['textures'][i]) for i in textures]
  for t in out['textures']:
   if 'source' in t:t['source']=image_map[t['source']]
   if 'sampler' in t:t['sampler']=sampler_map[t['sampler']]
   for ext in t.get('extensions',{}).values():
    if 'source' in ext:ext['source']=image_map[ext['source']]
 if images:
  out['images']=[copy.deepcopy(doc['images'][i]) for i in images]
  for im in out['images']:im['bufferView']=view_map[im['bufferView']]
 if samplers:out['samplers']=[copy.deepcopy(doc['samplers'][i]) for i in samplers]
 out['accessors']=[]
 for idx in accessors:
  a=copy.deepcopy(doc['accessors'][idx])
  if 'bufferView' in a:a['bufferView']=view_map[a['bufferView']]
  if 'sparse' in a:
   for kind in ['indices','values']:a['sparse'][kind]['bufferView']=view_map[a['sparse'][kind]['bufferView']]
  out['accessors'].append(a)
 out['bufferViews']=[];packed=bytearray()
 for idx in views:
  view=copy.deepcopy(doc['bufferViews'][idx]);assert view.get('buffer',0)==0
  old_start=view.get('byteOffset',0);chunk=binary[old_start:old_start+view['byteLength']]
  assert len(chunk)==view['byteLength']
  packed.extend(b'\0'*((-len(packed))%4));view['buffer']=0;view['byteOffset']=len(packed);packed.extend(chunk)
  out['bufferViews'].append(view)
 out['buffers']=[{'byteLength':len(packed)}]
 payload=json.dumps(out,ensure_ascii=False,separators=(',',':')).encode('utf-8');payload+=b' '*((-len(payload))%4)
 packed.extend(b'\0'*((-len(packed))%4))
 raw=struct.pack('<III',0x46546c67,2,12+8+len(payload)+8+len(packed))+struct.pack('<II',len(payload),0x4e4f534a)+payload+struct.pack('<II',len(packed),0x004e4942)+packed
 with target.open('xb') as f:f.write(raw)
 # Verify exact accessor byte payloads rather than claiming regeneration.
 for old,new in view_map.items():
  a=doc['bufferViews'][old];b=out['bufferViews'][new]
  assert binary[a.get('byteOffset',0):a.get('byteOffset',0)+a['byteLength']]==packed[b['byteOffset']:b['byteOffset']+b['byteLength']]
 return {'source':str(source),'target':str(target),'sourceBytes':source.stat().st_size,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'selectedScene':selected.get('name'),'nodes':len(nodes),'meshes':len(meshes),'skins':0,'scenes':1,'accessorPayloadsPreserved':True,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest()}

if __name__=='__main__':
 from prep_validate_cyber_glbs import validate
 manifest_path=ROOT/'frontend/src/config/cyberWorldManifest.json'
 manifest=json.loads(manifest_path.read_text(encoding='utf-8'));records=[];new_urls={}
 paths=[PUBLIC/Path(manifest['sceneUrl']).name]
 paths += [PUBLIC/Path(a['url']).name for a in manifest['props']+manifest['biomes']]
 for source in paths:
  target=PUBLIC/('ENV_Arapiraca_RealMaterials_v3_20261005.glb' if source.name.startswith('ENV_Arapiraca') else source.stem.replace('_20261005','_scene_20261005')+'.glb')
  record=extract(source,target);record['validation']=validate(target);records.append(record)
  new_urls['/assets/cyber/'+source.name]='/assets/cyber/'+target.name
 # Publish only assets actually extracted and validated.
 manifest['sceneUrl']=new_urls[manifest['sceneUrl']]
 for item in manifest['props']+manifest['biomes']:
  item['url']=new_urls[item['url']]
  rec=next(r for r in records if r['target'].endswith(Path(item['url']).name))
  item['bytes']=rec['bytes'];item['sha256']=rec['sha256']
 manifest['singleSceneRevision']=True
 manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 report={'count':len(records),'allSingleScene':True,'allStatic':True,'sourcesPreserved':True,'records':records}
 (ROOT/'reports/cyber_glb_single_scene_revision_20261005.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'count':len(records),'allSingleScene':True,'allStatic':True,'sourcesPreserved':True,'sceneUrl':manifest['sceneUrl']}))
