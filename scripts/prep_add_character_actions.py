"""Add genuine Dance/Interact skin animations, keeping earlier rig GLBs intact."""
import bpy,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
reports=ROOT/'reports/rigs';records=[json.loads(p.read_text(encoding='utf-8')) for p in reports.glob('*.json')]
for r in records:
 if 'Dance' in r.get('clips',[]):continue
 scene=bpy.data.scenes.new('ACTIONS_'+r['id'][4:]);bpy.context.window.scene=scene
 scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene.render.fps=30
 bpy.ops.import_scene.gltf(filepath=str(ROOT/'frontend/public'/r['url'].lstrip('/')));bpy.context.view_layer.update()
 arm=next(o for o in scene.objects if o.type=='ARMATURE');meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
 original_tracks=list(arm.animation_data.nla_tracks)
 for t in original_tracks:t.mute=True
 arm.animation_data.action=None;made={}
 for clip,frames in [('Dance',64),('Interact',32)]:
  action=bpy.data.actions.new(r['id']+'_'+clip);arm.animation_data.action=action
  for f in range(1,frames+2,8):
   phase=(f-1)/frames*2*math.pi;limited=r.get('needsRepose',False)
   for b in arm.pose.bones:b.rotation_mode='XYZ';b.matrix_basis=Matrix.Identity(4)
   if clip=='Dance':
    arm.pose.bones['spine'].rotation_euler.z=.07*math.sin(phase)
    arm.pose.bones['chest'].rotation_euler.y=.09*math.sin(phase)
    arm.pose.bones['head'].rotation_euler.y=.12*math.cos(phase)
    for side,sign in [('L',1),('R',-1)]:
     arm.pose.bones[side+'_upper_arm'].rotation_euler.x=(.08 if limited else .28)*math.sin(phase+sign)
     arm.pose.bones[side+'_forearm'].rotation_euler.x=(.10 if limited else .35)*math.sin(phase+sign)
     if not limited:arm.pose.bones[side+'_thigh'].rotation_euler.x=.13*math.sin(phase+sign*math.pi/2)
   else:
    reach=math.sin((f-1)/frames*math.pi)**2
    for side in ['L','R']:
     arm.pose.bones[side+'_upper_arm'].rotation_euler.x=-(.1 if limited else .65)*reach
     arm.pose.bones[side+'_forearm'].rotation_euler.x=-(.08 if limited else .45)*reach
   for b in arm.pose.bones:b.keyframe_insert(data_path='rotation_euler',frame=f,group=b.name)
  made[clip]=action;arm.animation_data.action=None
  t=arm.animation_data.nla_tracks.new();t.name=clip;t.strips.new(clip,1,action)
 # Export separate NLA actions, not an accidental combination of all clips.
 for t in arm.animation_data.nla_tracks:t.mute=False
 bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
 for o in meshes:o.select_set(True)
 bpy.context.view_layer.objects.active=arm
 dest=ROOT/'frontend/public/assets/characters'/('CHR_'+r['id'][4:]+'_Actions_v3.glb');assert not dest.exists()
 bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,use_active_scene=True,export_animation_mode='NLA_TRACKS',export_animations=True,export_skins=True,export_cameras=False,export_lights=False,export_image_format='AUTO')
 raw=dest.read_bytes();doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]]);clips=[a.get('name') for a in doc.get('animations',[])]
 assert 'Dance'in clips and 'Interact'in clips and doc.get('skins'),clips
 check=bpy.data.scenes.new('VALIDATE_ACTIONS_'+r['id']);bpy.context.window.scene=check;bpy.ops.import_scene.gltf(filepath=str(dest))
 bones=next(o for o in check.objects if o.type=='ARMATURE');skin=[o for o in check.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)];assert skin and all(v.groups for o in skin for v in o.data.vertices)
 bpy.context.window.scene=scene
 for t in arm.animation_data.nla_tracks:t.mute=True
 arm.animation_data.action=made['Dance'];scene.frame_set(9);bpy.context.view_layer.update()
 assert all(math.isfinite(c) for o in meshes for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices for c in v.co)
 scene.world=bpy.data.worlds.new(scene.name+'_World');scene.world.color=(.4,.4,.4)
 bpy.ops.object.light_add(type='AREA',location=(0,-3,4));bpy.context.object.data.energy=450;bpy.context.object.data.size=5
 bpy.ops.object.camera_add(location=(2.5,-5,2));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.3;scene.camera=cam
 scene.render.engine='CYCLES';scene.cycles.samples=4;scene.render.resolution_x=400;scene.render.resolution_y=400;scene.render.resolution_percentage=100;scene.render.filepath=str(reports/(r['id'][4:]+'_dance.png'));bpy.ops.render.render(write_still=True)
 r.update(url='/assets/characters/'+dest.name,clips=clips,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),actionsReimportValidated=True,notes=r['notes']+' Dance and Interact are procedural prototype clips; limited-pose rigs use smaller upper-body motion.')
 (reports/(r['id'][4:]+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 scene['source_id']=r['id'];scene['animation_notes']=r['notes']
 print(r['id'],clips)
records=[json.loads(p.read_text(encoding='utf-8')) for p in reports.glob('*.json')]
(ROOT/'frontend/src/config/riggedAssets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/checkpoints/RIGS_ACTIONS_20261002.blend'),compress=True,copy=True)
print('Saved',len(records),'rigs with actions')
