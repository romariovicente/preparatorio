"""Read-only independent validation of the saved master and hospital module."""
import bpy,hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261015.blend'
assert bpy.app.background and Path(bpy.data.filepath).resolve()==MASTER.resolve()
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
path=ROOT/'reports/HOSPITAL_RECEPTION_20261015.json'
report=json.loads(path.read_text(encoding='utf-8'))
assert len(bpy.data.scenes)==report['allScenes']
assert len(bpy.data.objects)==report['allObjects']
scene=bpy.data.scenes[report['scene']]
assert len(scene.objects)==report['sceneObjects']
assert len(bpy.data.scenes[report['roundtrip']['scene']].objects)==report['roundtrip']['objects']
baseline=json.loads((ROOT/'art/blender/checkpoints/HOSPITAL_BEFORE_OBJECTS_20261015.json').read_text(encoding='utf-8'))
assert all(name in bpy.data.objects for name in baseline['state'])
stored=object_state([bpy.data.objects[name] for name in baseline['state']])
diff=[name for name in baseline['state'] if baseline['state'][name]!=stored[name]]
assert not diff,'Stored object channels differ: '+str(diff[:20])
assert state_hash(stored)==baseline['hash']
glb=Path(report['glb'])
assert glb.stat().st_size==report['glbBytes']
assert hashlib.sha256(glb.read_bytes()).hexdigest()==report['glbSha256']
report['savedReadBack']={'passed':True,'timeLocal':datetime.now().astimezone().isoformat(timespec='seconds'),
    'blenderVersion':bpy.app.version_string,'autoexecDisabled':True,'scenes':len(bpy.data.scenes),
    'objects':len(bpy.data.objects),'previousObjectChannelsMatch':True,'previousObjectCount':len(stored),
    'masterBytes':MASTER.stat().st_size,'masterModifiedByReadback':False}
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PREP_HOSPITAL_READBACK_OK '+json.dumps(report['savedReadBack']))
