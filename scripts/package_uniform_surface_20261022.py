"""Remap exported surface indices and reuse the already validated Web PNG bytes."""
import copy,hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WHITE=bool(globals().get('PREP_WHITE_UNIFORM',False))
FINAL=bool(globals().get('PREP_SURFACE_FINAL',False))
SOURCE=ROOT/('art/characters/CHR_Remy_White_Uniform_Surface_20261022_v4.glb' if FINAL else ('art/characters/CHR_Remy_White_Uniform_Surface_20261022_v3.glb' if WHITE else 'art/characters/CHR_Remy_Uniform_Surface_20261022_v2.glb'))
PREVIOUS=ROOT/'frontend/public/assets/characters/runtime/CHR_Remy_Senac_Uniform_Web_20261021.glb'
FULL=ROOT/('art/characters/CHR_Remy_White_Uniform_Surface_Source_20261022.glb' if WHITE else 'art/characters/CHR_Remy_Uniform_Surface_Source_20261022.glb')
WEB=ROOT/('art/characters/CHR_Remy_White_Uniform_Surface_Web_20261022.glb' if WHITE else 'art/characters/CHR_Remy_Uniform_Surface_Web_20261022.glb')
if FINAL:
    FULL=FULL.parent/'white_uniform_final'/FULL.name
    WEB=WEB.parent/'white_uniform_final'/WEB.name
    FULL.parent.mkdir(exist_ok=True)
def read(path):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+length]),raw[28+length:],hashlib.sha256(raw).hexdigest()
def write(path,doc,binary):
    encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode()
    encoded+=b' '*((-len(encoded))%4);binary+=b'\0'*((-len(binary))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+
                     struct.pack('<II',len(encoded),0x4e4f534a)+encoded+
                     struct.pack('<II',len(binary),0x004e4942)+binary)
def payload(doc,binary,index):
    view=doc['bufferViews'][index];offset=view.get('byteOffset',0)
    return binary[offset:offset+view['byteLength']]
def accessor(doc,binary,index):
    a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
    fmt={5126:'f',5125:'I',5123:'H',5121:'B',5122:'h',5120:'b'}[a['componentType']]
    components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    size=struct.calcsize('<'+fmt*components);stride=v.get('byteStride',size)
    start=v.get('byteOffset',0)+a.get('byteOffset',0)
    assert not a.get('sparse')
    return [struct.unpack_from('<'+fmt*components,binary,start+i*stride) for i in range(a['count'])]
def fields(doc,binary,node):
    primitives=doc['meshes'][node['mesh']]['primitives'];assert len(primitives)==1
    return {key:accessor(doc,binary,value) for key,value in primitives[0]['attributes'].items() if key in ('POSITION','JOINTS_0','WEIGHTS_0')}
assert not FULL.exists() and not WEB.exists()
doc,binary,source_hash=read(SOURCE)
nodes={node['name']:node for node in doc['nodes']}
mapped=[]
for node in doc['nodes']:
    extras=node.get('extras',{})
    if not extras.get('uniformSurfaceAttachment'):continue
    cloth=nodes[extras['uniformSurfaceMesh']]
    target=fields(doc,binary,cloth);decal=fields(doc,binary,node)
    lookup={}
    for i,point in enumerate(target['POSITION']):lookup.setdefault(tuple(round(x,6) for x in point),[]).append(i)
    indices=[]
    for i,point in enumerate(decal['POSITION']):
        candidates=lookup.get(tuple(round(x,6) for x in point),[])
        if not candidates:
            candidates=[j for j,p in enumerate(target['POSITION']) if max(abs(a-b) for a,b in zip(point,p))<2e-6]
        exact=[j for j in candidates if target['JOINTS_0'][j]==decal['JOINTS_0'][i]
               and max(abs(a-b) for a,b in zip(target['WEIGHTS_0'][j],decal['WEIGHTS_0'][i]))<1e-6]
        assert exact,(node['name'],i,point,candidates)
        indices.append(exact[0])
    extras['uniformSurfaceVertexMap']=indices
    mapped.append({'name':node['name'],'surface':cloth['name'],'vertices':len(indices)})
assert len(mapped)==6
write(FULL,doc,binary)
old_doc,old_binary,old_hash=read(PREVIOUS)
old_images={image['name']:payload(old_doc,old_binary,image['bufferView']) for image in old_doc['images']}
new_doc=copy.deepcopy(doc)
replacement={image['bufferView']:old_images[image['name']] for image in doc['images']}
rebuilt=bytearray();unchanged=[]
for index,view in enumerate(new_doc['bufferViews']):
    original=payload(doc,binary,index);part=replacement.get(index,original)
    rebuilt.extend(b'\0'*((-len(rebuilt))%4))
    view['byteOffset']=len(rebuilt);view['byteLength']=len(part);rebuilt.extend(part)
    if index not in replacement:unchanged.append((index,hashlib.sha256(original).hexdigest()))
new_doc['buffers'][0]['byteLength']=len(rebuilt)
write(WEB,new_doc,bytes(rebuilt))
verify_doc,verify_bin,web_hash=read(WEB)
assert all(hashlib.sha256(payload(verify_doc,verify_bin,index)).hexdigest()==expected for index,expected in unchanged)
assert verify_doc['animations']==doc['animations'] and verify_doc['skins']==doc['skins']
assert all(payload(verify_doc,verify_bin,image['bufferView'])==old_images[image['name']] for image in verify_doc['images'])
assert read(SOURCE)[2]==source_hash and read(PREVIOUS)[2]==old_hash
report={'source':str(SOURCE),'sourceSha256':source_hash,'full':str(FULL),'fullSha256':read(FULL)[2],'whiteScrubs':WHITE,
        'web':str(WEB),'webSha256':web_hash,'webBytes':WEB.stat().st_size,'fullBytes':FULL.stat().st_size,
        'mappedPatches':mapped,'nonImageViewsByteIdentical':len(unchanged),'reusedImageCount':len(replacement),
        'imageSourceSha256':old_hash,'imageBytesUnchangedFromApprovedWeb':True,'animationsAndSkinsUnchangedFromBlenderExport':True}
(ROOT/('reports/costumes/REMY_WHITE_UNIFORM_SURFACE_PACKAGE_20261022.json' if WHITE else 'reports/costumes/REMY_UNIFORM_SURFACE_PACKAGE_20261022.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
