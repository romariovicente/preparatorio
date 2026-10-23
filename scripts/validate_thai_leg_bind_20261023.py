"""Independent GLB check for the PARTIAL student binding stage, not locomotion."""
import bpy,json,hashlib,math,struct
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,kdtree
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_REFIT_V2_20261023.blend'
BLEND=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_LEG_BIND_REIMPORT_V2_20261023.blend'
REPORT=ROOT/'reports/CHARACTER_THAI_LEG_BIND_REIMPORT_V2_20261023.json'
FOLDER=ROOT/'reports/thai_refit_20261023'
assert Path(bpy.data.filepath).resolve()==WORK.resolve() and not bpy.data.is_dirty
stage=json.loads((ROOT/'reports/CHARACTER_THAI_LEG_BIND_V2_20261023.json').read_text())
GLB=Path(stage['glb']['path']);SOURCE=ROOT/'frontend/public/assets/characters/CHR_thai_student_v9_Actions_v3.glb'
assert hashlib.sha256(GLB.read_bytes()).hexdigest()==stage['glb']['sha256']
def glb_images(path):
    raw=path.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);binary=raw[28+size:]
    hashes=[]
    for image in doc.get('images',[]):
        view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0)
        hashes.append(hashlib.sha256(binary[start:start+view['byteLength']]).hexdigest())
    return doc,hashes
original,old_images=glb_images(SOURCE);doc,new_images=glb_images(GLB)
original_scene=bpy.data.scenes['PREP_CHARACTER_THAI_REFIT_STAGING_20261023']
old_mesh=next(o for o in original_scene.objects if o.type=='MESH')
before={s.name:set(o.name for o in s.objects) for s in bpy.data.scenes}
scene=bpy.data.scenes.new('VALIDATE_THAI_PARTIAL_LEG_BIND_20261023');bpy.context.window.scene=scene
with bpy.context.temp_override(scene=scene,view_layer=scene.view_layers[0],collection=scene.collection):bpy.ops.import_scene.gltf(filepath=str(GLB))
helpers=[]
for name,names in before.items():
    for obj in list(bpy.data.scenes[name].objects):
        if obj.name not in names:
            assert obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa'))
            helpers.append(obj.name)
            for col in list(obj.users_collection):col.objects.unlink(obj)
    assert set(o.name for o in bpy.data.scenes[name].objects)==names
for obj in list(scene.objects):
    if obj.type=='MESH' and obj.name.startswith(('Icosphere','Esfera icosa')) and not any(m.type=='ARMATURE' for m in obj.modifiers):
        helpers.append(obj.name)
        for col in list(obj.users_collection):col.objects.unlink(obj)
arms=[o for o in scene.objects if o.type=='ARMATURE'];meshes=[o for o in scene.objects if o.type=='MESH']
assert len(arms)==len(meshes)==1
arm=arms[0];mesh=meshes[0];bpy.context.view_layer.update()
def points():
    ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=ev.to_mesh()
    values=np.empty(len(data.vertices)*3,dtype=np.float32);data.vertices.foreach_get('co',values)
    matrix=np.array(ev.matrix_world);result=values.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3];ev.to_mesh_clear();return result
rest=points();source=np.load(FOLDER/'initial_mesh.npz')['vertices']
tree=kdtree.KDTree(len(source))
for i,p in enumerate(source):tree.insert(Vector(p),i)
tree.balance();errors=[tree.find(Vector(p))[2] for p in rest]
reverse=kdtree.KDTree(len(rest))
for i,p in enumerate(rest):reverse.insert(Vector(p),i)
reverse.balance();errors.extend(reverse.find(Vector(p))[2] for p in source)
max_geometry_error=max(errors)
def surface_uv(obj):
    # Texture-coordinate associations per position (allow duplicated UV seams).
    result={}
    for loop in obj.data.loops:
        key=tuple(round(v,5) for v in obj.data.vertices[loop.vertex_index].co)
        uv=tuple(round(v,5) for v in obj.data.uv_layers.active.data[loop.index].uv)
        result.setdefault(key,set()).add(uv)
    return result
uv_before=surface_uv(old_mesh);uv_after=surface_uv(mesh)
# Rounding boundaries can differ by float precision. Verify each imported loop
# against the actual source position/UV using a spatial nearest-neighbor set.
uv_lookup={}
for loop in old_mesh.data.loops:uv_lookup.setdefault(loop.vertex_index,set()).add(tuple(old_mesh.data.uv_layers.active.data[loop.index].uv))
uv_error=0
for loop in mesh.data.loops:
    p=mesh.data.vertices[loop.vertex_index].co;uv=mesh.data.uv_layers.active.data[loop.index].uv
    candidates=tree.find_range(p,2e-5)
    uv_error=max(uv_error,min(math.dist(uv,old_uv) for _p,index,_dist in candidates for old_uv in uv_lookup.get(index,())))
weights=[{mesh.vertex_groups[g.group].name:float(g.weight) for g in v.groups} for v in mesh.data.vertices]
max_influences=max(map(len,weights));sum_error=max(abs(sum(w.values())-1) for w in weights)
soles={side:np.flatnonzero((rest[:,0]*sign>0)&(rest[:,2]<.1)) for side,sign in [('L',1),('R',-1)]}
probe=[]
for side in ['L','R']:
    for degrees in [-10,10]:
        bone=arm.pose.bones[side+'_shin'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((1,0,0),math.radians(degrees));bpy.context.view_layer.update()
        posed=points();ids=soles[side]
        upper_error=float(np.max(np.linalg.norm(posed[rest[:,2]>1.05]-rest[rest[:,2]>1.05],axis=1)))
        rigidity=float(np.max(np.abs(np.linalg.norm(posed[ids]-posed[ids[0]],axis=1)-np.linalg.norm(rest[ids]-rest[ids[0]],axis=1))))
        assert np.isfinite(posed).all() and upper_error<1e-5 and rigidity<1e-5
        probe.append({'side':side,'degrees':degrees,'upperBodyMaxDisplacement':upper_error,'soleMaxDistanceError':rigidity})
        bone.matrix_basis.identity();bpy.context.view_layer.update()
checks={'oneCharacterMesh':len(meshes)==1,'oneArmature20Bones':len(arm.data.bones)==20,
 'noUnvalidatedAnimationExported':not doc.get('animations'),'fullWeightCoverage':all(weights),
 'maxFourInfluences':max_influences<=4,'normalizedWeights':sum_error<2e-6,
 'originalVertexCount':len(rest)==len(source)==31726,'originalTriangles':sum(len(p.vertices)-2 for p in mesh.data.polygons)==44999,
 'restSurfacePreserved':max_geometry_error<1e-5,'textureCoordinatesPreserved':uv_error<1e-5,
 'embeddedImagesByteIdentical':old_images==new_images,'bothSolesIdentified':all(len(ids)>100 for ids in soles.values()),
 'fourLegArticulationProbes':len(probe)==4,'sourceRuntimePreserved':hashlib.sha256(SOURCE.read_bytes()).hexdigest()==stage['sourceRuntimeSha256']}
assert all(checks.values()),checks
scene.world=bpy.data.worlds.new('Thai_Bind_Review_World');scene.world.color=(.055,.055,.055)
for location,energy,size in [((2.4,-3.4,3),850,3),((-2.4,-1,2),500,2.5),((0,2.5,2.8),650,2)]:
    data=bpy.data.lights.new('Thai_Bind_Light','AREA');data.energy=energy;data.size=size
    light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=location;light.rotation_euler=(Vector((0,0,.85))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Thai_Bind_Camera');cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=560;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';cam.data.type='ORTHO';cam.data.ortho_scale=1.95;scene.view_settings.view_transform='AgX'
renders=[]
for sample in ['rest','R_knee_10','L_knee_10']:
    if sample!='rest':
        bone=arm.pose.bones[sample[0]+'_shin'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((1,0,0),math.radians(10));bpy.context.view_layer.update()
    for name,offset in [('front',(0,-5,0)),('side',(5,0,0))]:
        center=Vector((0,0,.85));cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        path=FOLDER/(f'reimport_v2_{sample}_{name}.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);renders.append(str(path))
    for bone in arm.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
scene['PREP_role']='validated-partial-leg-binding-not-playable-not-neutral'
scene['PREP_pending']='Full torso/arms/head refit, neutralization and real Idle/Walk.'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
report={'status':'partial-binding-reimport-passed-awaiting-visual-review','checks':checks,'maxRestGeometryError':max_geometry_error,'maxUVError':uv_error,'weightSumError':sum_error,
 'geometricSoles':{s:{'vertices':len(ids),'minZ':float(rest[ids,2].min())} for s,ids in soles.items()},
 'articulationProbes':probe,'imagesSha256':new_images,'source':stage['glb'],'library':str(BLEND),'scene':scene.name,'renders':renders,
 'importHelpersUnlinked':helpers,'nativeWalkValidated':False,'neutralPoseValidated':False,'runtimeChanged':False,'masterChanged':False,'visualReview':'pending'}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','checks','maxRestGeometryError','maxUVError','geometricSoles']}))
