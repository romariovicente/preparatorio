"""Read the live master before any hospital integration changes."""
import bpy, json
from pathlib import Path
from mathutils import Vector
ROOT = Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
def data(obj):
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box] if obj.type == 'MESH' else []
    return {'name':obj.name,'type':obj.type,'parent':obj.parent.name if obj.parent else None,
            'location':list(obj.location),'dimensions':list(obj.dimensions),
            'hideRender':obj.hide_render,'hideViewport':obj.hide_viewport,
            'collections':[c.name for c in obj.users_collection],
            'bounds':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]} if points else None}
report={'file':bpy.data.filepath,'dirty':bpy.data.is_dirty,'objects':len(bpy.data.objects),
        'scenes':len(bpy.data.scenes),'activeScene':bpy.context.scene.name,'candidateScenes':[]}
for scene in bpy.data.scenes:
    if any(s in scene.name for s in ('HOSPITAL','ARAPIRACA_CYBER','JALECO','CHARACTER')):
        matching=[o for o in scene.objects if 'HOSP' in o.name.upper() or 'HOSPITAL' in o.name.upper()]
        report['candidateScenes'].append({'name':scene.name,'objects':len(scene.objects),
             'hospitalObjects':len(matching),'sample':[data(o) for o in matching[:30]]})
(ROOT/'reports/HOSPITAL_CITY_AUDIT_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='candidateScenes'}))
for scene in report['candidateScenes']:
    print(json.dumps({k:v for k,v in scene.items() if k!='sample'}))
    print(json.dumps(scene['sample'][:4]))
