"""Render the five delivered PBR-compatible animals, preserving old previews."""
import bpy,hashlib,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
path=ROOT/'reports/fauna_catalog_entries_20261016.json';records=json.loads(path.read_text(encoding='utf-8'))
report=[]
for record in records:
    if record['id']=='FAUNA_MEGALODON_20261016':continue
    assert record['status']=='validated' and record['materialQA']['passed']
    scene=bpy.data.scenes[record['materialQAScene']]
    for w in bpy.context.window_manager.windows:w.scene=scene
    scene.frame_set(1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[]
    for obj in scene.objects:
        if obj.type!='MESH' or any(c.name.startswith('glTF_not_exported') for c in obj.users_collection):continue
        ev=obj.evaluated_get(dg);mesh=ev.to_mesh();used={i for p in mesh.polygons for i in p.vertices}
        points.extend(ev.matrix_world@mesh.vertices[i].co for i in used);ev.to_mesh_clear()
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=(lo+hi)*.5;span=max(hi-lo)
    studio=bpy.data.collections.new('STUDIO_PBR_'+record['id']);scene.collection.children.link(studio)
    data=bpy.data.cameras.new('CAM_PBR_'+record['id']);cam=bpy.data.objects.new(data.name,data);studio.objects.link(cam)
    cam.location=center+Vector((1.45,-1.6,.75))*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=span*1.3;data.clip_end=max(1000,span*10);scene.camera=cam
    for name,offset,power,color in [('Key',(1,-1.2,2),190,(1,.94,.88)),('Fill',(-1,-.4,.7),100,(.8,.9,1)),('Rim',(0,1.2,1.5),180,(1,1,1))]:
        lightdata=bpy.data.lights.new('LIGHT_PBR_'+record['id']+name,'AREA');obj=bpy.data.objects.new(lightdata.name,lightdata);studio.objects.link(obj)
        obj.location=center+Vector(offset)*span;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler();lightdata.energy=power*span*span;lightdata.size=span*1.5;lightdata.color=color
    world=bpy.data.worlds.new('WORLD_PBR_'+record['id']);world.use_nodes=True;scene.world=world
    bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.07,.095,.13,1);bg.inputs['Strength'].default_value=.5
    scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
    scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='JPEG'
    target=ROOT/'frontend/public/assets/additions20261016'/(record['id']+'_PBR.jpg')
    assert not target.exists(),'Preserve an existing preview before rendering again.'
    scene.render.filepath=str(target);bpy.ops.render.render(write_still=True);assert target.exists()
    record['previewBeforeMaterialAdaptation']=record['preview']
    record['preview']='/assets/additions20261016/'+target.name
    record['previewSha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    record['materialQA']['actualPBRRender']=record['preview']
    report.append({'id':record['id'],'preview':str(target),'sha256':record['previewSha256'],'actualDeliveredMaterialRender':True})
assert len(report)==5
path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'reports/FAUNA_PBR_PREVIEWS_20261016.json').write_text(json.dumps({'status':'passed','assets':report},indent=2),encoding='utf-8')
print('PREP_FAUNA_PBR_PREVIEWS '+str(len(report)))
