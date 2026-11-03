"""Frame the reviewed body in the existing project window without focusing it."""
import bpy,json,hashlib,runpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/CHARACTER_THAI_V32_REVIEW_SESSION_20261028.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
r=json.loads((ROOT/'reports/CHARACTER_THAI_COMPLETE_BASE_V32_20261028.json').read_text())
assert Path(bpy.data.filepath)==Path(r['library'])and not bpy.data.is_dirty and sha(r['library'])==r['sha256']
h=runpy.run_path(str(ROOT/'work/thai_bmesh_weight_helper_20261023.py'))
body=bpy.data.objects[r['bodyObject']];head=bpy.data.objects['V28_Thai_Face_And_Hair_Preserved']
def signature(obj):
    arrays=h['_snapshot'](obj.data)['arrays']
    return {'arrays':{k:hashlib.sha256(v.tobytes()).hexdigest()for k,v in arrays.items()},
        'groups':list(obj.vertex_groups.keys()),'weights':hashlib.sha256(h['_weights'](obj.data,len(obj.vertex_groups)).tobytes()).hexdigest()}
before={'body':signature(body),'head':signature(head)}
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[r['scene']];window.scene=scene;layer=scene.view_layers[0]
for obj in scene.objects:obj.select_set(False,view_layer=layer)
body.hide_set(False,view_layer=layer);body.select_set(True,view_layer=layer);layer.objects.active=body
views=0
for area in window.screen.areas:
    if area.type!='VIEW_3D':continue
    space=area.spaces.active;space.region_3d.view_location=Vector((0,0,.85));space.region_3d.view_distance=2.5
    space.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion();space.region_3d.view_perspective='ORTHO'
    space.overlay.show_overlays=False;space.shading.type='MATERIAL';views+=1
assert views>0
target=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_COMPLETE_BASE_V32_REVIEW_20261028.blend';assert not target.exists()
with bpy.context.temp_override(window=window,scene=scene,view_layer=layer):bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
after={'body':signature(body),'head':signature(head)};assert before==after and sha(r['library'])==r['sha256']
result={'status':'review-copy-open-in-existing-Blender-project-window','reviewFile':str(target),'reviewSha256':sha(target),
    'sourceValidatedFile':r['library'],'sourceSha256':r['sha256'],'geometryHeadWeightsUVExactAgainstValidatedBase':True,
    'beforeAfterDataSignatures':after,'viewportsFramed':views,'originalShirtSkirtAreUnfinishedWorkPieces':True,
    'appearanceOrRuntimeApproved':False,'MCPUsed':True,'newWindowOpened':False,'windowFocusedOrMoved':False,
    'desktopSwitched':False,'runtimeChanged':False,'remoteOperations':False}
OUT.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='beforeAfterDataSignatures'}))
