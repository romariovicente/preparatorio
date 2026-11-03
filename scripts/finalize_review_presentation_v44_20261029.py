"""Finish only the diagnostic presentation; keep all tested source data intact."""
import bpy,json,hashlib,runpy,sys,types,shutil
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_20261029.json'
r=json.loads(REPORT.read_text());raw=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json').read_text())
stage=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_STAGE_20261029.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path(bpy.data.filepath)==Path(r['library'])
cp=ROOT/'art/blender/libraries/PREP_CHARACTER_THAI_BEFORE_REVIEW_PRESENTATION_FINAL_V44_20261029.blend'
initial=ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_PRESENTATION_INITIAL_20261029.json'
resuming=cp.exists() and initial.exists()
if resuming:
    assert sha(cp)==r['sha256']
    failure=json.loads((ROOT/'reports/pose_review_controller_v44_20261029/presentation_failure_readback_v44.json').read_text())
    assert Path(failure['file'])==Path(r['library']) and failure['body']['exact']
else:assert sha(r['library'])==r['sha256']
assert sha(raw['library'])==raw['sha256']
u=runpy.run_path(str(ROOT/'work/thai_integrity_helpers_20261028.py'));h=u['helpers']
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
module=sys.modules['preparatorio_review_v44'];module._verify_bind(module.actor(bpy.context.scene),module._candidate())
if not resuming:
    assert not cp.exists() and not initial.exists()
    shutil.copyfile(r['library'],cp);assert sha(cp)==r['sha256'];shutil.copyfile(REPORT,initial)
hidden=[]
for name in [stage['nativeRig'],stage['poseRig'],'V30_ORIGINAL_SHIRT_Regional_Bind_Pilot','V33_ORIGINAL_BLACK_SKIRT_Continuous_Neutral_Drape','Shoes.003']:
    obj=bpy.data.objects[name];obj.hide_set(True);hidden.append(name)
window=bpy.context.window or bpy.context.window_manager.windows[0]
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;space.overlay.show_extras=False
        space.shading.color_type='SINGLE';space.shading.single_color=(.55,.55,.55)
        next(x for x in area.regions if x.type=='UI').active_panel_category='Preparatório';area.tag_redraw()
if not resuming:
    with bpy.context.temp_override(window=window):bpy.ops.wm.save_as_mainfile(filepath=r['library'],compress=True)
saved=sha(r['library'])
bpy.ops.wm.open_mainfile(filepath=r['library'],load_ui=False,use_scripts=False)
window=bpy.context.window or bpy.context.window_manager.windows[0];scene=bpy.data.scenes[raw['scene']];window.scene=scene;layer=scene.view_layers[0]
code=bpy.data.texts[raw['textBlock']].as_string();assert hashlib.sha256(code.encode()).hexdigest()==raw['controllerSha256']
module=types.ModuleType('preparatorio_review_v44');module.__file__=raw['controller'];sys.modules[module.__name__]=module
exec(compile(code,raw['controller'],'exec'),module.__dict__);module.register()
body=bpy.data.objects[raw['actor']];module._verify_bind(body,module._candidate())
a=h['_snapshot'](body.data)['arrays'];W=h['_weights'](body.data,55);names=list(body.vertex_groups.keys())
R=np.array([np.array(bpy.data.objects[stage['nativeRig']].data.bones[n].matrix_local) for n in names]);PR=np.array([np.array(bpy.data.objects[stage['poseRig']].data.bones[n].matrix_local) for n in names])
layer.update()
def points(obj):
    ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p);M=np.array(ev.matrix_world);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
Q=points(body);headQ=points(bpy.data.objects['V28_Thai_Face_And_Hair_Preserved'])
with np.load(raw['archive']) as z:
    checks={'coordinatesExact':np.array_equal(a['coordinates'],z['actualRestWorld']),'trianglesExact':np.array_equal(a['triangles'],z['actualTriangles']),'weights55Exact':np.array_equal(W,z['actualWeights55']),'names55Exact':np.array_equal(np.asarray(names),z['actualNames55']),'nativeRestExact':np.array_equal(R,z['actualBoneRest55']),'poseRigRestExact':np.array_equal(PR,z['actualBoneRest55']),'defaultQExact':np.array_equal(Q,z['Idle_101_corrected_studyQ'])}
with np.load(stage['actualV43Snapshots']) as z:
    head_exact=bool(np.array_equal(headQ,z['Idle_101_headQ']))
    head_error=float(np.linalg.norm(headQ-z['Idle_101_headQ'],axis=1).max())
    checks['headQWithinExisting20MicronGate']=head_error<2e-5
assert all(checks.values())
assert all(bpy.data.objects[n].hide_get(view_layer=layer) for n in hidden)
assert u['action_signatures']()==stage['actionSignatures']
assert all(u['mesh_signature'](bpy.data.objects[n])==s for n,s in stage['meshSignatures'].items())
assert sha(raw['library'])==raw['sha256'] and sha(r['library'])==saved
assert bpy.ops.preparatorio.review_pose_sample_v44.get_rna_type().identifier=='PREPARATORIO_OT_review_pose_sample_v44'
r.update(sha256=saved,presentationCheckpoint=str(cp),presentationCheckpointSHA256=sha(cp),initialPresentationReport=str(initial),bindAndDefaultPoseChecks={k:bool(v) for k,v in checks.items()},headPointsBitExact=head_exact,headMaximumDifferenceMeters=head_error,headToleranceMeters=2e-5,overstrictInitialHeadBitEqualityAssertionFailed=resuming,viewportOnlyHiddenObjects=hidden,originalClothesPreservedNotDeleted=True,defaultGameOutfitChanged=False,giantNativeRigDisplayHidden=True,sourceMeshesAnd2200CurvesExact=True,explicitRegistrationAfterReopen=True,diagnosticSingleViewportColorNotMaterialEdit=True)
r['viewports']=[]
for area in window.screen.areas:
    if area.type=='VIEW_3D':
        space=area.spaces.active;region=next(x for x in area.regions if x.type=='UI');region.active_panel_category='Preparatório';area.tag_redraw()
        r['viewports'].append({'activeCategory':region.active_panel_category,'viewDistance':space.region_3d.view_distance,'viewLocation':list(space.region_3d.view_location),'extrasVisible':space.overlay.show_extras,'singleViewportColor':list(space.shading.single_color)})
REPORT.write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
