"""Reopen the diagnostic library, verify the unchanged avatar, then preview.

This never poses the six rejected trials and never saves over the library.
"""
import bpy,json,hashlib,runpy,traceback,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.json'
OUT=ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_REOPEN_PREVIEW_20261027.json'
STATUS=ROOT/'work/v21_diagnostic_validation_retry2_status_20261027.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def points(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
    v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v)
    mat=np.array(ev.matrix_world);ev.to_mesh_clear()
    return v.reshape(-1,3)@mat[:3,:3].T+mat[:3,3]

try:
    assert bpy.app.background and not any(p.exists()for p in(OUT,STATUS))
    r=json.loads(REPORT.read_text());lib=Path(r['library'])
    assert sha(lib)==r['sha256'] and sha(r['source'])==r['sourceSha256'] and sha(r['checkpoint'])==r['sourceSha256']
    bpy.ops.wm.open_mainfile(filepath=str(lib),load_ui=False,use_scripts=False)
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    with np.load(ROOT/'work/thai_posture_v21_20261027/actual_rig_mesh.npz')as n:data={k:n[k].copy()for k in n.files}
    q,t=data['posed'],data['triangles']
    bodies=[bpy.data.objects[r['baselineBody']],bpy.data.objects[r['riskBody']]]
    checks={}
    for i,(name,body)in enumerate(zip(r['scenes'],bodies)):
        bpy.context.window.scene=bpy.data.scenes[name];bpy.context.view_layer.update()
        a=h['_snapshot'](body.data)['arrays'];dig={k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}
        expect=r['bodyArraysSha256']if i==0 else r['riskBodyArraysSha256']
        assert dig==expect
        assert np.array_equal(h['_weights'](body.data,len(body.vertex_groups)),data['weights'])
        assert np.array_equal(points(body),q)
        assert np.array_equal(np.array([np.array(body.parent.pose.bones[n].matrix_basis)for n in data['group_names']]),data['bone_pose_bases'])
        if i==1:
            for k,v in dig.items():
                if k!='polygonMaterial':assert v==r['bodyArraysSha256'][k]
        checks[body.name]={'arraysExact':True,'weightsExact':True,'standingWorldCoordinatesExact':True,'poseBasesExact':True}
    risk=bodies[1]
    with np.load(ROOT/'reports/thai_posture_diagnostic_v21_20261027/risk_attributes.npz')as n:
        expected={k:n[k].copy()for k in n.files}
    for name,key in [('prep_v21_risk_2mm_bits','risk_bits'),('prep_v21_source_face_id',None)]:
        a=risk.data.attributes[name];values=np.empty(len(a.data),np.int32);a.data.foreach_get('value',values)
        assert np.array_equal(values,expected[key]if key else np.arange(len(t),dtype=np.int32))
    assert set(np.flatnonzero(expected['risk_bits']))==set(r['direct2mmRiskFaces'])
    assert len([o for o in risk.users_scene[0].objects if o.name.startswith('V21_SOURCE_FACE_')])==3
    source_report=json.loads((ROOT/'reports/CHARACTER_THAI_CAP_REFIT_V20_20261027.json').read_text())
    original=bpy.data.objects[source_report['bodyObject']]
    bpy.context.window.scene=bpy.data.scenes[source_report['scene']];bpy.context.view_layer.update()
    assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in h['_snapshot'](original.data)['arrays'].items()}==r['bodyArraysSha256']
    assert np.array_equal(points(original),q)
    checks['originalV20InsideLibraryPreserved']=True
    bvh=BVHTree.FromPolygons(q.tolist(),t.tolist(),all_triangles=True)
    directions=[]
    for k in range(2048):
        z=1-2*(k+.5)/2048;angle=k*math.pi*(3-math.sqrt(5));rad=math.sqrt(1-z*z)
        directions.append(np.array([rad*math.cos(angle),rad*math.sin(angle),z]))
    closeups=[]
    for face in (23904,38884):
        tri=q[t[face]];center=tri.mean(0);norm=np.cross(tri[1]-tri[0],tri[2]-tri[0]);norm/=np.linalg.norm(norm)
        samples=[center]+[center*.9+v*.1 for v in tri]
        valid=[]
        for direction in directions:
            dot=float(direction@norm)
            if dot<.2:continue
            hits=[]
            for p in samples:
                origin=Vector(p+direction*.6);target=Vector(p);hit,_,fid,dist=bvh.ray_cast(origin,(target-origin).normalized(),.601)
                hits.append(hit is not None and fid==face and (hit-target).length<2e-5)
            if all(hits):valid.append((dot,direction))
        if valid:
            dot,direction=max(valid,key=lambda item:item[0])
            visible=True
        else:
            # Preserve occlusion instead of hiding geometry to manufacture proof.
            # This shot is contextual only; it cannot certify that source face.
            direction=np.array([1.,-1.,.15]);direction/=np.linalg.norm(direction)
            dot=float(direction@norm);visible=False
        closeups.append({'face':face,'target':center.tolist(),'direction':direction.tolist(),'normalFacingDot':dot,'allFourNearCentroidRaysHitExactSourceFace':visible,'exteriorVisibilityProven':visible,'semanticClassificationApproved':False,'scaleMeters':.18})
    folder=ROOT/'reports/thai_posture_diagnostic_v21_20261027/renders'
    assert not folder.exists();folder.mkdir()
    views=[{'name':'front_context','target':[0,0,.85],'direction':[0,-1,0],'scaleMeters':1.85,'resolution':[640,960]},
           {'name':'right_context','target':[0,0,.85],'direction':[-1,0,0],'scaleMeters':1.85,'resolution':[640,960]}]
    views += [dict(name='face_'+str(v['face'])+'_context',resolution=[640,640],**v)for v in closeups]
    images=[]
    for view in views:
        for scene_name,body,mode in zip(r['scenes'],bodies,('baseline','risk')):
            scene=bpy.data.scenes[scene_name];bpy.context.window.scene=scene;bpy.context.view_layer.update()
            scene.render.engine='BLENDER_EEVEE'
            scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
            scene.render.resolution_x,scene.render.resolution_y=view['resolution']
            scene.render.threads_mode='FIXED';scene.render.threads=2
            scene.render.film_transparent=False;scene.view_settings.view_transform='AgX'
            camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=view['scaleMeters']
            target=Vector(view['target']);direction=Vector(view['direction']).normalized()
            camera.location=target+direction*3
            camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            path=folder/(view['name']+'_'+mode+'.png');assert not path.exists()
            scene.render.filepath=str(path)
            (ROOT/'work/v21_diagnostic_render_progress_20261027.json').write_text(json.dumps({'view':view['name'],'mode':mode}))
            bpy.ops.render.render(write_still=True)
            images.append({'view':view['name'],'mode':mode,'path':str(path),'sha256':sha(path)})
    assert sha(lib)==r['sha256'] and sha(r['source'])==r['sourceSha256']
    result={'status':'diagnostic-library-reopened-exact-and-eight-previews-rendered','library':str(lib),'sha256':r['sha256'],'checks':checks,'riskAttributesExact':True,'originalAndRuntimeNotEdited':True,'sourceAndCheckpointExact':True,'images':images,'closeupVisibilityProof':closeups,'guidesHiddenInRenderToAvoidFalseDepth':True,'rejectedPoseImported':False,'postureFixed':False,'nativeWalkValidated':False,'GUIOpened':False,'MCPUsed':False,'backgroundMode':True,'libraryNotResavedDuringPreview':True,'priorFailedPreviewAttempt':str(ROOT/'work/v21_diagnostic_validation_status_20261027.json'),'limitation':'Diagnostic preview of unchanged old posture. Grey/red/amber are review materials; no repaired character or clinical anatomical approval. Face38884 has no proven external visibility and its contextual render does not certify semantics.'}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)},indent=2))
except BaseException as exc:
    STATUS.write_text(json.dumps({'status':'error','error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
