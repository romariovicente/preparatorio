"""Preserve the fresh empty session and the newer saved V38 before V39 work."""
import bpy, json, hashlib, runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/CHARACTER_THAI_GEOMETRY_V39_STAGE_20261029.json'
assert not OUT.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
stop=json.loads((ROOT/'reports/LOCAL_STOP_STATE_20261029.json').read_text(encoding='utf-8-sig'))
prior=json.loads((ROOT/'reports/CHARACTER_THAI_AXILLA_V38_STAGE_20261028.json').read_text())
source=Path(stop['currentFile'])
assert source.is_file() and sha(source)==stop['currentFileSHA256']
assert not bpy.data.filepath and not bpy.data.is_dirty
assert set(bpy.data.objects.keys())=={'Cube','Camera','Light'} and not bpy.data.actions
window=bpy.context.window or bpy.context.window_manager.windows[0]
startup=ROOT/'art/blender/libraries/PREP_BEFORE_RESUME_EMPTY_SESSION_V39_20261029.blend'
assert not startup.exists()
with bpy.context.temp_override(window=window):
    bpy.ops.wm.save_as_mainfile(filepath=str(startup),compress=True,copy=True)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
window=bpy.context.window or bpy.context.window_manager.windows[0]
assert not bpy.data.is_dirty
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'))
actions=u['action_signatures']()
signatures={n:u['mesh_signature'](bpy.data.objects[n]) for n in prior['meshSignatures'] if n in bpy.data.objects}
missing=[n for n in prior['meshSignatures'] if n not in bpy.data.objects]
differences=[n for n,s in signatures.items() if s!=prior['meshSignatures'][n]]
audit={'source':str(source),'sourceSha256':sha(source),'sourceLastWriteTimeObserved':stop['currentFileLastWriteTime'],
       'actionsMatchStage':actions==prior['actionSignatures'],'missingStageObjects':missing,
       'changedStageMeshSignatures':differences,'scene':window.scene.name,'frame':window.scene.frame_current,
       'objects':[{'name':o.name,'type':o.type,'hidden':o.hide_get(),'renderHidden':o.hide_render,
                   'modifiers':[{'name':m.name,'type':m.type,'viewport':m.show_viewport} for m in o.modifiers]}
                  for o in window.scene.objects],
       'dirtyAfterLoad':bpy.data.is_dirty,'freshEmptySessionCheckpoint':str(startup),'MCPUsed':True,
       'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'remoteOperations':False}
(ROOT/'reports/CHARACTER_THAI_NEWER_V38_AUDIT_20261029.json').write_text(json.dumps(audit,indent=2))
assert not missing and not differences and actions==prior['actionSignatures'], 'Newer source has data changes: preserve and inspect before continuation'
checkpoint=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_AXILLA_GEOMETRY_V39_20261029.blend'
working=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_AXILLA_GEOMETRY_V39_WORK_20261029.blend'
assert not checkpoint.exists() and not working.exists()
with bpy.context.temp_override(window=window):
    bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint),compress=True,copy=True)
window.scene.name='REVIEW_THAI_LOCAL_AXILLA_GEOMETRY_V39'
with bpy.context.temp_override(window=window):
    bpy.ops.wm.save_as_mainfile(filepath=str(working),compress=True)
assert sha(source)==stop['currentFileSHA256']
result={k:prior[k] for k in ['sourceBody','poseRig','nativeRig','nativeRestSHA256']}
result.update(status='geometry-study-staged-source-preserved',source=str(source),sourceSha256=sha(source),
              checkpoint=str(checkpoint),checkpointSha256=sha(checkpoint),working=str(working),workingSha256=sha(working),
              actionSignatures=actions,meshSignatures=signatures,scene=window.scene.name,
              newWindowOpened=False,windowFocusedOrMoved=False,desktopSwitched=False,remoteOperations=False,MCPUsed=True)
OUT.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['actionSignatures','meshSignatures']}))
