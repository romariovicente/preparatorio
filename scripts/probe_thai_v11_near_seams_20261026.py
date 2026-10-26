"""Read-only saved GLB reimport: test the eight scan seams at standing/head15."""
import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Matrix
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_GARMENT_V11_PROBES_20261026.blend'
OUT=ROOT/'reports/thai_garment_v11_validation_20261026/near_seams_reimport_head15.json'
assert Path(bpy.data.filepath).resolve()==INPUT.resolve() and not OUT.exists()
digest=hashlib.sha256(INPUT.read_bytes()).hexdigest()
scene=bpy.data.scenes['VALIDATE_THAI_GARMENT_BIND_V11_20261026'];bpy.context.window.scene=scene
mesh=next(o for o in scene.objects if o.type=='MESH');arm=next(o for o in scene.objects if o.type=='ARMATURE')
subset=json.loads((ROOT/'reports/thai_garment_v11_validation_20261026/white_seam_subset.json').read_text())['trustedPairs']
assert len(subset)==8 and len(mesh.data.vertices)==31726
names=[g.name for g in mesh.vertex_groups];W=np.zeros((len(mesh.data.vertices),len(names)),dtype=np.float32)
for v in mesh.data.vertices:
    for g in v.groups:W[v.index,g.group]=g.weight
def points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    a=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',a)
    world=np.array(ev.matrix_world);ev.to_mesh_clear()
    return a.reshape(-1,3)@world[:3,:3].T+world[:3,3]
def depth(b):return 0 if b.parent is None else depth(b.parent)+1
def apply(matrices):
    for bone in sorted(arm.pose.bones,key=depth):
        kw={'parent_matrix':matrices[bone.parent.name],'parent_matrix_local':bone.parent.bone.matrix_local} if bone.parent else {}
        bone.matrix_basis=bone.bone.convert_local_to_pose(matrices[bone.name],bone.bone.matrix_local,invert=True,**kw)
    bpy.context.view_layer.update()
original={b.name:b.matrix.copy() for b in arm.pose.bones};standing=points()
turn={name:matrix.copy() for name,matrix in original.items()}
rotation=Quaternion((0,0,1),math.radians(15))@turn['head'].to_quaternion()
turn['head']=Matrix.LocRotScale(turn['head'].translation,rotation,turn['head'].to_scale())
apply(turn);turned=points();apply(original);restored=points()
restore_error=float(np.linalg.norm(restored-standing,axis=1).max());assert restore_error<1e-5
pairs=[]
for pair in subset:
    a=np.array(pair['edgeA']);b=np.array(pair['edgeBEndpointMatched'])
    same=np.array_equal(W[a],W[b]);assert same
    sd=np.linalg.norm(standing[a]-standing[b],axis=1);td=np.linalg.norm(turned[a]-turned[b],axis=1)
    assert max(sd.max(),td.max())<.001
    pairs.append({'edgeA':a.tolist(),'edgeBEndpointMatched':b.tolist(),'identicalExportedWeights':same,
      'standingEndpointGapsMeters':sd.tolist(),'head15EndpointGapsMeters':td.tolist()})
report={'status':'eight-reviewed-near-seams-pass-standing-and-head15-reimport',
 'library':str(INPUT),'librarySha256':digest,'pairs':pairs,
 'maximumStandingGapMeters':max(max(p['standingEndpointGapsMeters']) for p in pairs),
 'maximumHead15GapMeters':max(max(p['head15EndpointGapsMeters']) for p in pairs),
 'restoredPoseMaxError':restore_error,'thresholdMeters':.001,
 'sourceSaved':False,'sourceHashUnchanged':hashlib.sha256(INPUT.read_bytes()).hexdigest()==digest,
 'nativeWalkValidated':False,'neutralPoseValidated':False,'runtimeChanged':False}
assert report['sourceHashUnchanged']
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='pairs'}))
