"""Apply staged anatomical rest joints/weights, preserving the original surface."""
import bpy,hashlib,json
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_UPPER_REFIT_20261023.blend'
FOLDER=ROOT/'reports/thai_upper_refit_20261023'
OUT=ROOT/'art/character_refit_20261023/CHR_Thai_Upper_Bind_Review_20261023.glb'
REPORT=ROOT/'reports/CHARACTER_THAI_UPPER_BIND_20261023.json'
assert Path(bpy.data.filepath).resolve()==WORK.resolve()
assert not OUT.exists() and not REPORT.exists()
scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023'];bpy.context.window.scene=scene
arm=next(o for o in scene.objects if o.type=='ARMATURE');mesh=next(o for o in scene.objects if o.type=='MESH')
base=np.load(FOLDER/'baseline_mesh.npz');prepared=np.load(FOLDER/'prepared_weights.npz');plan=json.loads((FOLDER/'prepared_weights.json').read_text())
coords=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
assert np.array_equal(coords,base['vertices']) and np.array_equal(coords,prepared['vertices'])
group_names=[g.name for g in mesh.vertex_groups];assert group_names==prepared['group_names'].tolist()==base['group_names'].tolist()
assert len(arm.data.bones)==20
def points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh();values=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',values)
    mat=np.array(ev.matrix_world);result=values.reshape(-1,3)@mat[:3,:3].T+mat[:3,3];ev.to_mesh_clear();return result
def uv_hash():
    values=np.empty(len(mesh.data.loops)*2,dtype=np.float32);mesh.data.uv_layers.active.data.foreach_get('uv',values);return hashlib.sha256(values.tobytes()).hexdigest()
old_uv=uv_hash();old_data={b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in arm.data.bones}
for b in arm.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update();before=points()
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for bone in arm.data.edit_bones:bone.use_connect=False
for n,row in plan['boneDefinitions'].items():
    bone=arm.data.edit_bones[n];bone.head=row['head'];bone.tail=row['tail']
    # Keep each pre-existing roll while fitting a new anatomical direction.
    # The pose solver transfers directions explicitly rather than assuming axes.
bpy.ops.object.mode_set(mode='OBJECT')
W=prepared['weights'];changed=np.flatnonzero(coords[:,2]>.66)
# Batch removals avoid invalidating the mesh/dependency graph once per old
# influence. Group additions retain the original float weights exactly.
# Grouping exactly equal weights also handles rigid head regions efficiently.
# No quantization or BMesh roundtrip is used, preserving UV/custom normals.
changed_list=changed.astype(int).tolist()
for group in mesh.vertex_groups:group.remove(changed_list)
for j,group in enumerate(mesh.vertex_groups):
    indices=changed[W[changed,j]>1e-8]
    if not len(indices):continue
    values=W[indices,j]
    unique,inverse=np.unique(values,return_inverse=True)
    for k,value in enumerate(unique):group.add(indices[inverse==k].astype(int).tolist(),float(value),'REPLACE')
bpy.context.view_layer.update();after=points();rest_error=float(np.max(np.linalg.norm(after-before,axis=1)))
assert rest_error<1e-5 and uv_hash()==old_uv
lower_preserved=0;max_error=0;max_influences=0
for v in mesh.data.vertices:
    w={g.group:float(g.weight) for g in v.groups};max_influences=max(max_influences,len(w));max_error=max(max_error,abs(sum(w.values())-1))
    if coords[v.index,2]<=.66:
        assert all(float(base['weights'][v.index,j])==w.get(j,0) for j in range(len(group_names)));lower_preserved+=1
assert lower_preserved==6283 and max_influences<=4 and max_error<2e-6
for side in ['L','R']:
    for part in ['shin','foot']:
        n=side+'_'+part
        assert np.linalg.norm(np.array(arm.data.bones[n].head_local)-np.array(old_data[n]['head']))<1e-6
        assert np.linalg.norm(np.array(arm.data.bones[n].tail_local)-np.array(old_data[n]['tail']))<1e-6
scene['PREP_role']='upper-and-lower-binding-review-not-neutral-not-runtime'
scene['PREP_pending']='Independent probes and visual review; lower hair/shoulders, neutral pose, individual fingers, real Idle/Walk.'
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_image_format='AUTO',export_cameras=False,export_lights=False,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK),compress=True)
report={'status':'upper-bind-staged-awaiting-independent-probes-and-visual-review','library':str(WORK),
 'glb':{'path':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'bytes':OUT.stat().st_size},
 'sourceLibraryCheckpoint':'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_UPPER_REFIT_20261023.blend',
 'oldRestBones':old_data,'newRestBones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in arm.data.bones},
 'maxRestSurfaceDisplacement':rest_error,'uvPreserved':uv_hash()==old_uv,'sourceVertices':len(coords),'maxWeightSumError':max_error,'maxInfluences':max_influences,
 'lowerWeightVerticesPreserved':lower_preserved,'lowerShinFootJointsPreserved':True,'upperWeightVerticesRevised':len(changed),
 'headHandMaskSource':'reports/thai_upper_refit_20261023/head_hand_graph_masks.npz','nativeWalkValidated':False,'neutralPoseValidated':False,
 'runtimeChanged':False,'masterChanged':False,'visualReview':'pending','limits':plan['limits']}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ['status','glb','maxRestSurfaceDisplacement','maxWeightSumError','lowerWeightVerticesPreserved']}))
