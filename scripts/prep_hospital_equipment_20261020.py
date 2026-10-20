import bpy,json,sys,hashlib,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_incremental_scene_tools_20261020 import save_scene_library,sha256
checkpoint=json.loads((ROOT/'reports/EVENING_ADDITIONS_CHECKPOINT_20261020.json').read_text())
assert Path(checkpoint['checkpoint']).is_file()
assert 'PREP_HOSPITAL_EQUIPMENT_20261020' not in bpy.data.scenes
review=bpy.data.scenes['PREP_THERMOMETER_REVIEW_20261020'];source=bpy.data.objects['THM20_ROOT']
asset=bpy.data.scenes.new('PREP_AMBIENT_MONITOR_ASSET_20261020');asset.unit_settings.system='METRIC'
for w in bpy.context.window_manager.windows:w.scene=asset
col=bpy.data.collections.new('AMBIENT20_ASSET');asset.collection.children.link(col)
sources=[source]+list(source.children_recursive);mapped={};materials={};images={}
texdir=ROOT/'art/source/hospital_equipment_20261020/runtime_textures';texdir.mkdir(parents=True,exist_ok=True)
for i,obj in enumerate(sources):
    copy=obj.copy();copy.name='AMBIENT20_'+str(i).zfill(2)
    if obj.type=='MESH':
        copy.data=obj.data.copy()
        for index,mat in enumerate(list(copy.data.materials)):
            if mat not in materials:
                material=mat.copy();material.name='AMBIENT20_'+mat.name
                if material.use_nodes:
                    for node in material.node_tree.nodes:
                        if node.type!='TEX_IMAGE' or not node.image:continue
                        old=node.image
                        if old not in images:
                            image=old.copy();image.name='AMBIENT20_'+old.name;factor=min(1,1024/max(image.size));image.scale(max(1,round(image.size[0]*factor)),max(1,round(image.size[1]*factor)))
                            image.file_format='PNG';image.filepath_raw=str(texdir/(str(len(images)).zfill(2)+'.png'));image.save();image.pack();images[old]=image
                        node.image=images[old]
                materials[mat]=material
            copy.data.materials[index]=materials[mat]
    col.objects.link(copy);mapped[obj]=copy
for obj,copy in mapped.items():
    copy.parent=mapped.get(obj.parent);copy.matrix_parent_inverse=obj.matrix_parent_inverse.copy();copy.matrix_basis=obj.matrix_basis.copy()
root=mapped[source]
credits={'author':'SeitVerivel (https://sketchfab.com/SeitVerivel)','license':'CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)','source':'https://sketchfab.com/3d-models/thermometer-e72a392f9fa94fbba0ed8356f29b5cec','title':'Thermometer'}
root['attribution_author']=credits['author'];root['attribution_license']=credits['license'];root['attribution_source']=credits['source'];root['static_display_not_live_measurement']=True
bpy.context.view_layer.update();parts=[o for o in mapped.values() if o.type=='MESH'];points=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box]
lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
assert abs(lo.z)<1e-5 and .14<hi.z<.15
triangles=0
for o in parts:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
assert triangles==13002
out=ROOT/'frontend/public/assets/additions20261020/PROP_Ambient_Monitor_20261020.glb';out.parent.mkdir(parents=True,exist_ok=True)
for o in asset.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_active_scene=True,use_selection=True,export_animations=False,export_extras=True,export_image_format='JPEG',export_jpeg_quality=92)
plan={'id':'PROP_Ambient_Monitor_20261020','label':'Monitor de temperatura e umidade','ready':True,'asset':'/assets/additions20261020/'+out.name,'localPosition':[-6.6,1.112,6.0],'localRotation':[0,0,0],'worldPosition':[41.4,1.372,-32.0],'worldLabel':[41.4,1.66,-32.0],'height':hi.z-lo.z,'dimensions':[hi.x-lo.x,hi.z-lo.z,hi.y-lo.y],'loadRadius':16,'labelRadius':3.4,'triangles':triangles,'bytes':out.stat().st_size,'sha256':sha256(out),'sourceSha256':sha256(ROOT/'art/source/hospital_equipment_20261020/Thermometer_Original.glb'),'credits':credits,'notice':'Este monitor é uma peça de demonstração. Os números do visor fazem parte da imagem do modelo; ainda não medem o ambiente do jogo.','liveMeasurement':False}
(ROOT/'frontend/src/config/hospitalEquipment.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
lib=save_scene_library(asset,ROOT/'art/blender/PREPARATORIO_AMBIENT_MONITOR_ASSET_20261020.blend')
# Keep the complete prior hospital scene intact. Collection links do not change
# original object's collection ownership, rig or door animation channels.
hospital=bpy.data.scenes.new('PREP_HOSPITAL_EQUIPMENT_20261020');hospital.unit_settings.system='METRIC';hospital.unit_settings.scale_length=1
prior=bpy.data.scenes['PREP_HOSPITAL_CHAIRS_CITY_20261020']
for c in prior.collection.children:hospital.collection.children.link(c)
equipment=bpy.data.collections.new('AMBIENT20_HOSPITAL_EQUIPMENT');hospital.collection.children.link(equipment)
instance=bpy.data.objects.new('AMBIENT20_COUNTER_MONITOR',None);equipment.objects.link(instance);instance.instance_type='COLLECTION';instance.instance_collection=col;instance.location=(41.4,32.0,1.372)
hospital.world=prior.world;hospital.camera=prior.camera
hospital.render.engine='BLENDER_EEVEE';hospital.render.resolution_x=1440;hospital.render.resolution_y=960;hospital.render.resolution_percentage=100;hospital.render.image_settings.file_format='PNG';hospital.view_settings.view_transform='AgX'
studio=bpy.data.collections.new('AMBIENT20_DETAILS');hospital.collection.children.link(studio)
data=bpy.data.cameras.new('AMBIENT20_DETAIL_CAMERA');cam=bpy.data.objects.new(data.name,data);studio.objects.link(cam);cam.location=(42.0,30.65,1.8);target=Vector((41.4,32,1.43));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=58;data.clip_start=.001;hospital.camera=cam
for w in bpy.context.window_manager.windows:w.scene=hospital
citylib=save_scene_library(hospital,ROOT/'art/blender/PREPARATORIO_HOSPITAL_EQUIPMENT_20261020.blend')
preview=ROOT/'reports/hospital_ambient_monitor_20261020.png';hospital.render.filepath=str(preview)
report={'checkpoint':checkpoint['checkpoint'],'asset':plan,'assetLibrary':lib,'hospitalLibrary':citylib,'sourcePreviewIdentifiedAsAmbientThermohygrometer':True,'meshGeometryNotDecimated':True,'staticSourceDigitsPreserved':True,'clinicalTemperatureReadingImplemented':False,'originalHospitalScenesPreserved':True,'masterSaved':False,'preview':str(preview)}
(ROOT/'reports/HOSPITAL_EQUIPMENT_BLENDER_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.render.render(write_still=True)
print(json.dumps({'assetBytes':out.stat().st_size,'triangles':triangles,'preview':str(preview)}))
