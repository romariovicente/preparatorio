"""Read-only export of the fresh native rig and fitted body for garment binding."""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'work/qa_thai_original_outfit_v30_20261028'
OUT=F/'target_surface_and_rig_report.json';STATUS=ROOT/'work/v30_target_export_status_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists();F.mkdir(parents=True,exist_ok=True)
    r=json.loads((ROOT/'reports/CHARACTER_THAI_HEAD_CLOTH_CLEANUP_V29_20261028.json').read_text())
    assert sha(r['library'])==r['sha256']
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    s=bpy.data.scenes['PREP_THAI_CLINICAL_STANDARD_BODY_V28'];window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=s;l=s.view_layers[0]
    arm=bpy.data.objects['V28_Clinical_Standard_Rig'];body=bpy.data.objects['Body.003']
    idle=bpy.data.actions['Idle.002'];arm.animation_data.action=idle;arm.animation_data.action_slot=idle.slots[0]
    for tr in arm.animation_data.nla_tracks:tr.mute=True
    body.hide_set(False,view_layer=l);body.hide_render=False;s.frame_set(1);l.update()
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    ev=body.evaluated_get(l.depsgraph);mesh=ev.to_mesh();a=h['_snapshot'](mesh)['arrays'];M=np.array(ev.matrix_world,dtype=float)
    Q=a['coordinates']@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
    names=list(body.vertex_groups.keys());assert len(names)==55
    W=h['_weights'](body.data,len(names));ev=arm.evaluated_get(l.depsgraph)
    rest=np.array([np.array(arm.data.bones[n].matrix_local,dtype=float)for n in names])
    pose=np.array([np.array(ev.pose.bones[n].matrix,dtype=float)for n in names])
    heads=np.array([np.array(ev.matrix_world@ev.pose.bones[n].head,dtype=float)for n in names])
    A=np.array(ev.matrix_world,dtype=float)
    out=F/'target_surface_and_rig_v30.npz';assert not out.exists()
    np.savez_compressed(out,bodyIdleWorld=Q,bodyTriangles=a['triangles'],bodyRestP=h['_snapshot'](body.data)['arrays']['coordinates'],
        bodyWeights=W,bodyWorld=M,boneNames=np.array(names),boneRestMatrices=rest,boneIdleMatrices=pose,
        boneIdleHeadsWorld=heads,armWorld=A,avatarRootWorld=np.array(bpy.data.objects['V28_Thai_Clinical_Avatar_Root'].matrix_world,dtype=float))
    result={'status':'fresh-native-Idle-body-and-55-bone-bind-data-exported','sourceLibrary':r['library'],'sourceSha256':r['sha256'],
        'archive':str(out),'archiveSha256':sha(out),'bodyObject':body.name,'vertices':len(Q),'triangles':len(a['triangles']),
        'bones':len(names),'poseAction':idle.name,'actionSlot':idle.slots[0].identifier,'frame':1,
        'sourceSavedOrModified':False,'sourceHashUnchanged':sha(r['library'])==r['sha256'],'runtimeChanged':False,
        'background':bpy.app.background,'blenderVersion':bpy.app.version_string,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));STATUS.write_text(json.dumps({'status':'success','report':str(OUT)}));print(json.dumps(result))
except BaseException as e:
    STATUS.write_text(json.dumps({'status':'error','error':str(e),'traceback':traceback.format_exc()},indent=2));raise
