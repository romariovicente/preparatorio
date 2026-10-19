"""Validate the material-compatible GLBs without re-exporting any skin."""
import bpy,contextlib,hashlib,io,json,math,struct,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
REPORT=ROOT/'reports/fauna_catalog_entries_20261016.json'
records=json.loads(REPORT.read_text(encoding='utf-8'))
compat=json.loads((ROOT/'reports/FAUNA_MATERIAL_COMPAT_20261016.json').read_text(encoding='utf-8'))
assert len(records)==6
prior=list(bpy.data.objects);before=state_hash(object_state(prior));results=[]

def positions(objects):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[]
    for obj in objects:
        if obj.type!='MESH':continue
        ev=obj.evaluated_get(dg);mesh=ev.to_mesh();used={i for p in mesh.polygons for i in p.vertices}
        points.extend(ev.matrix_world@mesh.vertices[i].co for i in used);ev.to_mesh_clear()
    assert points and all(math.isfinite(v) for p in points for v in p)
    return points

for record in records:
    if record['id']=='FAUNA_MEGALODON_20261016':continue
    assert record['status']=='pending-material-qa',record['id']
    path=ROOT/'frontend/public'/record['url'].lstrip('/')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
    raw=path.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size])
    assert 'KHR_materials_pbrSpecularGlossiness' not in doc.get('extensionsRequired',[])
    assert all(m.get('pbrMetallicRoughness',{}).get('baseColorTexture') is not None for m in doc['materials'])
    code=record['id'].split('_')[1];name='PREP_FAUNA_PBR_QA_'+code+'_20261016'
    assert name not in bpy.data.scenes,'Inspect partial material QA before retrying: '+name
    scene=bpy.data.scenes.new(name);scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=30
    scene['purpose']='Actual runtime GLB with compatible PBR material metadata and unchanged binary skins/animations.'
    for window in bpy.context.window_manager.windows:window.scene=scene
    old=set(bpy.data.objects);capture=io.StringIO()
    with contextlib.redirect_stdout(capture):
        assert 'FINISHED' in bpy.ops.import_scene.gltf(filepath=str(path))
    fresh=[o for o in set(bpy.data.objects)-old if not any(c.name.startswith('glTF_not_exported') for c in o.users_collection)]
    root=bpy.data.objects.new('PBR_QA_ROOT_'+code,None);scene.collection.objects.link(root)
    for obj in fresh:
        if obj.parent is None:obj.parent=root
        ad=obj.animation_data
        if ad and any(t.name==record['referenceClip'] for t in ad.nla_tracks):
            ad.action=None
            for track in ad.nla_tracks:track.mute=track.name!=record['referenceClip']
    # Failed trials are preserved, so Blender may suffix the successful root.
    roots=[o for o in bpy.data.scenes[record['blenderScene']].objects
           if o.name.startswith('ROOT_'+record['id']) and o.parent is None]
    assert len(roots)==1
    reference_root=roots[0]
    root.location=reference_root.location;root.scale=reference_root.scale
    scene.frame_set(1)
    meshes=[o for o in fresh if o.type=='MESH'];arms=[o for o in fresh if o.type=='ARMATURE']
    assert [len(o.data.bones) for o in arms]==record['boneCounts']
    triangles=0
    for obj in meshes:obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    assert triangles==record['triangles']
    p=positions(meshes);lo=Vector([min(v[i] for v in p) for i in range(3)]);hi=Vector([max(v[i] for v in p) for i in range(3)])
    assert max(abs(a-b) for a,b in zip(hi-lo,record['dimensions']))<max(record['dimensions'])*.001+.0001
    materials={m for obj in meshes for m in obj.data.materials if m};maps=[]
    for material in materials:
        assert material.use_nodes
        bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        links=list(bsdf.inputs['Base Color'].links)
        assert links,'Missing actual base-color image link: '+material.name
        images=[n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        assert images and all(min(image.size)>0 for image in images)
        maps.append({'material':material.name,'images':[{'name':i.name,'size':list(i.size)} for i in images]})
    record['status']='validated';record['reimportValidated']=True;record['materialQAScene']=scene.name
    record['materialQA']={'passed':True,'matchingBonesAndTriangles':True,'matchingReferencePoseBounds':True,
        'actualBaseColorImageLinks':len(maps),'materials':maps,'noSkinReexport':True}
    results.append({'id':record['id'],'scene':scene.name,**record['materialQA']})
    (ROOT/('reports/fauna_pbr_'+code.lower()+'_20261016.log')).write_text(capture.getvalue(),encoding='utf-8')
assert len(results)==5
assert state_hash(object_state(prior))==before,'An earlier stored object channel changed.'
REPORT.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/FAUNA_MATERIAL_BLENDER_QA_20261016.json').write_text(json.dumps({'status':'passed','assets':results,
    'previousObjectChannelsMatch':True,'masterSaved':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('PREP_FAUNA_MATERIAL_QA '+json.dumps({'assets':len(results),'status':'passed','newSceneCount':5}))
