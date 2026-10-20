import bpy,json,sys
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
baseline=json.loads((ROOT/'reports/INTEGRATED_BEFORE_CHAIRS_20261020.json').read_text())
before=json.loads(Path(baseline['stateSnapshot']).read_text())
current=object_state([o for o in bpy.data.objects if o.name in before])
assert current==before,'Prior integrated object channels changed; preserve and investigate'
scene=bpy.data.scenes['PREP_HOSPITAL_CHAIRS_CITY_20261020']
for w in bpy.context.window_manager.windows:
    w.scene=scene
    for area in w.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),compress=True)
# Blender cannot inspect its currently open file through libraries.load.
# A separate factory-startup Blender process checks the saved library names.
report=json.loads((ROOT/'reports/HOSPITAL_CHAIRS_BLENDER_20261020.json').read_text())
report.update({'masterSaved':True,'master':str(MASTER),'masterBytes':MASTER.stat().st_size,'masterLibraryReadValidated':False,'savedLibraryProbePending':True,'priorObjectCount':len(before),'priorObjectChannelsPreserved':True,'priorStateHash':state_hash(current),'blenderReceptionPreviewInspected':True,'previewAssessment':'Ten lounge chairs face shared waiting aisle; four consultation chairs face desks. Curved upholstered source retained; no clinical/architectural certification. Original hospital/door animation scenes retained.','savedAtLocal':datetime.now().astimezone().isoformat()})
(ROOT/'reports/HOSPITAL_CHAIRS_BLENDER_20261020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'saved':str(MASTER),'bytes':MASTER.stat().st_size,'oldObjectsPreserved':len(before),'scene':scene.name}))
