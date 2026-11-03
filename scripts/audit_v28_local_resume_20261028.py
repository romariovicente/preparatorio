"""Read-only resume audit after the shared computer was restarted."""
import bpy,json,hashlib,runpy,traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_V28_RESUME_AUDIT_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
try:
    assert not OUT.exists()
    r=json.loads((ROOT/'reports/CHARACTER_THAI_CLINICAL_GROUP_FIX_V28_20261027.json').read_text())
    path=Path(r['library']);backup=Path(str(path)+'1');assert sha(backup)==r['sha256']
    h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
    def snapshot(p):
        bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
        s=bpy.data.scenes['PREP_THAI_CLINICAL_STANDARD_BODY_V28'];arm=bpy.data.objects['V28_Clinical_Standard_Rig']
        rows={}
        for o in s.objects:
            if o.type!='MESH':continue
            a=h['_snapshot'](o.data)['arrays']
            rows[o.name]={'arrays':{k:digest(v)for k,v in a.items()},'groups':list(o.vertex_groups.keys()),
                'weights':digest(h['_weights'](o.data,len(o.vertex_groups))),
                'matrixWorld':list(np.array(o.matrix_world).reshape(-1).astype(float)),
                'parent':o.parent.name if o.parent else None,'parentType':o.parent_type,'parentBone':o.parent_bone,
                'hideRender':o.hide_render,'materials':[m.name for m in o.data.materials],
                'modifiers':[{'type':m.type,'target':m.object.name if m.type=='ARMATURE' and m.object else None}for m in o.modifiers]}
        bones={b.name:{'parent':b.parent.name if b.parent else None,'matrix':np.array(b.matrix_local).tolist()}for b in arm.data.bones}
        actions={}
        for track in arm.animation_data.nla_tracks:
            for strip in track.strips:
                a=strip.action;curves=[]
                for al in a.layers:
                    for st in al.strips:
                        for bag in st.channelbags:
                            for fc in bag.fcurves:curves.append((fc.data_path,fc.array_index,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation)for k in fc.keyframe_points]))
                actions[track.name]={'action':a.name,'slot':strip.action_slot.identifier if strip.action_slot else None,'curvesSha':hashlib.sha256(repr(curves).encode()).hexdigest()}
        return {'meshes':rows,'bones':bones,'actions':actions,'frame':s.frame_current,'activeAction':arm.animation_data.action.name if arm.animation_data.action else None}
    old=snapshot(backup);current=snapshot(path)
    mesh_diffs={name:[k for k in old['meshes'][name]if old['meshes'][name][k]!=v]for name,row in current['meshes'].items()for v in [None]}
    mesh_diffs={name:[k for k,v in row.items()if old['meshes'][name][k]!=v]for name,row in current['meshes'].items()}
    result={'status':'saved-resume-audited','library':str(path),'currentSha256':sha(path),'historicalSha256':r['sha256'],
        'backup':str(backup),'backupSha256':sha(backup),'byteMatchHistorical':sha(path)==r['sha256'],
        'meshDifferences':{k:v for k,v in mesh_diffs.items()if v},'rigRestUnchanged':old['bones']==current['bones'],
        'nativeActionsUnchanged':old['actions']==current['actions'],'currentFrame':current['frame'],'currentAction':current['activeAction'],
        'currentData':current,'backgroundMode':bpy.app.background,'blenderVersion':bpy.app.version_string,
        'MCPAvailable':False,'execution':'Existing GUI absent; hidden local Blender CLI used without opening a desktop window',
        'sourceSavedOrModified':False,'runtimeChanged':False,'remoteOperations':False}
    OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='currentData'}))
except BaseException as exc:
    (ROOT/'work/v28_resume_audit_error_20261028.json').write_text(json.dumps({'error':str(exc),'traceback':traceback.format_exc()},indent=2));raise
