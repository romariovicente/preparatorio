"""Prepare the openly licensed HRA/Allen anatomical brain without touching live Blender.

Run in a factory background Blender. --inspect renders the unmodified shape first.
The original GLB and its anatomical names are kept in a separate source scene.
"""
from pathlib import Path
import bpy
import json
import hashlib
import math
import sys
import struct
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'art/references/brain_hra_male_v1_4'
SOURCE=REF/'brain_original.glb'
REPORT_DIR=ROOT/'reports/brain_real_20261005'
REPORT_DIR.mkdir(parents=True,exist_ok=True)
GLB=ROOT/'frontend/public/assets/monuments/PROP_Brain_Real_20261005.glb'
BLEND=ROOT/'art/blender/PREPARATORIO_BRAIN_20261005.blend'
INSPECT='--inspect' in sys.argv
TARGET_HEIGHT=6.0
MAX_TRIANGLES=150000

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def mesh_bounds(objects):
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(v) for o in objects if o.type=='MESH' for v in o.bound_box]
    low=Vector([min(p[i] for p in points) for i in range(3)])
    high=Vector([max(p[i] for p in points) for i in range(3)])
    return low,high
def triangles(objects):
    count=0
    for obj in objects:
        if obj.type=='MESH':obj.data.calc_loop_triangles();count+=len(obj.data.loop_triangles)
    return count
def point_camera(camera,target):
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
def add_area(scene,name,location,power,size,color,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=location;point_camera(obj,target)
def setup_render(scene,objects,path):
    low,high=mesh_bounds(objects);center=(low+high)*.5;size=high-low
    data=bpy.data.cameras.new('CAM_Brain_Inspection');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera)
    camera.location=center+Vector((size.x*1.05,-size.y*1.30,size.z*.85));point_camera(camera,center)
    data.type='ORTHO';data.ortho_scale=max(size)*1.45;scene.camera=camera
    target=tuple(center)
    add_area(scene,'LIGHT_Brain_Key',tuple(center+Vector((-7,-8,12))),2000,7,(1.0,.92,.86),target)
    add_area(scene,'LIGHT_Brain_Fill',tuple(center+Vector((9,-2,6))),1300,8,(.78,.86,1.0),target)
    add_area(scene,'LIGHT_Brain_Rim',tuple(center+Vector((3,8,10))),1800,5,(1.0,.94,.89),target)
    scene.world=bpy.data.worlds.new('WORLD_Brain_Studio');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.045,.060,.075,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path)
    scene.view_settings.view_transform='AgX';scene.render.film_transparent=False
def material():
    mat=bpy.data.materials.new('MAT_Brain_Neutral_Tissue_Real');mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(.60,.39,.33,1)
    bsdf.inputs['Roughness'].default_value=.48
    bsdf.inputs['Metallic'].default_value=0
    bsdf.inputs['Specular IOR Level'].default_value=.30
    bsdf.inputs['Subsurface Weight'].default_value=.075
    mat.diffuse_color=(.60,.39,.33,1)
    return mat

assert SOURCE.exists(),'Missing legitimate source download'
assert sha(SOURCE)=='c97d7d0b9ff0baebbdec5566fa7b08d789195ef965e0bd04cf743a8d683882db','Unexpected source GLB'
if not INSPECT:
    assert not GLB.exists() and not BLEND.exists(),'Do not overwrite previously prepared deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
original=bpy.context.scene;original.name='SOURCE_HRA_BRAIN_v1_4'
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
source_objects=list(original.objects);meshes=[o for o in source_objects if o.type=='MESH']
assert meshes,'No anatomical meshes imported'
original.unit_settings.system='METRIC';original.unit_settings.scale_length=1
lo,hi=mesh_bounds(meshes)
source_report={'source':str(SOURCE),'sha256':sha(SOURCE),'bounds':{'min':list(lo),'max':list(hi)},
    'triangles':triangles(meshes),'objects':len(source_objects),'meshes':len(meshes),
    'meshRecords':[{'name':o.name,'triangles':triangles([o]),'dimensions':list(o.dimensions)} for o in meshes]}
scene=bpy.data.scenes.new('PREP_BRAIN_MONUMENT_20261005');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
collection=bpy.data.collections.new('PREP_Brain_Anatomical_20261005');scene.collection.children.link(collection)
scale=TARGET_HEIGHT/(hi.z-lo.z)
normalize=Matrix.Translation(Vector((-(lo.x+hi.x)*.5,-(lo.y+hi.y)*.5,-lo.z))*scale)@Matrix.Scale(scale,4)
prepared=[];tissue=material()
for source in meshes:
    obj=source.copy();obj.data=source.data.copy();obj.name='PROP_Brain_Real__'+source.name
    obj.parent=None;obj.matrix_world=normalize@source.matrix_world
    obj.data.materials.clear();obj.data.materials.append(tissue)
    for face in obj.data.polygons:face.material_index=0;face.use_smooth=True
    collection.objects.link(obj);prepared.append(obj)
    obj['source_anatomical_name']=source.name;obj['source_url']='https://purl.humanatlas.io/ref-organ/brain-male/v1.4'
    obj['source_license']='CC-BY-4.0';obj['author']='Romario Vicente Amaro (game adaptation); Kristen Browne and Heidi Schlehlein (HRA model)'
if INSPECT:
    setup_render(scene,prepared,REPORT_DIR/'brain_source_inspection.png')
    (REPORT_DIR/'source_inspection.json').write_text(json.dumps(source_report,indent=2),encoding='utf-8')
    bpy.ops.render.render(write_still=True)
    print('BRAIN_INSPECTION_COMPLETE',flush=True)
else:
    original_count=triangles(prepared)
    if original_count>MAX_TRIANGLES:
        ratio=(MAX_TRIANGLES-1000)/original_count
        for obj in prepared:
            bpy.context.view_layer.objects.active=obj;obj.select_set(True)
            modifier=obj.modifiers.new('PREP_Geometry_Budget','DECIMATE');modifier.ratio=ratio
            modifier.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=modifier.name);obj.select_set(False)
    count=triangles(prepared);assert count<=MAX_TRIANGLES,(count,MAX_TRIANGLES)
    low,high=mesh_bounds(prepared)
    # A collapse may remove an extremal vertex; restore the derivative's exact
    # height and base afterwards without touching source objects or topology.
    correction_scale=TARGET_HEIGHT/(high.z-low.z)
    correction=Matrix.Translation(Vector((-(low.x+high.x)*.5,-(low.y+high.y)*.5,-low.z))*correction_scale)@Matrix.Scale(correction_scale,4)
    for obj in prepared:obj.matrix_world=correction@obj.matrix_world
    low,high=mesh_bounds(prepared)
    assert abs(low.z)<1e-5 and abs(high.z-TARGET_HEIGHT)<.02,('normalization',list(low),list(high))
    for obj in prepared:
        assert all(math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co),'Non-finite source vertices'
    GLB.parent.mkdir(parents=True,exist_ok=True);BLEND.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in prepared:obj.select_set(True)
    bpy.context.view_layer.objects.active=prepared[0]
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,
                              export_extras=True,export_animations=False,export_materials='EXPORT')
    raw=GLB.read_bytes();gltf=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
    assert len(gltf.get('scenes',[]))==1,'Export must contain only the prepared monument scene'
    exported_count=sum(gltf['accessors'][primitive['indices']]['count']//3 for mesh in gltf['meshes'] for primitive in mesh['primitives'])
    assert 0<exported_count<=count<=MAX_TRIANGLES,'Invalid exported triangle budget'
    setup_render(scene,prepared,REPORT_DIR/'brain_real_preview.png')
    report={'id':'PROP_Brain_Real_20261005','source':source_report,
      'credits':{'author':'Kristen Browne and Heidi Schlehlein; HRA/HuBMAP, using Allen Human Reference Atlas data',
        'license':'CC-BY-4.0','licenseUrl':'https://creativecommons.org/licenses/by/4.0/',
        'source':'https://purl.humanatlas.io/ref-organ/brain-male/v1.4','doi':'https://doi.org/10.48539/HBM538.NKCT.649'},
      'modifications':'Uniform 6 m monumental scale, origin centered at base, restrained neutral tissue PBR material and polygon reduction when required. Original anatomical structures and source file retained.',
      'url':'/assets/monuments/PROP_Brain_Real_20261005.glb','glb':str(GLB),'blend':str(BLEND),
      'triangles':exported_count,'preparedTriangles':count,'degenerateTrianglesOmittedByExporter':count-exported_count,
      'meshes':len(prepared),'bounds':{'min':list(low),'max':list(high)},
      'dimensions':list(high-low),'height':TARGET_HEIGHT,'bytes':GLB.stat().st_size,'sha256':sha(GLB)}
    validate=bpy.data.scenes.new('VALIDATE_BRAIN_GLB_REIMPORT');bpy.context.window.scene=validate
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    imported=[o for o in validate.objects if o.type=='MESH'];ilo,ihi=mesh_bounds(imported)
    icount=triangles(imported)
    assert icount==exported_count,('reimport triangle mismatch',exported_count,icount)
    assert all(abs(ilo[i]-low[i])<1e-4 and abs(ihi[i]-high[i])<1e-4 for i in range(3)),('reimport bounds',list(ilo),list(ihi))
    assert all(math.isfinite(v) for obj in imported for vertex in obj.data.vertices for v in vertex.co),'Non-finite reimport'
    report['reimportValidated']=True;report['reimport']={'triangles':icount,'meshes':len(imported),'min':list(ilo),'max':list(ihi)}
    bpy.context.window.scene=scene
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.render.render(write_still=True)
    scene.camera.location=Vector((0,0,3))+Vector((-6,9,5));point_camera(scene.camera,(0,0,3))
    scene.render.filepath=str(REPORT_DIR/'brain_real_rear_preview.png');bpy.ops.render.render(write_still=True)
    report['preview']=str(REPORT_DIR/'brain_real_preview.png');report['rearPreview']=str(REPORT_DIR/'brain_real_rear_preview.png')
    report['blendBytes']=BLEND.stat().st_size
    (REPORT_DIR/'brain_real_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('BRAIN_PREPARED_REIMPORTED_RENDERED',json.dumps({'triangles':exported_count,'meshes':len(prepared),'sha256':report['sha256']}),flush=True)
