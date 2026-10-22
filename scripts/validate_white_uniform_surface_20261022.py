"""Fresh Blender reimport, skin/contact checks and garment/name previews."""
import bpy,hashlib,json,math,struct
from datetime import datetime,timezone
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'art/characters/CHR_Remy_White_Uniform_Surface_Web_20261022.glb'
FULL=ROOT/'art/characters/CHR_Remy_White_Uniform_Surface_Source_20261022.glb'
BLEND=ROOT/'art/blender/libraries/PREP_REMY_WHITE_UNIFORM_SURFACE_VALIDATED_20261022.blend'
REPORT=ROOT/'reports/costumes/REMY_WHITE_UNIFORM_SURFACE_REIMPORT_20261022.json'
FINAL=bool(globals().get('PREP_SURFACE_FINAL',False))
if FINAL:
    TARGET=TARGET.parent/'white_uniform_final'/TARGET.name
    FULL=FULL.parent/'white_uniform_final'/FULL.name
    BLEND=BLEND.with_name('PREP_REMY_WHITE_UNIFORM_SURFACE_VALIDATED_FINAL_20261022.blend')
scene=bpy.data.scenes.new('PREP_REMY_WHITE_UNIFORM_SURFACE_REIMPORT_FINAL_20261022' if FINAL else 'PREP_REMY_WHITE_UNIFORM_SURFACE_REIMPORT_20261022')
bpy.context.window.scene=scene
bpy.ops.import_scene.gltf(filepath=str(TARGET))
meshes=[o for o in scene.objects if o.type=='MESH']
arm=next(o for o in scene.objects if o.type=='ARMATURE')
assert len(meshes)==27 and len(arm.data.bones)==55
garments=[o for o in meshes if o.name.startswith(('COAT_','SCRUB_'))]
decals=[o for o in meshes if o.get('uniformSurfaceAttachment')]
assert len(garments)==20 and len(decals)==6
tracks={track.name.rsplit('|',1)[-1]:track for track in arm.animation_data.nla_tracks}
assert set(tracks)=={'Idle','Walk','Dance','Interact'}
def surface(obj):return next(o for o in meshes if o.name.startswith(obj['uniformSurfaceMesh']))
def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    try:return [ev.matrix_world@v.co for v in mesh.vertices]
    finally:ev.to_mesh_clear()
def activate(clip,frame):
    arm.animation_data.action=None
    for key,track in tracks.items():track.mute=key!=clip
    scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
max_influences=0;weight_error=0
for obj in garments:
    for vertex in obj.data.vertices:
        weights=[g.weight for g in vertex.groups if g.weight>1e-8]
        max_influences=max(max_influences,len(weights));weight_error=max(weight_error,abs(sum(weights)-1))
assert max_influences<=4 and weight_error<.003
white=[]
for obj in garments:
    if obj.name.startswith('SCRUB_') and not obj.get('uniformSurfaceAttachment'):
        for material in obj.data.materials:
            node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            value=list(node.inputs['Base Color'].default_value)
            assert all(abs(component-1)<1e-6 for component in value)
            white.append(obj.name)
rows=[]
for clip in tracks:
    end=tracks[clip].strips[0].frame_end
    for fraction in (0,.25,.5,.75):
        activate(clip,1+(end-1)*fraction)
        gaps=[]
        for decal in decals:
            garment=surface(decal);vertices=points(garment)
            tree=KDTree(len(vertices))
            for i,p in enumerate(vertices):tree.insert(p,i)
            tree.balance()
            gaps.append(max(tree.find(p)[2] for p in points(decal)))
        maximum=max(gaps);assert maximum<=.001,(clip,fraction,maximum)
        rows.append({'clip':clip,'fraction':fraction,'maxSurfaceGapMeters':maximum})
raw=FULL.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
references=json.loads((ROOT/'frontend/src/config/uniformReferences.json').read_text())['files']
identities=[]
for image in doc['images']:
    if image['name'] not in ('nursing-crest','senac-logo'):continue
    view=doc['bufferViews'][image['bufferView']];offset=view.get('byteOffset',0)
    digest=hashlib.sha256(binary[offset:offset+view['byteLength']]).hexdigest()
    expected=next(r for r in references if r['name']==image['name']+'.png')['sha256']
    assert digest==expected
    identities.append({'name':image['name'],'byteIdentical':True,'sha256':digest})
assert len(identities)==2
scene.world=bpy.data.worlds.new('White_Uniform_Review_World');scene.world.color=(.07,.07,.07)
for location,power in (((2,-3,3),450),((-2,-2,2.5),280)):
    bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object
    light.data.energy=power;light.data.size=3
    light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO'
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=480;scene.render.resolution_y=640
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
# Only the Blender preview uses a 0.35mm separation for its depth buffer.
# The exported game asset stays exactly coplanar and uses polygonOffset.
preview_modifiers=[]
for obj in decals:
    modifier=obj.modifiers.new('QA_preview_depth_separation_only','DISPLACE')
    modifier.direction='NORMAL';modifier.strength=.00035/max(abs(v) for v in obj.matrix_world.to_scale());modifier.mid_level=0
    preview_modifiers.append(modifier)
    for mat in obj.data.materials:
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE':node.extension='CLIP'
name_images={key:bpy.data.images.load(str(ROOT/f'work/uniform_name_previews_20261022/{key}.png')) for key in ('romario','ana')}
def name_preview(key):
    for obj in decals:
        if '_NAME_' not in obj.name:continue
        mat=obj.data.materials[0]
        mat.diffuse_color=(1,1,1,1)
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        node=mat.node_tree.nodes.get('QA_DemoName') or mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.name='QA_DemoName';node.image=name_images[key];node.extension='CLIP'
        mat.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
        mat.node_tree.links.new(node.outputs['Alpha'],bsdf.inputs['Alpha'])
def visibility(coat):
    for obj in meshes:
        if obj.name.startswith(('Tops','Bottoms')):obj.hide_render=True
        elif obj.name.startswith('COAT_'):obj.hide_render=not coat
        elif obj.name.startswith('SCRUB_'):obj.hide_render=coat and 'Trouser' not in obj.name
def render(label,view='front',close=False):
    focus=Vector((0,-.02,1.31 if close else .88))
    camera.location=focus+Vector((0,-4,0) if view=='front' else (3,-2,.1))
    camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=.62 if close else 1.98
    output=ROOT/f'reports/costumes/white_uniform_surface_20261022/{label}_{view}.png'
    output.parent.mkdir(exist_ok=True,parents=True);scene.render.filepath=str(output)
    bpy.ops.render.render(write_still=True);return str(output)
renders=[];name_preview('romario')
for coat in (False,True):
    visibility(coat)
    for clip,frame in [('Idle',1),('Walk',1),('Walk',9),('Walk',17),('Walk',25)]:
        activate(clip,frame)
        for view in ('front','side'):renders.append(render(f'{"coat" if coat else "scrubs"}_{clip}_{frame:03d}',view))
    activate('Idle',1)
    for name in ('romario','ana'):
        name_preview(name);renders.append(render(f'{"coat" if coat else "scrubs"}_name_{name}',close=True))
for modifier in preview_modifiers:modifier.show_viewport=False;modifier.show_render=False
name_preview('romario');visibility(True);activate('Idle',1)
scene['PREP_demo_names_only']=True
scene['PREP_runtime_name_source']='individual player profile; QA names are examples only'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
report={'createdAt':datetime.now(timezone.utc).isoformat(),'status':'reimport-passed','asset':str(TARGET),
        'sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),'bytes':TARGET.stat().st_size,'blend':str(BLEND),
        'checks':{'freshReimport':True,'fourPreservedClips':True,'whiteScrubFabric':bool(white),
                  'sixCoplanarAttachments':len(decals)==6,'maxFourNormalizedWeights':True,'surfaceGapWithin1mm':True,
                  'originalIdentityPngBytesPreserved':True},'maxGapMeters':max(r['maxSurfaceGapMeters'] for r in rows),
        'samples':rows,'identities':identities,'renders':renders,'visualReview':'pending',
        'previewOnlyDepthSeparationMeters':.00035,'sourceRigModified':False}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','checks','maxGapMeters','sha256','blend')}))
