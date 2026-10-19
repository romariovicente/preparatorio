"""Derive a functional bus hierarchy without modifying supplied source collections."""
import bpy,json,math,hashlib,struct
from pathlib import Path
from collections import defaultdict
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'art/blender/new_delivery_20261006/VEH_Bus_BRT_20261006.blend'
OUT=ROOT/'frontend/public/assets/new-delivery/VEH_Bus_BRT_Interactive_20261009.glb'
ART=ROOT/'art/blender/VEH_Bus_BRT_Interactive_20261009.blend'
assert not OUT.exists() and not ART.exists(),'Existing derivatives must be inspected, not overwritten'
source=bpy.data.collections['PREP_DELIVERY_VEH_Bus_BRT_20261006']
scene=bpy.data.scenes.new('PREP_BRT_INTERACTIVE_20261009');bpy.context.window.scene=scene
collection=bpy.data.collections.new('PREP_BRT_INTERACTIVE_20261009');scene.collection.children.link(collection)
root=bpy.data.objects.new('Bus_BRT_Root',None);collection.objects.link(root)
root['source_collection']=source.name;root['functional_bus']=True;root['forward']='-Y Blender / +Z glTF';root['source_file']=str(SOURCE)
joint=-.36325
rear=bpy.data.objects.new('RearSection',None);collection.objects.link(rear);rear.parent=root;rear.location=(0,joint,0);rear['joint_limit_degrees']=25
wheel_parts={9:1,8:2,11:3,10:4}
door_regions=[(-7.03,-5.63),(1.76,3.20),(8.68,10.00)]
objects=[];wheels=[];doors=[];bellows=[];source_triangles=0
def bounds(points):return (Vector([min(p[i] for p in points) for i in range(3)]),Vector([max(p[i] for p in points) for i in range(3)]))
def new_part(source_obj,face_ids,name,parent,pivot=None):
    m=source_obj.data;ids=sorted({i for fi in face_ids for i in m.polygons[fi].vertices});mapping={i:j for j,i in enumerate(ids)}
    pts=[source_obj.matrix_world@m.vertices[i].co for i in ids]
    parent_offset=Vector((0,joint,0)) if parent==rear else Vector((0,0,0))
    pivot=Vector(pivot) if pivot is not None else parent_offset
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata([p-pivot for p in pts],[],[tuple(mapping[i] for i in m.polygons[fi].vertices) for fi in face_ids]);mesh.update()
    for mat in m.materials:mesh.materials.append(mat)
    loop_map=[]
    for p,fi in zip(mesh.polygons,face_ids):
        old=m.polygons[fi];p.material_index=old.material_index;p.use_smooth=old.use_smooth;loop_map.extend(old.loop_indices)
    for uv in m.uv_layers:
        layer=mesh.uv_layers.new(name=uv.name)
        for k,old_loop in enumerate(loop_map):layer.data[k].uv=uv.data[old_loop].uv
    if len(m.corner_normals)==len(m.loops):
        normal_matrix=source_obj.matrix_world.to_3x3().inverted().transposed()
        try:mesh.normals_split_custom_set([(normal_matrix@m.corner_normals[i].vector).normalized() for i in loop_map])
        except Exception:pass
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj.parent=parent;obj.location=pivot-parent_offset
    for k,v in source_obj.items():obj[k]=v
    obj['source_faces']=len(face_ids);objects.append(obj)
    return obj,pts
for src in source.objects:
    if src.type!='MESH':continue
    src.data.calc_loop_triangles();source_triangles+=len(src.data.loop_triangles)
    part=int(src['source_part'].split('_')[-1].split('.')[0]) if src.get('source_part') else -1
    groups=defaultdict(list)
    coords=[src.matrix_world@v.co for v in src.data.vertices]
    for face in src.data.polygons:
        pts=[coords[i] for i in face.vertices];center=sum(pts,Vector())/len(pts)
        if part in wheel_parts:key=('Wheel',wheel_parts[part],'L' if center.x>0 else 'R')
        elif part==7 and all(p.x>.35 for p in pts):key=('SteeringWheel',)
        else:
            key=None
            for d,(low,high) in enumerate(door_regions,1):
                if all(p.x>1.12 and low<=p.y<=high and .43<=p.z<=2.72 for p in pts):
                    key=('Door',d,'A' if center.y<(low+high)/2 else 'B');break
            if key is None:key=('Front',) if center.y<-1.2181 else ('Rear',) if center.y>.4916 else ('Bellows',)
        groups[key].append(face.index)
    for key,face_ids in groups.items():
        pts=[coords[i] for fi in face_ids for i in src.data.polygons[fi].vertices];lo,hi=bounds(pts)
        if key[0]=='Wheel':
            axle,side=key[1:];center=(lo+hi)*.5;parent=rear if center.y>joint else root
            name='Wheel_%02d_%s'%(axle,side);obj,_=new_part(src,face_ids,name,parent,center)
            radius=(hi.z-lo.z)*.5;obj['radius']=radius;obj['spin_axis']='X';obj['steering_axle']=axle==1;wheels.append({'name':name,'radius':radius,'pivot':list(center),'steering':axle==1})
        elif key[0]=='SteeringWheel':
            center=Vector((.6201,-10.49,1.62));obj,_=new_part(src,face_ids,'SteeringWheel',root,center);obj['spin_axis']='Z';obj['source_role']='Original driver steering ring and spokes from model_7.obj'
        elif key[0]=='Door':
            d,leaf=key[1:];low,high=door_regions[d-1];pivot=Vector((1.285,low if leaf=='A' else high,.44));parent=rear if pivot.y>joint else root
            name='Door_%02d_%s_Part_%02d'%(d,leaf,part)
            # One group pivot per door leaf keeps every original material piece together.
            group_name='Door_%02d_%s'%(d,leaf);hinge=bpy.data.objects.get(group_name)
            if not hinge:
                hinge=bpy.data.objects.new(group_name,None);collection.objects.link(hinge);hinge.parent=parent;hinge.location=pivot-(Vector((0,joint,0)) if parent==rear else Vector());hinge['door_leaf']=leaf;hinge['door_index']=d;doors.append({'name':group_name,'pivot':list(pivot),'axis':'Y glTF / Z Blender','open_degrees':-65 if leaf=='A' else 65})
            obj,_=new_part(src,face_ids,name,root,pivot);obj.parent=hinge;obj.location=(0,0,0)
        else:
            label=key[0];parent=rear if label=='Rear' else root
            name='BRT_%s_Part_%02d'%(label,part) if part>=0 else 'BRT_%s_%s'%(label,src.name)
            obj,_=new_part(src,face_ids,name,parent)
            if label=='Bellows':
                obj.shape_key_add(name='Basis')
                for key_name,angle in [('ArticulationLeft',math.radians(25)),('ArticulationRight',math.radians(-25))]:
                    shape=obj.shape_key_add(name=key_name)
                    for v,k in zip(obj.data.vertices,shape.data):
                        p=v.co;weight=max(0,min(1,(p.y+1.2181)/(0.4916+1.2181)))
                        rotated=Matrix.Rotation(angle*weight,3,'Z')@(p-Vector((0,joint,0)))+Vector((0,joint,0));k.co=rotated
                bellows.append(obj.name)
for o in objects:o.data.calc_loop_triangles()
derivative_triangles=sum(len(o.data.loop_triangles) for o in objects)
assert source_triangles==derivative_triangles,(source_triangles,derivative_triangles)
root['source_triangles']=source_triangles;root['derived_triangles']=derivative_triangles
bpy.ops.object.select_all(action='DESELECT')
for o in collection.objects:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format='GLB',use_selection=True,use_active_scene=True,export_yup=True,export_animations=False,export_skins=False,export_extras=True,export_cameras=False,export_lights=False)
verify=bpy.data.scenes.new('QA_BRT_REIMPORT_20261009');bpy.context.window.scene=verify;bpy.ops.import_scene.gltf(filepath=str(OUT))
actual=[o for o in verify.objects if o.type=='MESH']
assert all(math.isfinite(f) for o in actual for v in o.data.vertices for f in v.co)
assert all(o.data.materials for o in actual)
for o in actual:o.data.calc_loop_triangles()
assert sum(len(o.data.loop_triangles) for o in actual)==derivative_triangles
assert len([o for o in verify.objects if o.name.startswith('Wheel_')])==8
bpy.context.window.scene=scene
# The standalone derivative contains source collections for provenance, functional hierarchy, and a fresh GLB reimport validation scene.
bpy.ops.wm.save_as_mainfile(filepath=str(ART))
record={'status':'validated','asset':'VEH_Bus_BRT_Interactive_20261009','url':'/assets/new-delivery/'+OUT.name,'blend':str(ART),'collection':collection.name,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'sourceTriangles':source_triangles,'derivedTriangles':derivative_triangles,'sourceMaterialsPreserved':True,'finite':True,'wheels':wheels,'doors':doors,'steering':'SteeringWheel','rear':'RearSection','jointBlender':[0,joint,0],'jointGLTF':[0,0,-joint],'bellows':bellows,'morphNames':['ArticulationLeft','ArticulationRight'],'morphLimitDegrees':25,'source':'Original prepared Caio Millennium BRT meshes; supplied materials were provisional because MTL was absent'}
(ROOT/'reports/bus_brt_interactive_20261009.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in record.items() if k not in ['wheels','doors','bellows']}))
