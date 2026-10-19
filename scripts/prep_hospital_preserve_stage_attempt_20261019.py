import bpy,json,sys
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
checkpoint=json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())
original=json.loads(Path(checkpoint['stateSnapshot']).read_text())
assert state_hash(object_state([o for o in bpy.data.objects if o.name in original]))==checkpoint['stateHash']
scene=bpy.data.scenes['PREP_HOSPITAL_CITY_20261019']
scene.name='PREP_HOSPITAL_CITY_20261019_ATTEMPT1'
scene['status']='Incomplete attempt retained: material slot became None when changing link; originals preserved'
for obj in scene.objects:
    assert obj.name not in original
    obj.name='HSC19_ATTEMPT1_'+obj.name
for col in scene.collection.children:col.name='HSC19_ATTEMPT1_'+col.name
print(json.dumps({'preservedScene':scene.name,'objects':len(scene.objects),'originalObjectsUnchanged':len(original)}))
