"""Read-only native clothing proxies: the original Remy body omits hidden torso skin."""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'work/qa_thai_original_outfit_v30_20261028';OUT=F/'native_clothing_proxies_report.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
    assert not OUT.exists()
    r=json.loads((ROOT/'reports/CHARACTER_THAI_HEAD_CLOTH_CLEANUP_V29_20261028.json').read_text());assert sha(r['library'])==r['sha256']
    bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
    s=bpy.data.scenes['PREP_THAI_CLINICAL_STANDARD_BODY_V28'];w=bpy.context.window or bpy.context.window_manager.windows[0];w.scene=s;l=s.view_layers[0]
    a=bpy.data.objects['V28_Clinical_Standard_Rig'];idle=bpy.data.actions['Idle.002'];a.animation_data.action=idle;a.animation_data.action_slot=idle.slots[0]
    for tr in a.animation_data.nla_tracks:tr.mute=True
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'));out={};rows=[]
    for label,name in [('top','Tops.003'),('bottom','Bottoms.003')]:
        o=bpy.data.objects[name];o.hide_render=False;o.hide_set(False,view_layer=l);s.frame_set(1);l.update()
        ev=o.evaluated_get(l.depsgraph);m=ev.to_mesh();arr=h['_snapshot'](m)['arrays'];M=np.array(ev.matrix_world,dtype=float)
        Q=arr['coordinates']@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
        names=list(o.vertex_groups.keys());assert names==list(bpy.data.objects['Body.003'].vertex_groups.keys())
        out[label+'Q']=Q;out[label+'T']=arr['triangles'];out[label+'W']=h['_weights'](o.data,55)
        rows.append({'object':name,'label':label,'vertices':len(Q),'triangles':len(arr['triangles']),'bounds':[Q.min(0).tolist(),Q.max(0).tolist()]})
    path=F/'native_clothing_proxies_v30.npz';assert not path.exists();np.savez_compressed(path,**out)
    result={'status':'native-top-and-bottom-proxies-exported-for-region-fit','archive':str(path),'archiveSha256':sha(path),
        'sourceLibrary':r['library'],'sourceSha256':r['sha256'],'objects':rows,'sourceHashUnchanged':sha(r['library'])==r['sha256'],
        'sourceSavedOrModified':False,'runtimeChanged':False,'remoteOperations':False,'blenderVersion':bpy.app.version_string}
    OUT.write_text(json.dumps(result,indent=2));print(json.dumps(result))
except BaseException as e:
    (ROOT/'work/v30_proxy_export_error_20261028.json').write_text(json.dumps({'error':str(e),'traceback':traceback.format_exc()},indent=2));raise
