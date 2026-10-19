"""Validate actual generated GLB byte ranges, finite data and scene topology."""
from pathlib import Path
import json,struct,hashlib,math,io
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'frontend/public/assets/cyber'
TYPES={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
WIDTH={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT2':4,'MAT3':9,'MAT4':16}

def validate(path):
 raw=path.read_bytes();magic,version,total=struct.unpack_from('<III',raw)
 assert magic==0x46546c67 and version==2 and total==len(raw),path
 offset=12;doc=None;binary=b''
 while offset<len(raw):
  size,kind=struct.unpack_from('<II',raw,offset);assert size%4==0 and offset+8+size<=len(raw)
  chunk=raw[offset+8:offset+8+size]
  if kind==0x4e4f534a:doc=json.loads(chunk)
  elif kind==0x004e4942:binary=chunk
  offset+=8+size
 assert offset==len(raw) and doc and doc['asset']['version']=='2.0'
 for b in doc.get('buffers',[]):assert 'uri' not in b and b['byteLength']<=len(binary)
 views=doc.get('bufferViews',[])
 for view in views:
  assert view.get('buffer',0)==0
  assert 0<=view.get('byteOffset',0)<=len(binary)
  assert view.get('byteOffset',0)+view['byteLength']<=len(binary)
 arrays=[]
 for a in doc.get('accessors',[]):
  assert a['count']>=0 and a['componentType'] in TYPES and a['type'] in WIDTH
  dtype=np.dtype(TYPES[a['componentType']]);width=WIDTH[a['type']]
  if 'bufferView' not in a:
   arr=np.zeros((a['count'],width),dtype=dtype)
  else:
   view=views[a['bufferView']];stride=view.get('byteStride',dtype.itemsize*width)
   local=a.get('byteOffset',0);end=local+max(0,a['count']-1)*stride+(dtype.itemsize*width if a['count'] else 0)
   assert stride>=dtype.itemsize*width and end<=view['byteLength']
   arr=np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=view.get('byteOffset',0)+local,strides=(stride,dtype.itemsize)).copy()
  assert 'sparse' not in a,'Generated static assets should not require sparse data'
  assert np.isfinite(arr).all()
  arrays.append(arr)
 tris=vertices=0
 for mesh in doc.get('meshes',[]):
  for p in mesh['primitives']:
   pos=arrays[p['attributes']['POSITION']];vertices+=len(pos);assert pos.shape[1]==3
   assert p.get('mode',4)==4
   for semantic,idx in p['attributes'].items():assert len(arrays[idx])==len(pos),(semantic,path)
   if 'indices' in p:
    idx=arrays[p['indices']];assert len(idx)%3==0
    assert not len(idx) or (idx.min()>=0 and idx.max()<len(pos))
    tris+=len(idx)//3
   else:assert len(pos)%3==0;tris+=len(pos)//3
 for i,node in enumerate(doc.get('nodes',[])):
  assert not node.get('name','').startswith('PRIVATE_')
  for key in ['translation','rotation','scale','matrix']:
   if key in node:assert all(math.isfinite(v) for v in node[key])
  for child in node.get('children',[]):assert 0<=child<len(doc['nodes']) and child!=i
  if 'mesh' in node:assert 0<=node['mesh']<len(doc['meshes'])
 embedded=[]
 for image in doc.get('images',[]):
  assert 'uri' not in image
  view=views[image['bufferView']];start=view.get('byteOffset',0)
  with Image.open(io.BytesIO(binary[start:start+view['byteLength']])) as im:
   im.verify();embedded.append({'size':list(im.size),'format':im.format})
 return {'file':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'meshes':len(doc.get('meshes',[])),'nodes':len(doc.get('nodes',[])),'materials':len(doc.get('materials',[])),'vertices':vertices,'triangles':tris,'embeddedImages':embedded,'accessorsFinite':True,'indexRangesValid':True,'privateNodesAbsent':True}

if __name__=='__main__':
 files=sorted(p for p in PUBLIC.glob('*.glb') if p.name.startswith(('PROP_','ENV_')))
 report={'files':[validate(p) for p in files],'scope':'Generated city environments, biomes and props; original supplied models and character rigs untouched.'}
 report['count']=len(report['files'])
 target=ROOT/'reports/cyber_glb_structural_validation_20261005.json'
 target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'count':report['count'],'allValid':True,'report':str(target)}))
