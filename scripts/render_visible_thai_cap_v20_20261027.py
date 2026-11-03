"""Find a naturally unoccluded matched cap view using the complete body BVH."""
import bpy,json,hashlib,traceback,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from math import radians,sqrt,pi,cos,sin
ROOT=Path(__file__).resolve().parents[1];r=json.loads((ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_20261027.json').read_text());p=Path(r['library']);F=ROOT/'reports/thai_cap_refit_v20_20261027'
OUT=ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_VISIBLE_RENDERS_20261027.json';STATUS=ROOT/'work/v20_visible_render_status_20261027.json';assert not OUT.exists()and not STATUS.exists()
try:
 assert bpy.app.background and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'];bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
 scene=bpy.data.scenes[r['scene']];bpy.context.window.scene=scene;bpy.context.view_layer.update();body=bpy.data.objects[r['bodyObject']];ref=bpy.data.objects[r['referenceObject']];ref.hide_set(False);body.hide_set(False);arm=body.parent
 def points(o):
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);M=np.array(ev.matrix_world);ev.to_mesh_clear();return v.reshape(-1,3)@M[:3,:3].T+M[:3,3]
 oldT=np.array([list(f.vertices)for f in ref.data.polygons],np.int32);newT=np.array([list(f.vertices)for f in body.data.polygons],np.int32);faces=np.array(r['changedFaces']);capset=set(range(42674,42679))
 directions=[]
 for i in range(512):
  z=1-2*(i+.5)/512;theta=i*pi*(3-sqrt(5));radius=sqrt(max(0,1-z*z));directions.append(np.array([radius*cos(theta),radius*sin(theta),z]))
 def samples(Q,T):
  values=[]
  for fi in faces:
   tri=Q[T[fi]];k=int(np.flatnonzero(np.isin(T[fi],[29974,9755]))[0]);weights=np.full(3,.1);weights[k]=.8;values.append(weights@tri)
  values.extend(Q[T[faces]].mean(1));return np.array(values)
 def visible(tree,targets,direction):
  result=[];hits=[]
  for point in targets:
   loc,normal,index,distance=tree.ray_cast(Vector(point+direction*2),Vector(-direction),3)
   good=index in capset and loc is not None and np.linalg.norm(np.array(loc)-point)<.0001
   result.append(bool(good));hits.append(None if index is None else int(index))
  return result,hits
 best=None;trials=[];poses=[(None,0),('R_clavicle',-10),('R_clavicle',10),('R_upper_arm',-15),('R_upper_arm',15)]
 for bone_name,degrees in poses:
  bone=arm.pose.bones[bone_name]if bone_name else None;basis=bone.matrix_basis.copy()if bone else None
  if bone:bone.matrix_basis=basis@Matrix.Rotation(radians(degrees),4,'X')
  bpy.context.view_layer.update();q0,q1=points(ref),points(body);s0,s1=samples(q0,oldT),samples(q1,newT)
  trees=[BVHTree.FromPolygons(q0.tolist(),oldT.tolist(),all_triangles=True),BVHTree.FromPolygons(q1.tolist(),newT.tolist(),all_triangles=True)]
  tris=q1[newT[faces]];normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]).sum(0);normal/=np.linalg.norm(normal);pose_best=None
  for direction in directions:
   v0,h0=visible(trees[0],s0,direction);v1,h1=visible(trees[1],s1,direction);both=np.array(v0)&np.array(v1);near=int(both[:3].sum());centroids=int(both[3:].sum());front=float(normal@direction)
   score=near*100+centroids*10+(2 if front>0 else 0)+(1 if bone_name is None else 0)+front*.1
   item={'bone':bone_name or'standing','degrees':degrees,'direction':direction.tolist(),'bothVisibleNearCorner':near,'bothVisibleCentroids':centroids,'visibleBothMask':both.tolist(),'oldHitFaces':h0,'newHitFaces':h1,'frontFacingDot':front,'score':score,'target':np.r_[s0[:3],s1[:3]].mean(0).tolist()}
   if pose_best is None or score>pose_best['score']:pose_best=item
  trials.append(pose_best)
  if best is None or pose_best['score']>best['score']:best=pose_best
  if bone:bone.matrix_basis=basis
  bpy.context.view_layer.update()
  if best['bone']=='standing'and best['bothVisibleNearCorner']==3 and best['bothVisibleCentroids']==3 and best['frontFacingDot']>0:break
 assert best['bothVisibleNearCorner']>=2 and best['bothVisibleCentroids']>=2,{'noSufficientUnoccludedView':trials}
 bone=arm.pose.bones[best['bone']]if best['bone']!='standing'else None;basis=bone.matrix_basis.copy()if bone else None
 if bone:bone.matrix_basis=basis@Matrix.Rotation(radians(best['degrees']),4,'X')
 bpy.context.view_layer.update();camera=scene.camera;scene.render.engine='BLENDER_EEVEE';scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.film_transparent=False
 camera.data.type='ORTHO';camera.data.clip_start=.001;camera.data.clip_end=10;target=Vector(best['target']);camera.location=target+Vector(best['direction'])*2;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.035;scene.render.resolution_x=768;scene.render.resolution_y=768
 directory=F/'renders_visible';assert not directory.exists();directory.mkdir();images=[]
 for view in('visible_closeup','same_pose_context'):
  if view=='same_pose_context':
   center=Vector((0,0,1.27));camera.location=center+Vector(best['direction'])*3;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.98;scene.render.resolution_x=640;scene.render.resolution_y=768
  for state in('before','after'):
   body.hide_render=state=='before';ref.hide_render=state!='before';path=directory/(view+'_'+state+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);images.append({'view':view,'state':state,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 if bone:bone.matrix_basis=basis
 bpy.context.view_layer.update();body.hide_render=False;ref.hide_render=True;ref.hide_set(True);assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 record={'status':'unoccluded-cap-paired-renders-awaiting-visual-review','librarySha256':r['sha256'],'images':images,'selectedView':best,'bestViewsPerTestedPose':trials,'visibilityMethod':'Full old/new body BVHs, no removed geometry; first hit must be an existing cap triangle within0.1mm of sampled face centroid or near fitted corner. Three near-corner samples plus three face centroids tested in both models.','bodyPartsHiddenOrMovedIndependently':False,'sameCameraLightsMaterialsAndPosePerPair':True,'poseIsStanding':best['bone']=='standing','alternatePoseFromAlreadyValidatedProbes':best['bone']!='standing','libraryNotSavedOrChanged':True,'visibleWindowsOpened':False,'desktopSwitched':False,'limit':'Target visibility is measured and still needs visual confirmation. A tested joint pose or back-side-facing view must not be presented as proof of complete standing body clearance or a healthy full character.'}
 OUT.write_text(json.dumps(record,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2));print(json.dumps(record))
except BaseException as error:
 STATUS.write_text(json.dumps({'status':'error','error':str(error),'traceback':traceback.format_exc()},indent=2));raise
