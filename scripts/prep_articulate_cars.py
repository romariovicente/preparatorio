"""Derive two articulated real cars in an independent Blender process.

The supplied files are hash-checked and never rewritten. Atlas doors, windows
and wheels use the authored component hierarchy. SLS wheels/windows use actual
disconnected geometry and material islands; its connected body requires a
bounded door-panel adaptation, explicitly recorded as approximate.
"""
from pathlib import Path
import bpy,json,math,hashlib,struct
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
CATALOG=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
BLEND=ROOT/'art/blender/PREPARATORIO_CARS_INTERACTIVE_20261005.blend'
REPORT=ROOT/'reports/cars_interactive_validation_20261005.json'
SPECS=[('SUP_2010_mercedes_sls_amg','VEH_SLS_Interactive_20261005',1.260,0),
       ('SUP_volkswagen_atlas_teramont_cross_sport_2025','VEH_Atlas_Interactive_20261005',1.733,math.pi)]

def log(message):print('CARS: '+message,flush=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ancestors(obj):
    while obj.parent:obj=obj.parent;yield obj
def bounds(objects):
    bpy.context.view_layer.update()
    pts=[o.matrix_world@Vector(p) for o in objects if o.type=='MESH' for p in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo,hi
def triangles(objects):return sum(len(p.vertices)-2 for o in objects if o.type=='MESH' for p in o.data.polygons)
def new_empty(name,parent=None,pos=(0,0,0)):
    o=bpy.data.objects.new(name,None);collection.objects.link(o);o.parent=parent;o.location=pos
    o['asset_node_name']=name
    return o

def islands(obj, per_material=False):
    """Weld only positions for topology analysis; never modify source geometry."""
    coords=[obj.matrix_world@v.co for v in obj.data.vertices]
    weld={};ids=[]
    for v in coords:
        key=tuple(round(x,6) for x in v)
        if key not in weld:weld[key]=len(weld)
        ids.append(weld[key])
    parent={}
    for p in obj.data.polygons:
        mat=p.material_index if per_material else -1
        for vi in p.vertices:parent.setdefault((mat,ids[vi]),(mat,ids[vi]))
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[b]=a
    for p in obj.data.polygons:
        mat=p.material_index if per_material else -1
        first=(mat,ids[p.vertices[0]])
        for vi in p.vertices[1:]:union(first,(mat,ids[vi]))
    components={}
    for p in obj.data.polygons:
        key=find((p.material_index if per_material else -1,ids[p.vertices[0]]))
        comp=components.setdefault(key,{'polys':[],'verts':set(),'materials':set()})
        comp['polys'].append(p.index);comp['verts'].update(p.vertices)
        comp['materials'].add(obj.data.materials[p.material_index].name)
    for comp in components.values():
        vs=[coords[i] for i in comp['verts']]
        comp['min']=Vector(tuple(min(v[i] for v in vs) for i in range(3)))
        comp['max']=Vector(tuple(max(v[i] for v in vs) for i in range(3)))
        comp['center']=(comp['min']+comp['max'])/2
    return list(components.values()),coords

def split_mesh(original, poly_indices, name, parent, pivot_global):
    """Copy an exact subset, preserving face materials, loop UVs and normals."""
    if not poly_indices:return None
    source=original.data
    polygons=[source.polygons[i] for i in poly_indices]
    old_vertices=sorted({vi for poly in polygons for vi in poly.vertices})
    remap={old:new for new,old in enumerate(old_vertices)}
    matrix=original.matrix_world
    positions=[normalize(matrix@source.vertices[i].co)-pivot_global for i in old_vertices]
    faces=[tuple(remap[vi] for vi in poly.vertices) for poly in polygons]
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(positions,[],faces);mesh.update()
    for mat in source.materials:mesh.materials.append(mat)
    for new,old in zip(mesh.polygons,polygons):
        new.material_index=old.material_index;new.use_smooth=old.use_smooth
    loop_indices=[li for p in polygons for li in p.loop_indices]
    for old_uv in source.uv_layers:
        uv=mesh.uv_layers.new(name=old_uv.name)
        for index,li in enumerate(loop_indices):uv.data[index].uv=old_uv.data[li].uv
    normal_matrix=rotation@matrix.to_3x3().inverted().transposed()
    try:
        normals=[(normal_matrix@source.corner_normals[li].vector).normalized() for li in loop_indices]
        mesh.normals_split_custom_set(normals)
    except (AttributeError,RuntimeError):pass
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj.parent=parent
    obj['source_object']=original.name
    obj['source_faces']=len(polygons)
    obj['source_materials_uv_preserved']=True
    copied_positions=[parent.matrix_world@p for p in positions]
    return obj

def extract_source_mesh(original,name,parent,pivot):
    return split_mesh(original,list(range(len(original.data.polygons))),name,parent,pivot)

def build_sls(imported):
    source=next(o for o in imported if o.type=='MESH')
    components,coords=islands(source)
    by_material,_=islands(source,True)
    labels={i:'Body' for i in range(len(source.data.polygons))}
    tire_components=[c for c in components if any(m.startswith('Tyre.') for m in c['materials'])]
    if len(tire_components)!=4:raise RuntimeError('SLS must contain exactly four isolated tire components')
    centers={}
    for comp in tire_components:
        c=comp['center'];label=('F' if c.y<0 else 'R')+('L' if c.x>0 else 'R')
        centers[label]=c
    for comp in components:
        if any(m.startswith(('Rim.','Rim_Blurred','Tyre.','Brake_Disk')) for m in comp['materials']):
            label=min(centers,key=lambda key:(comp['center']-centers[key]).length)
            # Components are kept whole; no rectangular wheel-region body cut is made.
            for index in comp['polys']:labels[index]='Wheel_'+label
    glass_components=[c for c in by_material if c['materials']=={'Glass_Windows.005'}]
    side_glass=[c for c in glass_components if c['min'].x*c['max'].x>0 and c['min'].z>.8]
    if len(side_glass)!=2:raise RuntimeError('SLS side glass must be two isolated real window islands')
    glass_trees={}
    for c in side_glass:
        side='FL' if c['center'].x>0 else 'FR'
        for index in c['polys']:labels[index]='Glass_'+side
        glass_trees[side]=BVHTree.FromPolygons(coords,[source.data.polygons[i].vertices[:] for i in c['polys']],all_triangles=True)
    # Include the actual damage overlay of the same window when present.
    for p in source.data.polygons:
        if not source.data.materials[p.material_index].name.startswith('DAMAGE_GLASS'):continue
        center=sum((coords[i] for i in p.vertices),Vector())/len(p.vertices)
        for side,tree in glass_trees.items():
            nearest=tree.find_nearest(center)
            if nearest and nearest[3]<.012:labels[p.index]='Glass_'+side;break
    door_shells={}
    for side in ('FL','FR'):
        sign=1 if side=='FL' else -1
        selected=[]
        for c in by_material:
            if c['materials']=={'INT_Carpaint.005'} and c['min'].x*c['max'].x>0 and sign*c['center'].x>0:
                selected.extend(c['polys'])
        door_shells[side]=BVHTree.FromPolygons(coords,[source.data.polygons[i].vertices[:] for i in selected],all_triangles=True)
        for index in selected:labels[index]='Door_'+side
    # The prepared SLS hull is connected; use nearby actual door inner shells
    # to adapt the exterior panels. This is not an authored factory door split.
    for p in source.data.polygons:
        if labels[p.index]!='Body':continue
        mat=source.data.materials[p.material_index].name
        if mat.startswith(('Glass','DAMAGE_GLASS','Tyre','Rim','Brake')):continue
        center=sum((coords[i] for i in p.vertices),Vector())/len(p.vertices)
        if not (-.36<center.y<.98 and .30<center.z<1.30 and abs(center.x)>.18):continue
        side='FL' if center.x>0 else 'FR'
        nearest=door_shells[side].find_nearest(center)
        if nearest and nearest[3]<.075:labels[p.index]='Door_'+side
    groups={'Body':root}
    for side,c in centers.items():
        normalized=normalize(c)
        groups['Wheel_'+side]=new_empty('Wheel_'+side,root,normalized)
        groups['Wheel_'+side]['radius_m']=max(tire_components[0]['max'].z-tire_components[0]['min'].z,tire_components[0]['max'].y-tire_components[0]['min'].y)*scale/2
        groups['Wheel_'+side]['rotation_axis_gltf']='X'
    for side in ('FL','FR'):
        sign=1 if side=='FL' else -1
        pivot=normalize(Vector((sign*.195,.60,1.247)))
        door=new_empty('Door_'+side,root,pivot)
        door['opening_axis_gltf']='Z';door['opening_angle_gltf']=sign*1.22
        door['door_split_method']='Approximate inner-shell-guided adaptation of connected hull'
        glass=new_empty('Glass_'+side,door)
        glass['window_drop_m']=.30
        groups['Door_'+side]=door;groups['Glass_'+side]=glass
    counts={}
    for label,parent in groups.items():
        selected=[i for i,owner in labels.items() if owner==label]
        if not selected:raise RuntimeError('SLS empty required part '+label)
        pivot=parent.matrix_world.translation.copy() if parent!=root else Vector()
        bpy.context.view_layer.update();pivot=parent.matrix_world.translation.copy()
        obj=split_mesh(source,selected,'SLS_'+label+'_Geometry',parent,pivot)
        counts[label]=len(selected)
    assert sum(counts.values())==len(source.data.polygons)
    return groups,{'method':'Four real tire/rim component groups and two material-island side windows. Door hull adapted by proximity to original inner door shells.','partFaces':counts,'doorSplitApproximate':True,'windowCount':2,'wheelCount':4}

def build_atlas(imported):
    meshes=[o for o in imported if o.type=='MESH']
    groups={'Body':root};wheel_sources={};door_sources={}
    for side in ('FL','FR','RL','RR'):
        wheel=[o for o in meshes if any(a.name.startswith('ALUMINIUM_21_'+side+'_') for a in ancestors(o))]
        if len(wheel)!=2:raise RuntimeError('Atlas authored wheel group not found '+side)
        lo,hi=bounds(wheel);center=(lo+hi)/2
        groups['Wheel_'+side]=new_empty('Wheel_'+side,root,normalize(center))
        groups['Wheel_'+side]['radius_m']=max(hi.y-lo.y,hi.z-lo.z)*scale/2
        groups['Wheel_'+side]['rotation_axis_gltf']='X'
        wheel_sources[side]=wheel
        source_pivot=next(o for o in imported if o.name.startswith('EXT_DOOR_'+side+'_'))
        door=new_empty('Door_'+side,root,normalize(source_pivot.matrix_world.translation))
        door['opening_axis_gltf']='Y';door['opening_angle_gltf']=(-1 if side.endswith('L') else 1)*1.05
        door['door_split_method']='Original authored exterior and interior door hierarchy'
        groups['Door_'+side]=door
        glass=new_empty('Glass_'+side,door)
        glass['window_drop_m']=.49 if side.startswith('F') else .46
        groups['Glass_'+side]=glass
    windshield=new_empty('Windshield',root);windshield['interactive']=False
    groups['Windshield']=windshield
    counts={key:0 for key in groups}
    for index,original in enumerate(meshes):
        lineage=' '.join(a.name for a in ancestors(original))
        label='Body'
        for side in ('FL','FR','RL','RR'):
            if original in wheel_sources[side]:label='Wheel_'+side;break
            if 'EXT_DOOR_'+side+'_' in lineage or 'INT_DOOR_'+side+'_' in lineage:
                window=(('Ext_Door_'+side+'#Windows' in lineage) or ('Int_Door_'+side+'#Glass_Clear' in lineage))
                label=('Glass_' if window else 'Door_')+side;break
        if 'Window_Windshield#' in lineage:label='Windshield'
        parent=groups[label]
        bpy.context.view_layer.update();pivot=parent.matrix_world.translation.copy()
        new=extract_source_mesh(original,'Atlas_'+label+'_'+str(index),parent,pivot)
        counts[label]+=triangles([new])
    for key in ['Wheel_'+s for s in ('FL','FR','RL','RR')]+['Glass_'+s for s in ('FL','FR','RL','RR')]:
        if counts[key]<=0:raise RuntimeError('Atlas empty required part '+key)
    return groups,{'method':'Original authored door, paired interior/exterior window and wheel hierarchy; no body regions clipped.','partFaces':counts,'doorSplitApproximate':False,'windowCount':4,'wheelCount':4,'frontAndRearWindshieldsFixed':True}

def setup_render(scene):
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=768;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    w=bpy.data.worlds.new(scene.name+'_World');w.use_nodes=True
    w.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.25,.3,1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;scene.world=w
    for suffix,pos,energy,size in [('Key',(3,-3,6),1100,4),('Fill',(-4,-2,4),800,4),('Rim',(2,4,5),1400,3)]:
        data=bpy.data.lights.new(scene.name+'_'+suffix,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        o=bpy.data.objects.new(data.name,data);scene.collection.objects.link(o);o.location=pos
        o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new(scene.name+'_Camera');data.lens=52
    camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);camera.location=(6,-7,4.3)
    camera.rotation_euler=(Vector((0,0,.7))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera

def main():
    global collection,root,normalize,rotation,scale
    outputs=[ROOT/'frontend/public/assets/vehicles'/(spec[1]+'.glb') for spec in SPECS]
    for path in [BLEND,REPORT]+outputs:
        if path.exists():raise FileExistsError('Preserve existing revision: '+str(path))
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    initial=bpy.context.scene
    results=[];scenes=[]
    for spec,output in zip(SPECS,outputs):
        source_id,asset_id,height,angle=spec
        record=next(a for a in CATALOG if a['id']==source_id)
        source=ROOT/'frontend/public'/record['url'].lstrip('/')
        if sha(source)!=record['sha256']:raise RuntimeError('Supplied source changed '+source_id)
        scene=bpy.data.scenes.new(asset_id);bpy.context.window.scene=scene;scenes.append(scene)
        scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
        collection=bpy.data.collections.new(asset_id+'_Collection');scene.collection.children.link(collection)
        root=new_empty(asset_id);root['source_id']=source_id;root['source_credit']=json.dumps(record['credits'],ensure_ascii=False)
        before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(source));scene.frame_set(0);bpy.context.view_layer.update()
        imported=[o for o in bpy.data.objects if o not in before]
        source_meshes=[o for o in imported if o.type=='MESH']
        original_triangles=triangles(source_meshes);low,high=bounds(source_meshes)
        origin=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z));scale=height/(high.z-low.z)
        rotation=Matrix.Rotation(angle,3,'Z')
        normalize=lambda point,origin=origin.copy(),scale=scale,rotation=rotation.copy():rotation@((point-origin)*scale)
        log('Articulating '+asset_id+' actual triangles '+str(original_triangles))
        groups,method=(build_sls(imported) if source_id.endswith('sls_amg') else build_atlas(imported))
        for original in imported:bpy.data.objects.remove(original,do_unlink=True)
        objects=list(collection.objects);derived=[o for o in objects if o.type=='MESH']
        total=triangles(derived)
        if total!=original_triangles:raise RuntimeError('Source triangles must all be preserved exactly once')
        lo,hi=bounds(derived)
        if abs(lo.z)>0.002 or abs(hi.z-height)>0.002:raise RuntimeError('Car floor or normalized height invalid')
        wheel_check={}
        for name,group in groups.items():
            if not name.startswith('Wheel_'):continue
            children=list(group.children_recursive);before_low,before_high=bounds(children)
            center_before=(before_low+before_high)/2
            group.rotation_euler.x=math.pi/2
            after_low,after_high=bounds(children);center_after=(after_low+after_high)/2
            error=(center_after-center_before).length
            if error>.015:raise RuntimeError('Wheel moved from axle center '+name)
            group.rotation_euler.x=0
            wheel_check[name]={'pivotBlenderXYZ':list(group.location),'triangles':triangles(children),'radiusMeters':group['radius_m'],'centerDisplacementAt90Degrees':error,'passed':True}
        for image in bpy.data.images:
            if image.type!='RENDER_RESULT' and image.has_data:
                try:image.pack()
                except RuntimeError:pass
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        output.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,use_active_scene=True,
            export_yup=True,export_apply=True,export_animations=False,export_cameras=False,
            export_lights=False,export_extras=True,export_materials='EXPORT',export_draco_mesh_compression_enable=False)
        blob=output.read_bytes();jslength,_=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+jslength].rstrip(b'\x00 \t\r\n'))
        # Blender object names are global across scenes; preserve canonical
        # interactive names inside each separate exported asset.
        for node in doc.get('nodes',[]):
            canonical=node.get('extras',{}).get('asset_node_name')
            if canonical:node['name']=canonical
        encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8');encoded+=b' '*((-len(encoded))%4)
        tail=blob[20+jslength:]
        blob=struct.pack('<4sII',b'glTF',2,20+len(encoded)+len(tail))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+tail
        output.write_bytes(blob)
        if len(doc.get('scenes',[]))!=1:raise RuntimeError('Expected exactly one exported vehicle scene')
        required=['Wheel_'+s for s in ('FL','FR','RL','RR')]+['Glass_'+s for s in (('FL','FR') if source_id.endswith('sls_amg') else ('FL','FR','RL','RR'))]
        names={n.get('name') for n in doc.get('nodes',[])}
        if not all(name in names for name in required):raise RuntimeError('Named articulated nodes missing')
        setup_render(scene)
        closed=ROOT/'reports'/(asset_id+'_closed.png');opened=ROOT/'reports'/(asset_id+'_open_wheels90.png')
        scene.render.filepath=str(closed);bpy.ops.render.render(write_still=True)
        for name,group in groups.items():
            if name.startswith('Wheel_'):group.rotation_euler.x=math.pi/2
            if name.startswith('Door_'):
                if source_id.endswith('sls_amg'):group.rotation_euler.y=-(1 if name.endswith('L') else -1)*1.22
                else:group.rotation_euler.z=(-1 if name.endswith('L') else 1)*1.05
            if name.startswith('Glass_'):group.location.z=-group['window_drop_m']
        scene.render.filepath=str(opened);bpy.ops.render.render(write_still=True)
        for name,group in groups.items():
            if name.startswith(('Wheel_','Door_')):group.rotation_euler=(0,0,0)
            if name.startswith('Glass_'):group.location.z=0
        results.append({'assetId':asset_id,'source':{'id':source_id,'path':str(source),'sha256':record['sha256'],'stillUnchanged':sha(source)==record['sha256'],'credits':record['credits']},
          'glb':{'path':str(output),'url':'/assets/vehicles/'+output.name,'sha256':sha(output),'bytes':len(blob),'scenes':len(doc.get('scenes',[])),'meshes':len(doc.get('meshes',[])),'materials':len(doc.get('materials',[])),'embeddedImages':len(doc.get('images',[]))},
          'dimensionsBlenderXYZ':list(hi-lo),'feetZ':lo.z,'scale':1,'heightMeters':height,
          'canonicalForwardGltf':'+Z','sourceAppliedRotationDegrees':math.degrees(angle),'geometry':{'sourceTriangles':original_triangles,'derivedTriangles':total,'allSourceFacesPreservedOnce':True},
          'parts':method,'wheelRotationValidation':wheel_check,'requiredNodeNames':required,
          'render':{'closed':str(closed),'doorsOpenWindowsDownWheels90':str(opened),'visualReviewPending':True},'liveMcpTouched':False,'frontendConfigModified':False})
    bpy.data.scenes.remove(initial)
    bpy.context.window.scene=scenes[0]
    BLEND.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    for result in results:
        validation=bpy.data.scenes.new('VERIFY_'+result['assetId']);bpy.context.window.scene=validation
        before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=result['glb']['path']);bpy.context.view_layer.update()
        new=[o for o in bpy.data.objects if o not in before];meshes=[o for o in new if o.type=='MESH']
        total=triangles(meshes);lo,hi=bounds(meshes)
        finite=all(math.isfinite(x) for o in meshes for v in o.data.vertices for x in v.co)
        if not finite or total!=result['geometry']['sourceTriangles'] or abs(lo.z)>.002:raise RuntimeError('Actual exported vehicle reimport failed')
        result['actualReimport']={'passed':True,'meshes':len(meshes),'triangles':total,'vertices':sum(len(o.data.vertices) for o in meshes),'finite':finite,'dimensionsBlenderXYZ':list(hi-lo),'feetZ':lo.z}
    report={'date':'2026-10-05','blenderVersion':bpy.app.version_string,'blend':{'path':str(BLEND),'bytes':BLEND.stat().st_size,'sha256':sha(BLEND)},'assets':results}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
