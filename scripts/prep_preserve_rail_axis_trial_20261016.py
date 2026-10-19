import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
rp=ROOT/'reports/rail_assets_20261016/SUP_trem_composicao_obj_20261016.json';r=json.loads(rp.read_text(encoding='utf-8'))
assert r['status']=='failed_requires_inspection' and not r['parts']
objs=[o for o in bpy.data.objects if o.get('rail_owner')=='prep_train_import_20261016_v1' and o.get('rail_stage')=='source']
assert len(objs)==1 and objs[0]['rail_source_relative']==r'Trem\model_0.obj'
s=bpy.data.scenes.new('FAILED_PREP_RAIL_AXIS_20261016');s['purpose']='First OBJ axis import preserved; XY inverted by NEGATIVE_Y; not runtime.'
for o in objs:
 for c in list(o.users_collection):c.objects.unlink(o)
 s.collection.objects.link(o);o['rail_stage']='failed_axis_trial';o.name='FAILED_AXIS_'+o.name
r['preservedFailedAxisScene']=s.name;rp.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('Owned failed axis trial preserved. Next import uses native Y-forward Z-up coordinates.')
