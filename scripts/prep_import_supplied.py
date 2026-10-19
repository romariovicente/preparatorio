"""Run with Blender --background --factory-startup --python this.py -- manifest-index.

Each isolated Blender process derives one asset; originals and open Blender are untouched.
Static meshes are combined and reduced. Skinned/animated assets retain their hierarchy.
"""
import bpy, json, sys, math, hashlib, traceback, struct
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
entries = json.loads((ROOT/'reports/supplied_assets_inventory.json').read_text(encoding='utf-8'))
index = int(sys.argv[sys.argv.index('--')+1])
entry = entries[index]
key = 'SUP_' + Path(entry['relative']).stem.strip().replace(' ', '_').replace('-', '_')
out = ROOT/'frontend/public/assets/supplied'
out.mkdir(parents=True, exist_ok=True)
report_path = ROOT/'reports/supplied'/f'{key}.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
dest = out/f'{key}.glb'
assert not dest.exists(), f'Output exists; inspect before replacing: {dest}'
category = ('Personagens' if entry['relative'].startswith('Personagens') else
            'Anatomia' if entry['relative'].startswith(('Anatomia','Esqueleto')) else
            'Equipamentos' if entry['relative'].startswith('Itens') else 'Veículos' if entry['relative'].startswith(('Veiculos','Caminhões','Motocicletas','Tank')) else
            'Naves' if entry['relative'].startswith('Naves') else 'Cenários' if entry['relative'].startswith('Mapa') else 'Edifícios')
record = {'id':key, 'category':category, 'sourceRelative':entry['relative'],
          'sourceSha256':entry['sha256'], 'originalTriangles':entry['triangles'],
          'credits':entry['asset'].get('extras', {}), 'status':'processing'}
report_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    existing_images=set(bpy.data.images)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.context.scene.name = 'PREP_'+key
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    if entry.get('format')=='obj':
        for objfile in entry['objFiles']:
            if Path(objfile).name in entry.get('skipParts',[]):continue
            oldobjs=set(bpy.context.scene.objects);bpy.ops.wm.obj_import(filepath=objfile)
            for part in set(bpy.context.scene.objects)-oldobjs:part['obj_source_part']=Path(objfile).name
        palette=[(.10,.34,.46,1),(.8,.46,.15,1),(.18,.22,.28,1),(.68,.73,.75,1),(.24,.46,.35,1)]
        folder=Path(entry['path']).parent
        candidates=[f for f in folder.glob('*.png') if any(t in f.stem.lower() for t in ['diffuse','basecolor','albedo']) and 'ao' not in f.stem.lower()]
        for j,obj in enumerate(o for o in bpy.context.scene.objects if o.type=='MESH'):
            mat=bpy.data.materials.new('PREP_OBJ_'+str(j));mat.use_nodes=True;mat.diffuse_color=palette[j%len(palette)]
            bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Base Color'].default_value=mat.diffuse_color;bsdf.inputs['Roughness'].default_value=.48
            chosen=folder/entry['textureOverrides'][obj['obj_source_part']] if obj.get('obj_source_part') in entry.get('textureOverrides',{}) else candidates[0] if len(candidates)==1 else None
            if chosen:
                tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(chosen),check_existing=True);mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
            obj.data.materials.clear();obj.data.materials.append(mat)
        record['materialRecovery']='Part-level albedo association for Ferra; presentation planes excluded; missing MTL still requires artistic review' if entry.get('textureOverrides') else 'Single unambiguous albedo applied' if len(candidates)==1 else 'MTL absent: provisional category palette; original texture association unresolved'
    else:bpy.ops.import_scene.gltf(filepath=entry['path'])
    bpy.context.view_layer.update()
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
    animated=bool(entry['skins'] or entry['animations'])
    if not animated:
        # Preserve world placement when detaching only these freshly imported static objects.
        for obj in meshes:
            matrix=obj.matrix_world.copy(); obj.parent=None; obj.matrix_world=matrix
        bpy.data.batch_remove(ids=[obj for obj in bpy.context.scene.objects if obj.type!='MESH'])
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:obj.select_set(True)
        bpy.context.view_layer.objects.active=meshes[0]
        bpy.ops.object.join()
        obj=bpy.context.object; obj.name=key
        tris=sum(len(p.vertices)-2 for p in obj.data.polygons)
        budget=45000 if category=='Personagens' else 160000
        if tris>budget:
            mod=obj.modifiers.new('PREP_Web_Reduction','DECIMATE')
            mod.ratio=budget/tris; mod.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        # Only standalone static derivative; rigs never enter this branch.
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        meshes=[obj]
    for image in set(bpy.data.images)-existing_images:
        if image.type=='IMAGE' and image.size[0] and image.users:
            width,height=image.size
            factor=min(1,1024/max(width,height))
            if factor<1:image.scale(max(1,round(width*factor)),max(1,round(height*factor)))
            image.pack()
    bpy.ops.object.select_all(action='SELECT')
    prepared_triangles=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
    bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,
        use_active_scene=True,export_yup=True,export_animations=animated,export_skins=True,
        export_cameras=False,export_lights=False,export_extras=True,
        export_image_format='JPEG',export_jpeg_quality=85)
    # Compare the actual exported triangle primitives: the exporter can discard
    # degenerates and triangulate evaluated modifiers differently from the base mesh.
    with dest.open('rb') as stream:
        header=stream.read(20); document=json.loads(stream.read(struct.unpack_from('<I',header,12)[0]))
    primitive_counts=[sum(document['accessors'][p['indices']]['count']//3 for p in m['primitives'] if p.get('mode',4)==4) for m in document['meshes']]
    def node_triangles(index):
        node=document['nodes'][index]
        return (primitive_counts[node['mesh']] if 'mesh' in node else 0)+sum(node_triangles(child) for child in node.get('children',[]))
    expected_triangles=sum(node_triangles(index) for index in document['scenes'][document.get('scene',0)]['nodes'])
    if entry['skins']:assert document.get('skins'),'Rig export lost'
    if entry['animations']:assert document.get('animations'),'Animation export lost'
    # Reimport exactly the delivered bytes into a clean scene.
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(dest))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
    triangles=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
    assert triangles==expected_triangles,(triangles,expected_triangles)
    assert meshes and all(math.isfinite(v) for o in meshes for p in o.data.vertices for v in p.co)
    if entry['skins']:assert any(o.type=='ARMATURE' for o in bpy.context.scene.objects),'Rig lost'
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    low=Vector([min(p[i] for p in points) for i in range(3)])
    high=Vector([max(p[i] for p in points) for i in range(3)])
    size=high-low; center=(high+low)/2
    record.update(status='validated',url='/assets/supplied/'+dest.name,triangles=triangles,
        bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
        meshes=len(meshes),dimensions=list(size),animated=animated,preparedTriangles=prepared_triangles,meshPrimitiveTriangles=sum(primitive_counts),
        animations=entry['animations'],modifications='Static mesh batching/reduction where applicable; textures capped at 1024 px; JPEG export. Original pose/rig retained.',
        validation='Blender reimport; finite vertices; matching triangle count; rig check when present')
    # Preview depicts the actual reimported model, never a generated substitute.
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=8
    scene.render.resolution_x=480;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.world.color=(.35,.35,.35)
    span=max(size); bpy.ops.object.camera_add(location=center+Vector((1.25,-1.8,.9))*span)
    cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=span*1.4;cam.data.clip_end=max(1000,span*10);scene.camera=cam
    bpy.ops.object.light_add(type='AREA',location=center+Vector((0,-1,2))*span)
    bpy.context.object.data.energy=1000*span*span;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=span*3
    bpy.context.object.rotation_euler=(center-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
    preview=out/f'{key}.jpg';scene.render.image_settings.file_format='JPEG';scene.render.filepath=str(preview)
    bpy.ops.render.render(write_still=True)
    record['preview']='/assets/supplied/'+preview.name
except Exception:
    record.update(status='failed',error=traceback.format_exc())
    raise
finally:
    report_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
