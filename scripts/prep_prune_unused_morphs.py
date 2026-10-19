from pathlib import Path
import json,struct,hashlib,shutil
root=Path('outputs/preparatorio');p=root/'frontend/public/assets/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre.glb'
raw=p.read_bytes();jl=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+jl]);bstart=20+jl+8;binary=raw[bstart:]
import numpy as np
binary=bytearray(binary)
backup=root/'art/source/preserved_full_morphs';backup.mkdir(parents=True,exist_ok=True)
if not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
def floats(index):
 a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];assert a['componentType']==5126 and 'sparse' not in a
 return np.frombuffer(binary,dtype='<f4',count=a['count'],offset=v.get('byteOffset',0)+a.get('byteOffset',0)).copy()
kept={}
for mi,m in enumerate(d['meshes']):
 count=len(m['primitives'][0].get('targets',[]))
 if not count:continue
 use=np.array(m.get('weights',[0]*count))!=0
 for node in d['nodes']:
  if node.get('mesh')==mi and 'weights' in node:use|=np.array(node['weights'])!=0
 for anim in d['animations']:
  for channel in anim['channels']:
   if channel['target']['path']=='weights' and d['nodes'][channel['target']['node']].get('mesh')==mi:
    values=floats(anim['samplers'][channel['sampler']]['output']).reshape(-1,count);use|=np.any(values!=0,axis=0)
 indices=np.flatnonzero(use).tolist();kept[mi]=(count,indices)
 for q in m['primitives']:
  q['targets']=[q['targets'][i] for i in indices]
  if not indices:q.pop('targets')
 if 'weights' in m:m['weights']=[m['weights'][i] for i in indices]
 if 'extras' in m and 'targetNames' in m['extras']:m['extras']['targetNames']=[m['extras']['targetNames'][i] for i in indices]
for node in d['nodes']:
 if node.get('mesh') in kept and 'weights' in node:node['weights']=[node['weights'][i] for i in kept[node['mesh']][1]]
for anim in d['animations']:
 channels=[]
 for channel in anim['channels']:
  if channel['target']['path']!='weights':channels.append(channel);continue
  mi=d['nodes'][channel['target']['node']]['mesh'];count,indices=kept[mi]
  if not indices:continue
  sampler=anim['samplers'][channel['sampler']].copy();values=floats(sampler['output']).reshape(-1,count)[:,indices].astype('<f4').flatten()
  while len(binary)%4:binary.append(0)
  view=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':values.nbytes});binary.extend(values.tobytes())
  sampler['output']=len(d['accessors']);d['accessors'].append({'bufferView':view,'componentType':5126,'count':len(values),'type':'SCALAR'})
  channel['sampler']=len(anim['samplers']);anim['samplers'].append(sampler);channels.append(channel)
 anim['channels']=channels
 active=sorted({c['sampler'] for c in channels});mapping={old:i for i,old in enumerate(active)}
 anim['samplers']=[anim['samplers'][i] for i in active]
 for c in channels:c['sampler']=mapping[c['sampler']]
print('Kept morph columns',sum(len(v[1]) for v in kept.values()),'of',sum(v[0] for v in kept.values()))
used=set()
for m in d['meshes']:
 for q in m['primitives']:
  used.update(q['attributes'].values())
  for t in q.get('targets',[]):used.update(t.values())
  if 'indices' in q:used.add(q['indices'])
for a in d['animations']:
 for s in a['samplers']:used.update([s['input'],s['output']])
for s in d['skins']:
 if 'inverseBindMatrices' in s:used.add(s['inverseBindMatrices'])
indices=sorted(used);amap={old:i for i,old in enumerate(indices)}
for m in d['meshes']:
 for q in m['primitives']:
  q['attributes']={k:amap[v] for k,v in q['attributes'].items()}
  if 'targets' in q:q['targets']=[{k:amap[v] for k,v in t.items()} for t in q['targets']]
  if 'indices' in q:q['indices']=amap[q['indices']]
for a in d['animations']:
 for s in a['samplers']:s['input']=amap[s['input']];s['output']=amap[s['output']]
for s in d['skins']:
 if 'inverseBindMatrices' in s:s['inverseBindMatrices']=amap[s['inverseBindMatrices']]
d['accessors']=[d['accessors'][i] for i in indices];views=set()
for a in d['accessors']:
 if 'bufferView' in a:views.add(a['bufferView'])
 if 'sparse' in a:views.update(a['sparse'][k]['bufferView'] for k in ['indices','values'])
for image in d.get('images',[]):
 if 'bufferView' in image:views.add(image['bufferView'])
viewids=sorted(views);vmap={old:i for i,old in enumerate(viewids)};packed=bytearray();newviews=[]
for i in viewids:
 v=d['bufferViews'][i].copy();offset=v.get('byteOffset',0);chunk=binary[offset:offset+v['byteLength']]
 while len(packed)%4:packed.append(0)
 v['byteOffset']=len(packed);packed.extend(chunk);newviews.append(v)
for a in d['accessors']:
 if 'bufferView' in a:a['bufferView']=vmap[a['bufferView']]
 if 'sparse' in a:
  for k in ['indices','values']:a['sparse'][k]['bufferView']=vmap[a['sparse'][k]['bufferView']]
for image in d.get('images',[]):
 if 'bufferView' in image:image['bufferView']=vmap[image['bufferView']]
d['bufferViews']=newviews;d['buffers']=[{'byteLength':len(packed)}]
while len(packed)%4:packed.append(0)
j=json.dumps(d,separators=(',',':')).encode();j+=b' '*((-len(j))%4)
result=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(packed))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(packed),0x004e4942)+packed
new=p.with_name(p.stem+'_BodyRig.glb');new.write_bytes(result)
report=root/'reports/supplied/SUP_character_cyberpunk_free_3d_by_oscar_cre.json';r=json.loads(report.read_text(encoding='utf-8'));r.update(status='needs_reimport',url='/assets/supplied/'+new.name,bytes=len(result),sha256=hashlib.sha256(result).hexdigest(),modifications=r['modifications']+' Removed only morph targets unused by both default weights and every animation sample from runtime derivative; full morph GLB preserved in art/source/preserved_full_morphs. Active facial and skeletal animation retained.');report.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('Body rig',len(result),'from',len(raw))
