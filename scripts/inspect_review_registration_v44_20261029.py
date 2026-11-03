import bpy,json,sys
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
identifier=bpy.ops.preparatorio.review_pose_sample_v44.get_rna_type().identifier
cls=bpy.types.Operator.bl_rna_get_subclass_py(identifier,None)
out={'file':bpy.data.filepath,'operatorRNAIdentifier':identifier,'registeredClassName':None if cls is None else cls.__name__,'registeredClassModule':None if cls is None else cls.__module__,'hasNamedPythonClass':hasattr(bpy.types,'PREP44_OT_PoseSample'),'hasCanonicalRNAClass':hasattr(bpy.types,identifier),'panelRegistered':hasattr(bpy.types,'PREP44_PT_PoseReview'),'currentFrame':bpy.context.scene.frame_current,'currentSample':[bpy.context.scene.get('PREP_review_last_clip'),bpy.context.scene.get('PREP_review_last_frame'),bpy.context.scene.get('PREP_review_last_branch'),bpy.context.scene.get('PREP_review_last_variant')],'modulePresent':'preparatorio_review_v44' in sys.modules,'readOnly':True}
(ROOT/'reports/pose_review_controller_v44_20261029/registration_inspection_v44.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
