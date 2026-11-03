"""Render matched contextual before/after views without saving the library."""
import bpy,json,hashlib,runpy,numpy as np,traceback
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];r=json.loads((ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_20261027.json').read_text());p=Path(r['library']);F=ROOT/'reports/thai_cap_refit_v20_20261027'
STATUS=ROOT/'work/v20_headless_render_status_20261027.json';OUT=ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_RENDERS_20261027.json';assert not STATUS.exists()and not OUT.exists()
try:
 assert bpy.app.background and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'];bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
 scene=bpy.data.scenes[r['scene']];bpy.context.window.scene=scene;bpy.context.view_layer.update();body=bpy.data.objects[r['bodyObject']];reference=bpy.data.objects[r['referenceObject']];reference.hide_set(False)
 camera=scene.camera;camera.data.type='ORTHO';scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100;scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.render.threads_mode='FIXED';scene.render.threads=2
 def points(o):
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
 q=points(reference);ref_tri=np.array([list(f.vertices)for f in reference.data.polygons],np.int32);cap=ref_tri[np.arange(42674,42679)];center=Vector(q[np.unique(cap)].mean(0));cap_tri=q[cap];normal=np.cross(cap_tri[:,1]-cap_tri[:,0],cap_tri[:,2]-cap_tri[:,0]).sum(0);normal/=np.linalg.norm(normal);cap_offset=Vector(normal)*2
 torso=Vector((0,0,1.32));full=Vector((0,0,.85))
 views=[('front',torso,Vector((0,-3,0)),.86,(512,640)),('back',torso,Vector((0,3,0)),.86,(512,640)),('right',torso,Vector((-3,0,0)),.86,(512,640)),('cap_closeup',center,cap_offset,.065,(640,640))]
 failures=[];images=[];used_engine=None
 for engine,folder in[('BLENDER_EEVEE','renders_eevee'),('CYCLES','renders_cycles')]:
  directory=F/folder;assert not directory.exists();directory.mkdir();attempt=[]
  try:
   scene.render.engine=engine
   if engine=='CYCLES':
    scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.max_bounces=4
   elif hasattr(scene,'eevee')and hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=32
   for name,target,offset,scale,resolution in views:
    camera.data.ortho_scale=scale;camera.location=target+offset;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.resolution_x,scene.render.resolution_y=resolution
    for state in('before','after'):
     body.hide_render=state=='before';reference.hide_render=state!='before';path=directory/(name+'_'+state+'.png');assert not path.exists();scene.render.filepath=str(path)
     (ROOT/'work/v20_render_progress_20261027.json').write_text(json.dumps({'engine':engine,'view':name,'state':state,'output':str(path)}))
     bpy.ops.render.render(write_still=True);attempt.append({'view':name,'state':state,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
   camera.data.ortho_scale=1.85;camera.location=full+Vector((0,-3,0));camera.rotation_euler=(full-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.resolution_x=512;scene.render.resolution_y=768;body.hide_render=False;reference.hide_render=True;path=directory/'full_body_after.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);attempt.append({'view':'full_body','state':'after','path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
   images=attempt;used_engine=engine;break
  except Exception as error:failures.append({'engine':engine,'error':str(error),'traceback':traceback.format_exc()})
 assert used_engine and len(images)==9,failures
 body.hide_render=False;reference.hide_render=True;reference.hide_set(True)
 h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));arrays=h['_snapshot'](body.data)['arrays'];assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in arrays.items()}==r['bodyArraysSha256']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 record={'status':'nine-matched-contextual-images-rendered-awaiting-visual-review','library':str(p),'librarySha256':r['sha256'],'engine':used_engine,'scene':scene.name,'images':images,'failedEngineAttempts':failures,'sameCameraLightsMaterialsAndStandingPosePerPair':True,'bodyArraysUnchanged':True,'libraryNotSavedOrChanged':True,'sourceAndRuntimeNotEdited':True,'visibleWindowOpened':False,'desktopSwitched':False,'limit':'Matched local before/after renders show only this cap fitting and its shading change. They do not approve full garment, anatomy or native Walk.'}
 OUT.write_text(json.dumps(record,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps(record))
except BaseException as error:
 STATUS.write_text(json.dumps({'status':'error','error':str(error),'traceback':traceback.format_exc()},indent=2));raise
