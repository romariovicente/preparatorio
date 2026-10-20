import bpy,json
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
scenes=[{'name':s.name,'objects':len(s.objects),'properties':{k:str(s[k])[:240] for k in s.keys() if not k.startswith('_')},
 'armatures':[{'name':o.name,'bones':len(o.data.bones),'parent':o.parent.name if o.parent else None,'properties':{k:str(o[k])[:180] for k in o.keys() if not k.startswith('_')}} for o in s.objects if o.type=='ARMATURE'][:25]} for s in bpy.data.scenes]
(ROOT/'reports/CHARACTER_SCENE_INVENTORY_20261019.json').write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'name':s['name'],'objects':s['objects'],'armatures':len(s['armatures'])} for s in scenes],ensure_ascii=False))
