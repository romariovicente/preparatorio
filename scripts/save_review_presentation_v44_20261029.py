"""Save presentation-only copy, reopen and compare the actual default pose."""
import bpy,json,hashlib,runpy,sys,types
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json').read_text())
stage=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_STAGE_20261029.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path(bpy.data.filepath)==Path(r['library']) and sha(r['library'])==r['sha256']
assert sha(r['archive'])==r['archiveSha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
body=bpy.data.objects[r['actor']]
module=sys.modules['preparatorio_review_v44'];module._verify_bind(body,module._candidate())
assert bpy.context.scene['PREP_review_last_clip']=='Idle' and bpy.context.scene['PREP_review_last_frame']==101
out=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_POSE_REVIEW_V44_READY_20261029.blend'
assert not out.exists()
window=bpy.context.window or bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
saved=sha(out)
bpy.ops.wm.open_mainfile(filepath=str(out),load_ui=False,use_scripts=False)
body=bpy.data.objects[r['actor']];scene=bpy.data.scenes[r['scene']]
window=bpy.context.window or bpy.context.window_manager.windows[0];window.scene=scene;layer=scene.view_layers[0]
code=bpy.data.texts[r['textBlock']].as_string()
assert hashlib.sha256(code.encode()).hexdigest()==r['controllerSha256']
module=types.ModuleType('preparatorio_review_v44');module.__file__=r['controller'];sys.modules[module.__name__]=module
exec(compile(code,r['controller'],'exec'),module.__dict__);module.register()
module._verify_bind(body,module._candidate())
arrays=h['_snapshot'](body.data)['arrays'];W=h['_weights'](body.data,55)
names=list(body.vertex_groups.keys())
R=np.array([np.array(bpy.data.objects[stage['nativeRig']].data.bones[n].matrix_local) for n in names])
poseR=np.array([np.array(bpy.data.objects[stage['poseRig']].data.bones[n].matrix_local) for n in names])
layer.update();ev=body.evaluated_get(layer.depsgraph);mesh=ev.to_mesh()
P=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',P)
M=np.array(ev.matrix_world);Q=P.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
with np.load(r['archive']) as z:
    checks={'coordinatesExact':np.array_equal(arrays['coordinates'],z['actualRestWorld']),
      'trianglesExact':np.array_equal(arrays['triangles'],z['actualTriangles']),
      'weights55Exact':np.array_equal(W,z['actualWeights55']),
      'names55Exact':np.array_equal(np.asarray(names),z['actualNames55']),
      'nativeRestExact':np.array_equal(R,z['actualBoneRest55']),
      'poseRigRestExact':np.array_equal(poseR,z['actualBoneRest55']),
      'defaultQExact':np.array_equal(Q,z['Idle_101_corrected_studyQ'])}
assert all(checks.values())
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
assert sha(out)==saved and sha(r['library'])==r['sha256']
assert not bpy.data.texts[r['textBlock']].use_module
assert bpy.ops.preparatorio.review_pose_sample_v44.get_rna_type().identifier=='PREPARATORIO_OT_review_pose_sample_v44'
viewports=[]
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;region=next(x for x in area.regions if x.type=='UI')
        region.active_panel_category='Preparatório';area.tag_redraw()
        viewports.append({'activeCategory':region.active_panel_category,'viewLocation':list(space.region_3d.view_location),'viewDistance':space.region_3d.view_distance})
result={'status':'presentation-only-ready-copy-saved-reopened-and-default-geometry-verified','library':str(out),'sha256':saved,'sourceLibrary':r['library'],'sourceLibrarySHA256':r['sha256'],'checkpointIsPreservedSourceLibrary':True,'sourceArchive':r['archive'],'sourceArchiveSHA256':r['archiveSha256'],'bindAndDefaultPoseChecks':{k:bool(v) for k,v in checks.items()},'sourceMeshesAnd2200CurvesExact':True,'operatorRNARegistered':True,'panelRNARegistered':hasattr(bpy.types,'PREP44_PT_PoseReview'),'explicitRegistrationAfterReopen':True,'viewports':viewports,'presentationChangesOnly':True,'full32CaseQARefersToSourceLibrary':True,'newSolverExecuted':False,'poseGeometryApproved':False,'fullAnimationApproved':False,'clothesApproved':False,'runtimeChanged':False,'masterChanged':False,'remoteOperations':False,'newWindowOpened':False,'windowFocusedOrMoved':False,'desktopSwitched':False,'MCPUsed':True}
(ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_20261029.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
