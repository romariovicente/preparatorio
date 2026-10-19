import bpy,json,sys
from pathlib import Path
from datetime import datetime
ROOT=Path(r"C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio")
master=ROOT/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
assert Path(bpy.data.filepath).resolve()==master.resolve(),'Inspect the other open project before continuing.'
assert 'PREP_HOSPITAL_RECEPTION_20261015' not in bpy.data.scenes,'Inspect the existing hospital module instead of rebuilding.'
target=ROOT/('art/blender/checkpoints/BEFORE_HOSPITAL_20261015_'+datetime.now().strftime('%H%M%S_%f')+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(target),copy=True)
assert target.is_file()
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
state=object_state(list(bpy.data.objects))
snapshot=ROOT/'art/blender/checkpoints/HOSPITAL_BEFORE_OBJECTS_20261015.json'
assert not snapshot.exists()
snapshot.write_text(json.dumps({'hash':state_hash(state),'state':state},separators=(',',':')),encoding='utf-8')
rna=bpy.ops.export_scene.gltf.get_rna_type()
settings={p.identifier:[i.identifier for i in p.enum_items] for p in rna.properties if p.identifier in ('export_animation_mode','export_materials')}
report={'checkpoint':str(target),'bytes':target.stat().st_size,'source':str(master),'objects':len(bpy.data.objects),'scenes':len(bpy.data.scenes),'objectStateHash':state_hash(state),'exportSettings':settings,'exportAnimationProps':[p.identifier for p in rna.properties if 'animation' in p.identifier or 'nla' in p.identifier]}
(ROOT/'reports/hospital_checkpoint_20261015.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
