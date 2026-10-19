"""Build a real scanned Florence Nightingale monument in isolated Blender.

The downloaded Scan-the-World figure is kept unchanged on disk. The new
pedestal, inscriptions and bronze ornaments are original game adaptations.
No live MCP connection or other scene files are touched by this script.
Run: blender --background --factory-startup --python this_file.py
"""
from pathlib import Path
import bpy
import json
import math
import hashlib
import struct
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'art/references/florence_zenodo_21163474'
SOURCE = REFERENCE / 'b8b72586064167bb7bc5bf56ccc70375_normalized_optimized.glb'
SOURCE_SHA = 'f8701c5c7200cb485fada8e276d3d11c7fb6e3025fcd1577606869d96d873636'
BLEND = ROOT / 'art/blender/PREPARATORIO_FLORENCE_20261005.blend'
GLB = ROOT / 'frontend/public/assets/monuments/PROP_Florence_Nightingale_Real_20261005.glb'
REPORT = ROOT / 'reports/florence_monument_validation_20261005.json'
RENDER_FRONT = ROOT / 'reports/florence_monument_front_20261005.png'
RENDER_REVERSE = ROOT / 'reports/florence_monument_reverse_20261005.png'
TEXTURES = ROOT / 'art/textures/florence_granite_20261005'
ASSET_NAME = 'PROP_Florence_Nightingale_Real_20261005'
SOURCE_CREDIT = ('Florence Nightingale — Scan-the-World / 3DBigDataSpace. '
                 'Zenodo DOI 10.5281/zenodo.21163474. CC BY-NC-SA 4.0.')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log(message):
    print('FLORENCE: ' + message, flush=True)


def select_only(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def relocate(obj):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def material(name, color, metal=0.0, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = tuple(color) + (1.0,)
    principled = mat.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value = mat.diffuse_color
    principled.inputs['Metallic'].default_value = metal
    principled.inputs['Roughness'].default_value = roughness
    return mat


def bake_granite(name, base, dark, light):
    """Bake an original procedural stone color to an embedded 8-bit image."""
    log('Baking ' + name)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    coord = nodes.new('ShaderNodeTexCoord')
    grain = nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value = 115.0
    grain.inputs['Detail'].default_value = 2.1
    grain.inputs['Roughness'].default_value = 0.8
    links.new(coord.outputs['Generated'], grain.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    elements = ramp.color_ramp.elements
    elements[0].position = 0.29
    elements[0].color = tuple(dark) + (1.0,)
    elements[1].position = 0.73
    elements[1].color = tuple(light) + (1.0,)
    middle = elements.new(0.50)
    middle.color = tuple(base) + (1.0,)
    links.new(grain.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs[0], output.inputs['Surface'])
    image = bpy.data.images.new(name + '_BaseColor_512', 512, 512, alpha=False, float_buffer=False)
    image.colorspace_settings.name = 'sRGB'
    target = nodes.new('ShaderNodeTexImage')
    target.image = image
    nodes.active = target
    bpy.ops.mesh.primitive_plane_add(size=1)
    plane = bpy.context.object
    plane.name = 'TEMP_Granite_Bake'
    plane.data.materials.append(mat)
    select_only([plane])
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 1
    bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(TEXTURES / (name + '_BaseColor.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
    bpy.data.objects.remove(plane, do_unlink=True)
    # The exported material uses the baked color directly, not Blender-only nodes.
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    pbr = nodes.new('ShaderNodeBsdfPrincipled')
    pbr.inputs['Roughness'].default_value = 0.69
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.interpolation = 'Linear'
    links.new(texture.outputs['Color'], pbr.inputs['Base Color'])
    links.new(pbr.outputs[0], out.inputs['Surface'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.13
    bump.inputs['Distance'].default_value = 0.012
    links.new(texture.outputs['Color'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], pbr.inputs['Normal'])
    mat.diffuse_color = tuple(base) + (1.0,)
    return mat


def box(name, size, center, mat, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = relocate(bpy.context.object)
    obj.name = name
    obj.data.name = name + '_Mesh'
    for vertex in obj.data.vertices:
        for axis in range(3):
            vertex.co[axis] *= size[axis]
    obj.location = center
    obj.parent = root
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft stone edges', 'BEVEL')
        mod.width = min(bevel, min(size) / 4)
        mod.segments = 3
        mod.limit_method = 'ANGLE'
    return obj


def text(name, body, position, size, mat, rotation=(math.pi / 2, 0, 0)):
    curve = bpy.data.curves.new(name + '_Font', 'FONT')
    curve.body = body
    curve.size = size
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.extrude = 0.0012
    curve.bevel_depth = 0.00045
    curve.bevel_resolution = 1
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.parent = root
    obj.location = position
    obj.rotation_euler = rotation
    curve.materials.append(mat)
    select_only([obj])
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def curve_ornament(name, points, side_rotation):
    data = bpy.data.curves.new(name + '_Curve', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 16
    data.bevel_depth = 0.013
    data.bevel_resolution = 3
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for knot, point in zip(spline.bezier_points, points):
        knot.co = point
        knot.handle_left_type = 'AUTO'
        knot.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = root
    obj.rotation_euler.z = side_rotation
    data.materials.append(ornament_bronze)
    select_only([obj])
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def sphere(name, location, radius, mat, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, location=location)
    obj = relocate(bpy.context.object)
    obj.name = name
    obj.parent = root
    for vert in obj.data.vertices:
        vert.co.x *= scale[0]
        vert.co.y *= scale[1]
        vert.co.z *= scale[2]
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def world_bounds(objects):
    bpy.context.view_layer.update()
    values = [obj.matrix_world @ Vector(vertex) for obj in objects if obj.type == 'MESH' for vertex in obj.bound_box]
    if not values:
        raise RuntimeError('No mesh bounds')
    lo = Vector(tuple(min(v[i] for v in values) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in values) for i in range(3)))
    return lo, hi


def camera_at(name, position, target):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens = 58
    scene.camera = obj
    return obj


def render_view(path, camera):
    scene.camera = camera
    scene.render.filepath = str(path)
    log('Rendering ' + path.name)
    bpy.ops.render.render(write_still=True)


def main():
    global scene, collection, root, ornament_bronze
    for output in (BLEND, GLB, REPORT, RENDER_FRONT, RENDER_REVERSE):
        if output.exists():
            raise FileExistsError('Review existing output before creating another revision: ' + str(output))
    if not SOURCE.is_file() or sha(SOURCE) != SOURCE_SHA:
        raise RuntimeError('Downloaded scan SHA does not match the provider')
    for scene_data in list(bpy.data.scenes):
        if scene_data != bpy.context.scene:
            bpy.data.scenes.remove(scene_data)
    scene = bpy.context.scene
    scene.name = 'PREP_FLORENCE_NIGHTINGALE_20261005'
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'
    collection = bpy.data.collections.new('PREP_FLORENCE_REAL_MONUMENT')
    scene.collection.children.link(collection)
    root = bpy.data.objects.new(ASSET_NAME, None)
    collection.objects.link(root)
    root['asset_id'] = ASSET_NAME
    root['pedestal_author'] = 'Romario Vicente Amaro — Projeto PREPARATÓRIO'
    root['figure_source_credit'] = SOURCE_CREDIT
    root['license'] = 'CC-BY-NC-SA-4.0'
    root['source_sha256'] = SOURCE_SHA
    log('Importing real scanned Florence figure')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    imported_meshes = [obj for obj in imported if obj.type == 'MESH']
    if not imported_meshes:
        raise RuntimeError('The scan did not import as geometry')
    low, high = world_bounds(imported_meshes)
    original_bounds = {'min':list(low), 'max':list(high)}
    height_scale = 3.4 / (high.z - low.z)
    origin = Vector(((low.x + high.x)/2, (low.y + high.y)/2, low.z))
    derived = []
    for index, original in enumerate(imported_meshes):
        mesh = original.data.copy()
        mesh.name = 'Florence_Real_Scan_Geometry_' + str(index)
        world = original.matrix_world.copy()
        for vertex in mesh.vertices:
            vertex.co = (world @ vertex.co - origin) * height_scale + Vector((0,0,3.2))
        obj = bpy.data.objects.new('FLORENCE_SCAN_Real_Figure_' + str(index), mesh)
        collection.objects.link(obj)
        obj.parent = root
        obj['source'] = SOURCE_CREDIT
        for poly in mesh.polygons:
            poly.use_smooth = True
        for slot, source_mat in enumerate(list(mesh.materials)):
            bronze = source_mat.copy()
            bronze.name = 'MAT_Florence_Real_Bronze_' + str(slot)
            pbr = next(node for node in bronze.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
            for socket in ('Base Color','Metallic','Roughness'):
                for link in list(pbr.inputs[socket].links):
                    bronze.node_tree.links.remove(link)
            pbr.inputs['Base Color'].default_value = (0.055,0.045,0.031,1)
            pbr.inputs['Metallic'].default_value = 0.80
            pbr.inputs['Roughness'].default_value = 0.59
            pbr.inputs['Coat Weight'].default_value = 0.09
            bronze.diffuse_color = (0.055,0.045,0.031,1)
            mesh.materials[slot] = bronze
        derived.append(obj)
    for original in imported:
        bpy.data.objects.remove(original,do_unlink=True)
    figure_low, figure_high = world_bounds(derived)
    if abs(figure_low.z - 3.2) > 0.001 or abs(figure_high.z - 6.6) > 0.001:
        raise RuntimeError('Figure normalization did not meet exact meter-scale bounds')
    red_granite = bake_granite('MAT_Granite_Red_Florence', (.28,.20,.17), (.07,.06,.05), (.54,.43,.38))
    grey_granite = bake_granite('MAT_Granite_Grey_Florence', (.23,.24,.24), (.055,.06,.062), (.49,.5,.49))
    ornament_bronze = material('MAT_Florence_Pedestal_Bronze',(.095,.072,.04),.76,.46)
    lettering = material('MAT_Florence_Lettering_Warm_Bronze',(.57,.4,.17),.75,.34)
    inscription = material('MAT_Florence_Inscription_Dark_Bronze',(.020,.015,.007),.2,.65)
    # The reference has a pale lower plinth, red granite center and stepped cornices.
    tiers = [
      ('Ground_Step', (2.92,2.80,.20), (0,0,.10), grey_granite,.035),
      ('Lower_Molding', (2.66,2.56,.18), (0,0,.29), grey_granite,.026),
      ('Lower_Plinth', (2.46,2.34,.93), (0,0,.845), grey_granite,.030),
      ('Grey_Upper_Molding', (2.60,2.50,.14), (0,0,1.38), grey_granite,.022),
      ('Red_Base_Molding', (2.34,2.25,.18), (0,0,1.54), red_granite,.022),
      ('Red_Core', (2.10,2.0,.94), (0,0,2.10), red_granite,.018),
      ('Red_Lower_Cornice', (2.27,2.18,.15), (0,0,2.645), red_granite,.020),
      ('Name_Band', (2.23,2.14,.28), (0,0,2.86), red_granite,.016),
      ('Upper_Cornice', (2.55,2.44,.16), (0,0,3.08), red_granite,.022),
      ('Figure_Slab', (1.49,1.44,.04), (0,0,3.18), ornament_bronze,.006),
    ]
    for suffix, size, center, mat, bevel in tiers:
        box('FLORENCE_Pedestal_' + suffix,size,center,mat,bevel)
    for side in range(4):
        angle = side * math.pi/2
        nx,ny = math.sin(angle),-math.cos(angle)
        panel = box('FLORENCE_Bronze_Inset_'+str(side),(1.35,.035,.56),(nx*1.017,ny*1.017,2.10),ornament_bronze,.010)
        panel.rotation_euler.z = angle
        # Original symmetrical fern/scroll ornaments. These are not replicas of historic bas-reliefs.
        for direction in (-1,1):
            points = [(direction*0.26,-1.041,1.91), (direction*0.16,-1.041,2.04), (direction*0.17,-1.041,2.21), (direction*0.28,-1.041,2.27), (direction*0.31,-1.041,2.18)]
            curve_ornament('FLORENCE_Bronze_Scroll_%d_%d'%(side,direction),points,angle)
        for height in (1.98,2.06,2.14,2.22):
            px = -math.sin(angle)*1.045
            py = -math.cos(angle)*1.045
            sphere('FLORENCE_Bronze_Seed_%d_%s'%(side,height),(px,py,height),.025,lettering)
    text('FLORENCE_Name','FLORENCE NIGHTINGALE',(0,-1.084,2.92),.121,inscription)
    text('FLORENCE_Lifetime','1820 — 1910',(0,-1.085,2.78),.106,inscription)
    text('FLORENCE_Tribute','Pioneira da enfermagem moderna',(0,-1.051,1.78),.068,inscription)
    text('FLORENCE_Game_Author','PREPARATÓRIO · Romario Vicente Amaro',(0,-1.184,.52),.062,inscription)
    scene['source_credit'] = SOURCE_CREDIT
    scene['pedestal_authorship'] = root['pedestal_author']
    scene['historic_reliefs_replicated'] = False
    notes = bpy.data.texts.new('FLORENCE_SOURCE_AND_LICENSE.txt')
    notes.write(SOURCE_CREDIT + '\nhttps://creativecommons.org/licenses/by-nc-sa/4.0/\n'
                'The new pedestal and ornaments adapt the supplied visual references.\n'
                'The historical bas-relief figures are not reconstructed.\n'
                'Original user photographs and provider GLB are preserved unchanged.\n')
    mesh_objects = [obj for obj in collection.objects if obj.type=='MESH']
    # Embed texture data in the .blend. External original scan remains untouched.
    for image in bpy.data.images:
        if image.type != 'RENDER_RESULT' and image.has_data:
            try: image.pack()
            except RuntimeError: pass
    for path in (BLEND,GLB,REPORT):
        path.parent.mkdir(parents=True,exist_ok=True)
    select_only([root] + mesh_objects)
    log('Exporting selected monument as a single-scene GLB')
    status = bpy.ops.export_scene.gltf(filepath=str(GLB), export_format='GLB',
      use_selection=True, export_yup=True, export_apply=True, export_animations=False,
      export_cameras=False, export_lights=False, export_extras=True,
      export_materials='EXPORT',export_texcoords=True,export_normals=True,
      export_draco_mesh_compression_enable=False)
    if status!={'FINISHED'} or not GLB.is_file():
        raise RuntimeError('Monument GLB was not exported')
    exported = GLB.read_bytes()
    _,version,length = struct.unpack_from('<4sII',exported)
    json_length,_ = struct.unpack_from('<II',exported,12)
    doc = json.loads(exported[20:20+json_length].rstrip(b'\x00 \t\r\n'))
    if len(doc.get('scenes',[])) != 1 or 'KHR_draco_mesh_compression' in doc.get('extensionsRequired',[]):
        raise RuntimeError('Expected one GLB scene with no Draco runtime requirement')
    if not all('bufferView' in image for image in doc.get('images',[])):
        raise RuntimeError('Expected embedded images')
    original_mesh_count = len(mesh_objects)
    original_material_count = len(set(mat for obj in mesh_objects for mat in obj.data.materials))
    # Dedicated rendering additions are excluded from the exported asset selection.
    floor = box('REVIEW_Floor',(18,18,.05),(0,0,-.03),material('MAT_Review_Floor',(.095,.105,.112),0,.8),0)
    floor.parent = None
    review_collection = bpy.data.collections.new('PREP_FLORENCE_REVIEW_COLLECTION')
    scene.collection.children.link(review_collection)
    collection.objects.unlink(floor)
    review_collection.objects.link(floor)
    world = bpy.data.worlds.new('Florence_Review_World')
    world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.20,.25,.32,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.75
    scene.world = world
    for name,position,energy,size in (
      ('Key',(4,-5,9),1300,5),('Fill',(-4,-2,5),900,4),('Rim',(3,4,8),1800,4)):
        light_data = bpy.data.lights.new('REVIEW_'+name,'AREA')
        light_data.energy = energy
        light_data.shape = 'DISK'
        light_data.size = size
        light_obj = bpy.data.objects.new('REVIEW_'+name,light_data)
        scene.collection.objects.link(light_obj)
        light_obj.location = position
        light_obj.rotation_euler = (Vector((0,0,3.6))-light_obj.location).to_track_quat('-Z','Y').to_euler()
    front = camera_at('REVIEW_Camera_Front',(8,-12,7.3),(0,0,3.3))
    reverse = camera_at('REVIEW_Camera_Reverse',(-8,12,7.3),(0,0,3.3))
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=8
    scene.cycles.use_denoising=True
    scene.render.resolution_x=768
    scene.render.resolution_y=1024
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    # Save first so the real scanned figure and packed materials are safe before renders.
    scene.camera=front
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log('Saved standalone blend checkpoint')
    render_view(RENDER_FRONT,front)
    render_view(RENDER_REVERSE,reverse)
    # Actual reimport in a clean secondary scene tests the generated asset geometry.
    validation = bpy.data.scenes.new('VALIDATE_FLORENCE_GLB')
    bpy.context.window.scene=validation
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    reimported=[obj for obj in bpy.data.objects if obj not in before]
    reimported_meshes=[obj for obj in reimported if obj.type=='MESH']
    lo,hi=world_bounds(reimported_meshes)
    finite = all(math.isfinite(value) for obj in reimported_meshes for vertex in obj.data.vertices for value in vertex.co)
    if not finite or len(reimported_meshes)<10 or abs(lo.z)>0.005 or abs(hi.z-6.6)>0.005:
        raise RuntimeError('Reimported monument failed bounds or finite geometry checks')
    result={
      'date':'2026-10-05', 'assetId':ASSET_NAME, 'blenderVersion':bpy.app.version_string,
      'source':{'path':str(SOURCE),'sha256':SOURCE_SHA,'sha256StillMatches':sha(SOURCE)==SOURCE_SHA,
        'record':'https://zenodo.org/records/21163474','creator':'Scan-the-World',
        'license':'CC-BY-NC-SA-4.0','licenseUrl':'https://creativecommons.org/licenses/by-nc-sa/4.0/',
        'credit':SOURCE_CREDIT,'preserved':True,'sourceBoundsBlenderXYZ':original_bounds},
      'originalGeometryUsed':True,'figureHeightMeters':3.4,'pedestalHeightMeters':3.2,
      'historicBasReliefsReconstructed':False,'ornaments':'Original bronze botanical scrolls; historical reliefs are not replicated.',
      'authorship':'Pedestal adaptation: Romario Vicente Amaro — Projeto PREPARATÓRIO. Figure scan: Scan-the-World.',
      'created':{'objects':original_mesh_count,'figureMeshes':len(derived),'materials':original_material_count,
        'text':'Florence Nightingale; 1820 — 1910; Pioneira da enfermagem moderna; PREPARATÓRIO · Romario Vicente Amaro'},
      'blend':{'path':str(BLEND),'bytes':BLEND.stat().st_size,'sha256':sha(BLEND)},
      'glb':{'path':str(GLB),'url':'/assets/monuments/'+GLB.name,'bytes':len(exported),'sha256':sha(GLB),
        'version':version,'headerLengthMatches':length==len(exported),'scenes':len(doc.get('scenes',[])),
        'nodes':len(doc.get('nodes',[])),'meshes':len(doc.get('meshes',[])),
        'materials':len(doc.get('materials',[])),'embeddedImages':len(doc.get('images',[])),
        'dracoRequired':False},
      'actualGlbReimport':{'passed':True,'meshes':len(reimported_meshes),
        'materials':len(set(mat for obj in reimported_meshes for mat in obj.data.materials)),
        'vertices':sum(len(obj.data.vertices) for obj in reimported_meshes),
        'triangles':sum(len(poly.vertices)-2 for obj in reimported_meshes for poly in obj.data.polygons),
        'boundsMinBlenderXYZ':list(lo),'boundsMaxBlenderXYZ':list(hi),
        'dimensionsBlenderXYZ':list(hi-lo),'allVerticesFinite':finite},
      'render':{'front':str(RENDER_FRONT),'reverse':str(RENDER_REVERSE),
        'resolution':[768,1024],'engine':'Cycles CPU','samples':8,'visualReviewPending':True},
      'frontendConfigModified':False,'liveBlenderModified':False,
    }
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log('Validation report saved: '+str(REPORT))
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
