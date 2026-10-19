import bpy,json,sys
from pathlib import Path
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
before=json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())
original=json.loads(Path(before['stateSnapshot']).read_text())
actual=object_state([o for o in bpy.data.objects if o.name in original])
diff=[n for n in original if original[n]!=actual[n]]
report={'preservationDiff':diff,'actors':[]}
for name in ('CHAR_ROMARIO_DEMO_ROOT','CHAR_ANA_DEMO_ROOT'):
    root=bpy.data.objects[name]
    tree=[root]+list(root.children_recursive)
    actor={'name':name,'location':list(root.location),'scale':list(root.scale),'rotation':list(root.rotation_euler),
           'objects':[{'name':o.name,'type':o.type,'hideRender':o.hide_render,'parent':o.parent.name if o.parent else None} for o in tree],
           'rigs':[]}
    for o in tree:
        if o.type=='ARMATURE':
            animation=o.animation_data
            actor['rigs'].append({'name':o.name,'bones':len(o.data.bones),
                'action':animation.action.name if animation and animation.action else None,
                'nla':[{'track':t.name,'strips':[{'name':s.name,'action':s.action.name,'frames':[s.frame_start,s.frame_end],
                       'slot':s.action_slot.identifier if s.action_slot else None} for s in t.strips]} for t in animation.nla_tracks] if animation else []})
    report['actors'].append(actor)
report['walkActions']=[{'name':a.name,'frameRange':list(a.frame_range),'slots':[s.identifier for s in a.slots]} for a in bpy.data.actions if 'Walk' in a.name]
(ROOT/'reports/HOSPITAL_ACTOR_AUDIT_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'preservationDiff':diff,'actors':[{'name':a['name'],'rigs':a['rigs']} for a in report['actors']]}))
