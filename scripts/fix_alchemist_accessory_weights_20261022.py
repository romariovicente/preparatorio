"""Pin the belt-mounted flask components to hips, preserving geometry and UV."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['PREP_CHARACTER_ALCHEMIST_RETARGET_20261022']
bpy.context.window.scene=scene
obj=next(o for o in scene.objects if o.type=='MESH' and 'Body' in o.name)
mesh=obj.data;co=np.array([obj.matrix_world@v.co for v in mesh.vertices])
green=np.load(ROOT/'work/alchemist_green_seeds_20261022.npz')['indices']
parent=np.arange(len(co))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
def union(a,b):
    a,b=find(a),find(b)
    if a!=b:parent[b]=a
for edge in mesh.edges:union(*edge.vertices)
weld={}
for i,p in enumerate(co):
    key=tuple(np.round(p,6))
    if key in weld:union(i,weld[key])
    else:weld[key]=i
labels=np.array([find(i) for i in range(len(co))])
components=set(labels[green].tolist())
selected=np.flatnonzero(np.isin(labels,list(components)))
# Components containing actual green flask UV pixels are bounded to the belt;
# abort rather than accidentally bind a whole arm/head to the pelvis.
assert len(selected)>len(green) and len(selected)<12000
low,high=co[selected].min(axis=0),co[selected].max(axis=0)
assert low[2]>.72 and high[2]<1.2 and high[0]<.30 and low[0]>-.12,(low,high)
for group in obj.vertex_groups:group.remove(selected.tolist())
obj.vertex_groups['hips'].add(selected.tolist(),1.0,'REPLACE')
report={'method':'Connected/welded components containing green flask texture pixels, rigidly bound to hips; no vertex or UV changes',
 'greenSeeds':len(green),'componentCount':len(components),'rigidVertexCount':len(selected),'rigidVertexIndices':selected.tolist(),
 'min':low.tolist(),'max':high.tolist(),'runtimeChanged':False}
(ROOT/'reports/CHARACTER_ALCHEMIST_ACCESSORY_WEIGHTS_20261022.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print(json.dumps({k:v for k,v in report.items() if k!='rigidVertexIndices'}))
