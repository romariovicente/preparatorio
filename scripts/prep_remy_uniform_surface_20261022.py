"""Attach identity to copied garment triangles; preserve Remy's rig and motion."""
import bpy,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
WORKING=ROOT/'art/blender/libraries/PREP_REMY_UNIFORM_SURFACE_20261022.blend'
FINAL=bool(globals().get('PREP_SURFACE_FINAL',False))
OUTPUT=ROOT/('art/characters/CHR_Remy_White_Uniform_Surface_20261022_v4.glb' if FINAL else 'art/characters/CHR_Remy_Uniform_Surface_20261022.glb')
REPORT=ROOT/'reports/costumes/REMY_UNIFORM_SURFACE_BUILD_20261022.json'
assert Path(bpy.data.filepath).resolve()==WORKING.resolve() or (FINAL and 'PREP_REMY_WHITE_UNIFORM_SURFACE_VALIDATED_20261022.blend' in bpy.data.filepath)
assert not OUTPUT.exists(), 'Preserve existing candidate before another revision.'
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
assert len(arm.data.bones)==55
scene.name='PREP_REMY_UNIFORM_SURFACE_STAGE_20261022'
garments=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(('COAT_','SCRUB_'))]
assert len(garments)==20
rows=[]
for prefix,is_coat in [('COAT',True),('SCRUB',False)]:
    cloth=bpy.data.objects[prefix+'_Remy_'+('FittedShell' if is_coat else 'Shirt')]
    cloth.data.calc_loop_triangles()
    points=[cloth.matrix_world@vertex.co for vertex in cloth.data.vertices]
    for role,cx,cz,width,height in (
        ('BRAND_Remy_Crest',-.106,1.325,.112,.127),
        ('BRAND_Remy_Senac',.082 if FINAL else .155,1.33 if FINAL else 1.402,.060 if FINAL else .064,.062 if FINAL else .065),
        ('NAME_Remy_Player',.078 if FINAL else .093,1.270 if FINAL else 1.302,.120 if FINAL else .159,.048 if FINAL else .060),
    ):
        name=prefix+'_'+role
        old=bpy.data.objects[name]
        material=old.data.materials[0]
        triangles=[]
        for triangle in cloth.data.loop_triangles:
            coords=[points[i] for i in triangle.vertices]
            normal=(coords[1]-coords[0]).cross(coords[2]-coords[0])
            if normal.length_squared<1e-16 or normal.normalized().y>-.12:continue
            if sum(p.y for p in coords)/3>.025:continue
            if max(p.x for p in coords)<cx-width/2 or min(p.x for p in coords)>cx+width/2:continue
            if max(p.z for p in coords)<cz-height/2 or min(p.z for p in coords)>cz+height/2:continue
            triangles.append(tuple(triangle.vertices))
        used=sorted({i for triangle in triangles for i in triangle})
        assert len(used)>=4,(name,len(used))
        lookup={original:index for index,original in enumerate(used)}
        mesh=bpy.data.meshes.new(name+'_GarmentTriangles')
        mesh.from_pydata([cloth.data.vertices[i].co.copy() for i in used],[],
                         [tuple(lookup[i] for i in triangle) for triangle in triangles])
        mesh.materials.append(material)
        old.data=mesh
        old.parent=cloth.parent
        old.matrix_parent_inverse=cloth.matrix_parent_inverse.copy()
        old.matrix_world=cloth.matrix_world.copy()
        old.vertex_groups.clear()
        groups={group.index:old.vertex_groups.new(name=group.name) for group in cloth.vertex_groups}
        for index,original in enumerate(used):
            for group in cloth.data.vertices[original].groups:
                groups[group.group].add([index],group.weight,'REPLACE')
        for modifier in list(old.modifiers):old.modifiers.remove(modifier)
        for modifier in cloth.modifiers:
            if modifier.type=='ARMATURE':
                skin=old.modifiers.new('Remy_Original_Cloth_Skin','ARMATURE')
                skin.object=modifier.object
                skin.use_vertex_groups=modifier.use_vertex_groups
                skin.use_deform_preserve_volume=modifier.use_deform_preserve_volume
        uv=mesh.uv_layers.new(name='IdentityProjection')
        for polygon in mesh.polygons:
            polygon.use_smooth=True
            for loop in polygon.loop_indices:
                p=points[used[mesh.loops[loop].vertex_index]]
                uv.data[loop].uv=((p.x-cx)/width+.5,(p.z-cz)/height+.5)
        for node in material.node_tree.nodes:
            if node.type=='TEX_IMAGE':node.extension='CLIP'
        old['uniformSurfaceAttachment']=True
        old['uniformSurfaceMesh']=cloth.name
        old['uniformSurfaceVertexMap']=used
        old['uniformSurfaceOffsetMeters']=0.0
        old['uniformSurfaceUVClip']=True
        rows.append({'name':name,'surface':cloth.name,'vertices':len(used),'triangles':len(triangles),
                     'zeroOffset':True,'sameWeightsAndBind':True,'projection':{'x':cx,'z':cz,'width':width,'height':height}})
assert len(rows)==6
# Export exactly the character's existing meshes/rig, never staging equipment.
for obj in scene.objects:obj.select_set(obj.type in ('MESH','ARMATURE','EMPTY'))
bpy.context.view_layer.objects.active=arm
arm.animation_data.action=None
for track in arm.animation_data.nla_tracks:track.mute=False
scene.frame_set(1)
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUTPUT),export_format='GLB',use_selection=True,
                         export_yup=True,export_animations=True,export_skins=True,
                         export_animation_mode='NLA_TRACKS',export_cameras=False,export_lights=False,
                         export_extras=True,export_image_format='AUTO')
bpy.ops.wm.save_as_mainfile(filepath=str(WORKING),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'built-awaiting-reimport-and-runtime-validation',
        'working':str(WORKING),'glb':str(OUTPUT),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        'bytes':OUTPUT.stat().st_size,'sourcePreserved':True,'rigModified':False,'animationsModified':False,
        'patches':rows,'runtimeRequirements':['clip map UV outside 0..1','polygon offset for coplanar identity'],
        'scope':'six identity surfaces only; other character coats and tailoring remain separate work'}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
