"""Stabilize feather and halo components without editing geometry or UVs."""
from pathlib import Path
from datetime import datetime,timezone
import bpy,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
WORKING=ROOT/'art/blender/libraries/PREP_CHARACTER_SERAPH_RETARGET_20261023.blend'
assert Path(bpy.data.filepath).resolve()==WORKING.resolve()
scene=bpy.data.scenes['PREP_CHARACTER_SERAPH_RETARGET_20261023']
bpy.context.window.scene=scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
obj=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers))
mesh=obj.data
co=np.array([obj.matrix_world@v.co for v in mesh.vertices]);count=len(co)
raw=np.empty(count*3,dtype=np.float32);mesh.vertices.foreach_get('co',raw)
geometry_hash=hashlib.sha256(raw.tobytes()).hexdigest()
parent=np.arange(count)
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return int(i)
def union(a,b):
    a,b=find(a),find(b)
    if a!=b:parent[b]=a
for edge in mesh.edges:union(*edge.vertices)
weld={}
for i,p in enumerate(co):
    key=tuple(np.round(p,6))
    if key in weld:union(i,weld[key])
    else:weld[key]=i
labels=np.array([find(i) for i in range(count)])
groups={g.name:g.index for g in obj.vertex_groups}
weights=np.zeros((count,2),dtype=np.float32)
for v in mesh.vertices:
    for g in v.groups:
        for side,name in enumerate(('L_wing','R_wing')):
            if g.group==groups[name]:weights[v.index,side]=g.weight
selected={}
for index,(side,sign) in enumerate((('L',1),('R',-1))):
    seed=(co[:,0]*sign>.31)&(-co[:,1]<.06)&(weights[:,index]>.10)
    indices=np.flatnonzero(np.isin(labels,np.unique(labels[seed])))
    assert 13000<len(indices)<15000,(side,len(indices))
    assert (co[indices,0]*sign).min()>.20
    selected[side+'_wing']=indices
halo_seed=(co[:,2]>1.60)&(np.abs(co[:,0])<.14)
halo=np.flatnonzero(np.isin(labels,np.unique(labels[halo_seed])))
assert 200<len(halo)<500 and np.abs(co[halo,0]).max()<.15
selected['head']=halo
assert not(set(selected['L_wing'])&set(selected['R_wing']))
assert not(set(halo)&set(selected['L_wing'])) and not(set(halo)&set(selected['R_wing']))
report={'createdAt':datetime.now(timezone.utc).isoformat(),'geometryHash':geometry_hash,'vertices':count,
 'method':'Conservative wing-weight/spatial seeds expanded over welded connected components; separate halo-height seeds. Each accepted component bound rigidly to its wing bone or head; wings inherit chest, not arms.',
 'regions':[],'runtimeChanged':False,'masterChanged':False}
for name,indices in selected.items():
    ids=indices.tolist()
    prior={g.name:0.0 for g in obj.vertex_groups}
    for i in indices:
        for g in mesh.vertices[i].groups:prior[obj.vertex_groups[g.group].name]+=g.weight
    for group in obj.vertex_groups:group.remove(ids)
    obj.vertex_groups[name].add(ids,1.0,'REPLACE')
    report['regions'].append({'bone':name,'count':len(ids),'min':co[indices].min(axis=0).tolist(),
      'max':co[indices].max(axis=0).tolist(),'previousEquivalentInfluences':prior,'indices':ids})
mesh.vertices.foreach_get('co',raw)
assert hashlib.sha256(raw.tobytes()).hexdigest()==geometry_hash
report['geometryUnchanged']=True
(ROOT/'reports/CHARACTER_SERAPH_WEIGHT_FIX_20261023.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(WORKING),compress=True)
print(json.dumps({'regions':[{k:v for k,v in r.items() if k not in ('indices','previousEquivalentInfluences')} for r in report['regions']],'geometryUnchanged':True}))
