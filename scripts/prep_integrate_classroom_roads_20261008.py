"""Integrate the verified classroom and road polygons into the saved city."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
city=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
for window in bpy.context.window_manager.windows:
    window.scene=city
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='SOLID'
            area.spaces.active.shading.color_type='MATERIAL'
parent=bpy.data.collections.get('ARAP_16_CLASSROOM_20261008')
if not parent:
    parent=bpy.data.collections.new('ARAP_16_CLASSROOM_20261008');city.collection.children.link(parent)
    names=['PREP_CLASSROOM_ARCHITECTURE','PREP_CLASSROOM_FURNITURE','PREP_CLASSROOM_EDUCATIONAL','PREP_CLASSROOM_REAL_STUDENTS']
    with bpy.data.libraries.load(str(ROOT/'art/blender/PREPARATORIO_CLASSROOM_FUTURISTIC_20261007.blend'),link=False) as (available,loaded):
        assert all(n in available.collections for n in names)
        loaded.collections=names
    anchor=bpy.data.objects.new('PREP_CLASSROOM_CITY_ANCHOR',None);parent.objects.link(anchor)
    for collection in loaded.collections:
        parent.children.link(collection)
        for obj in collection.objects:
            if obj.parent is None:
                basis=obj.matrix_basis.copy();obj.parent=anchor;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=basis
    wall=next(o for o in parent.all_objects if o.name.startswith('BLD_Classroom_RearWallLeft'))
    mesh=bpy.data.meshes.new('Classroom_Door_Infill_Mesh')
    vertices=[(x*.903/2,y*.16/2,z*3.76/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    mesh.from_pydata(vertices,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    infill=bpy.data.objects.new('BLD_Classroom_DoorOpening_Infill_20261008',mesh);parent.objects.link(infill)
    infill.parent=anchor;infill.location=(4.1515,5.92,1.88);infill.data.materials.append(wall.data.materials[0])
    hinge=bpy.data.objects.new('DOOR_Classroom_Animated',None);parent.objects.link(hinge)
    hinge.location=(4.715,5.92,0)
    bpy.context.view_layer.update()
    for name in ['MOD_Classroom_Door','PROP_Classroom_DoorHandle']:
        part=next(o for o in parent.all_objects if o.name.startswith(name))
        matrix=part.matrix_world.copy();part.parent=hinge;part.matrix_world=matrix
    hinge.parent=anchor
    for frame,angle in [(1,0),(45,0),(85,math.radians(85)),(140,math.radians(85)),(180,0)]:
        hinge.rotation_euler.z=angle;hinge.keyframe_insert(data_path='rotation_euler',frame=frame)
    hinge.rotation_euler.z=0
    anatomy=next(c for c in bpy.data.collections if c.name.startswith('PREP_DELIVERY_EDU_Anatomy_XRay_20261006'))
    exhibit=bpy.data.objects.new('EDU_Classroom_Anatomy_Instance',None);parent.objects.link(exhibit)
    exhibit.instance_type='COLLECTION';exhibit.instance_collection=anatomy;exhibit.parent=anchor;exhibit.location=(-2.75,-4.2,.18)
    anchor.location=(16,-60,0)
roads=json.loads((ROOT/'reports/new_delivery_roads_20261008.json').read_text(encoding='utf-8'))
road_collection=bpy.data.collections.get('ARAP_17_DELIVERY_ROAD_CONNECTIONS_20261008')
if not road_collection:
    road_collection=bpy.data.collections.new('ARAP_17_DELIVERY_ROAD_CONNECTIONS_20261008');city.collection.children.link(road_collection)
    batches={}
    for surface in roads['surfaces']:
        key=(surface['material'],surface['surfaceY']);batches.setdefault(key,[]).append(surface)
    for (material_name,height),surfaces in batches.items():
        vertices=[];faces=[]
        for surface in surfaces:
            offset=len(vertices);points=surface['blenderVertices'];vertices.extend(points);faces.append(tuple(range(offset,offset+len(points))))
        mesh=bpy.data.meshes.new('DELIVERY_ROAD_'+material_name+str(height));mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh);road_collection.objects.link(obj);obj['walkable']=True
        spec=roads['materials'][material_name];material=bpy.data.materials.get(spec['source'])
        if not material:
            material=bpy.data.materials.new('MAT_DELIVERY_'+material_name);material.use_nodes=True
            material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*spec['linearColor'],1)
            material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=spec['roughness']
            material.diffuse_color=(*spec['linearColor'],1)
        obj.data.materials.append(material)
bus=bpy.data.objects.get('DELIVERY_BUS_CIRCULAR')
if bus and bus.animation_data and bus.animation_data.action:
    for layer in bus.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
city.frame_start=1;city.frame_end=max(city.frame_end,6301);city.frame_set(1)
for window in bpy.context.window_manager.windows:
    window.scene=city
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            view=area.spaces.active.region_3d;view.view_location=(16,-60,1.4);view.view_distance=25
            view.view_rotation=(Vector((27,-43,12))-Vector((16,-60,1.4))).to_track_quat('Z','Y')
dest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261008.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'saved':str(dest),'sceneObjects':len(city.objects),'classroomCollection':parent.name,'classroomObjects':len(parent.all_objects),'students':len([o for o in parent.all_objects if o.type=='ARMATURE']),'roadMeshes':len(road_collection.objects),'roadPolygons':sum(len(o.data.polygons) for o in road_collection.objects),'frameEnd':city.frame_end,'view':'Solid material colors; textured Material Preview remains available'}
(ROOT/'reports/live_classroom_roads_20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
