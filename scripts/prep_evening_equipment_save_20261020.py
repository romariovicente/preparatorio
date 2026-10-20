import bpy,json,sys
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
checkpoint=json.loads((ROOT/'reports/EVENING_ADDITIONS_CHECKPOINT_20261020.json').read_text())
prior=json.loads(Path(checkpoint['stateSnapshot']).read_text())
current=object_state([o for o in bpy.data.objects if o.name in prior])
assert current==prior,'Inspect changed original channels before saving'
scene=bpy.data.scenes['PREP_HOSPITAL_EQUIPMENT_20261020']
for w in bpy.context.window_manager.windows:
    w.scene=scene
    for area in w.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
report=json.loads((ROOT/'reports/HOSPITAL_EQUIPMENT_BLENDER_20261020.json').read_text())
report.update({'masterSaved':True,'master':str(MASTER),'masterBytes':MASTER.stat().st_size,'savedLibraryProbePending':True,'priorObjectsPreserved':len(prior),'priorStateHash':state_hash(current),'sourcePreviewReviewed':True,'placementPreviewReviewed':True,'assessment':'14.33 cm ambient thermohygrometer rests on existing reception countertop, unchanged static source digits; no clinical or live measurement feature. Original hospital/chairs/rig channels retained.','savedAtLocal':datetime.now().astimezone().isoformat()})
(ROOT/'reports/HOSPITAL_EQUIPMENT_BLENDER_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(MASTER),'bytes':MASTER.stat().st_size,'objectsPreserved':len(prior),'scenes':len(bpy.data.scenes)}))
