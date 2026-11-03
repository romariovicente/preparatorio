"""Resume a verified project session in the existing Desktop1 Blender window.

Keep frozen review/source libraries intact; save the viewport/session to WORK.
No window is created, focused or moved by this script.
"""
import bpy,json,hashlib,shutil,runpy
import numpy as np
from pathlib import Path
from datetime import datetime,timezone
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_POSTURE_DIAGNOSTIC_V21_20261027.json').read_text())
desktop=json.loads((ROOT/'work/blender_desktop_v21_20261027.json').read_text())
observed=datetime.fromisoformat(desktop['ObservedAt'])
assert (datetime.now(timezone.utc)-observed).total_seconds()<600
assert len(desktop['BlenderWindows'])==1 and desktop['BlenderWindows'][0]['DesktopIndex']==1
assert not bpy.app.background
work=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_WORK_V21_MCP_20261027.blend'
checkpoint=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_MCP_SESSION_V21_20261027.blend'
out=ROOT/'reports/CHARACTER_THAI_POSTURE_V21_MCP_SESSION_20261027.json'
assert not out.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(r['library'])==r['sha256']
if not work.exists():
    assert not checkpoint.exists() and not bpy.data.filepath and not bpy.data.is_dirty
    assert set(bpy.data.objects.keys())=={'Camera','Cube','Light'}
    shutil.copy2(r['library'],checkpoint)
    shutil.copy2(r['library'],work)
    bpy.ops.wm.open_mainfile(filepath=str(work),load_ui=False,use_scripts=False)
else:
    # The first open succeeded, but the MCP callback lost its window context.
    # Resume only that exact untouched copy, never an arbitrary dirty session.
    assert Path(bpy.data.filepath)==work and not bpy.data.is_dirty
    assert sha(work)==r['sha256'] and sha(checkpoint)==r['sha256']
scene=bpy.data.scenes[r['scenes'][0]]
window=bpy.context.window or bpy.context.window_manager.windows[0]
window.scene=scene
body=bpy.data.objects[r['baselineBody']]
layer=scene.view_layers[0];layer.update()
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
a=h['_snapshot'](body.data)['arrays']
assert {k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in a.items()}==r['bodyArraysSha256']
assert hashlib.sha256(h['_weights'](body.data,len(body.vertex_groups)).tobytes()).hexdigest()==r['weightsSha256']
for obj in scene.objects:obj.select_set(False,view_layer=layer)
body.select_set(True,view_layer=layer);layer.objects.active=body
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=1.9
target=Vector((0,0,.85));camera.location=Vector((0,-3,.85));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_location=target
            space.region_3d.view_distance=2.2
            space.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            space.region_3d.view_perspective='ORTHO'
            space.shading.type='SOLID';space.shading.color_type='TEXTURE'
            space.clip_start=.01;space.clip_end=100
scene['PREP_current_status']='Posture diagnosis only; no accepted posture repair; frozen source and runtime preserved.'
with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):
    bpy.ops.wm.save_as_mainfile(filepath=str(work),compress=True)
assert sha(r['library'])==r['sha256'] and sha(checkpoint)==r['sha256']
record={'status':'existing-Desktop1-Blender-resumed-through-local-MCP-and-WORK-saved','workingLibrary':str(work),'sha256':sha(work),'checkpoint':str(checkpoint),'checkpointSha256':sha(checkpoint),'frozenDiagnosticLibrary':r['library'],'frozenDiagnosticSha256':r['sha256'],'desktopEvidence':str(ROOT/'work/blender_desktop_v21_20261027.json'),'activeScene':scene.name,'bodyArraysAndWeightsExact':True,'nativeWalkValidated':False,'postureFixed':False,'MCPUsed':True,'GUIWindowAlreadyExisted':True,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'sourceAndRuntimePreserved':True,'remoteOperations':False}
out.write_text(json.dumps(record,indent=2));print(json.dumps(record))
