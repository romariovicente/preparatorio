import bpy,json,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
raw=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_20261029.json').read_text());stage=json.loads((ROOT/'reports/CHARACTER_THAI_REVIEW_CONTROLLER_V44_STAGE_20261029.json').read_text())
scene=bpy.context.scene;layer=scene.view_layers[0];layer.update()
def points(obj):
    ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();p=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',p);M=np.array(ev.matrix_world);q=p.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear();return q
bodyQ=points(bpy.data.objects[raw['actor']]);headQ=points(bpy.data.objects['V28_Thai_Face_And_Hair_Preserved'])
with np.load(raw['archive']) as z:body={'exact':bool(np.array_equal(bodyQ,z['Idle_101_corrected_studyQ'])),'maxDifferenceM':float(np.linalg.norm(bodyQ-z['Idle_101_corrected_studyQ'],axis=1).max())}
with np.load(stage['actualV43Snapshots']) as z:head={'exact':bool(np.array_equal(headQ,z['Idle_101_headQ'])),'maxDifferenceM':float(np.linalg.norm(headQ-z['Idle_101_headQ'],axis=1).max())}
out={'file':bpy.data.filepath,'frame':scene.frame_current,'body':body,'head':head,'rigs':[{'name':n,'hidden':bpy.data.objects[n].hide_get(),'action':bpy.data.objects[n].animation_data.action.name,'slot':bpy.data.objects[n].animation_data.action_slot.identifier} for n in [stage['nativeRig'],stage['poseRig']]],'state':[scene.get('PREP_review_last_clip'),scene.get('PREP_review_last_frame'),scene.get('PREP_review_last_branch'),scene.get('PREP_review_last_variant')]}
(ROOT/'reports/pose_review_controller_v44_20261029/presentation_failure_readback_v44.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
