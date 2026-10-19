import bpy,json
from mathutils import Vector
for name in ['PREP_FAUNA_FOX_20261016','PREP_FAUNA_QA_FOX_20261016']:
 s=bpy.data.scenes[name]
 for w in bpy.context.window_manager.windows:w.scene=s
 result={'scene':name,'objects':len(s.objects),'arms':[],'frames':{}}
 for o in s.objects:
  if o.type=='ARMATURE':
   ad=o.animation_data
   result['arms'].append({'name':o.name,'action':ad.action.name if ad and ad.action else None,'tracks':[{'name':t.name,'mute':t.mute,'strips':[{'action':st.action.name,'frame':list(st.action_frame_start for k in [0])+[st.action_frame_end],'start':st.frame_start,'end':st.frame_end} for st in t.strips]} for t in ad.nla_tracks] if ad else []})
 for f in [0,1,2]:
  s.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();points=[]
  for o in s.objects:
   if o.type!='MESH':continue
   ev=o.evaluated_get(dg);m=ev.to_mesh();points.extend(ev.matrix_world@v.co for v in m.vertices);ev.to_mesh_clear()
  result['frames'][f]=[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
 print(json.dumps(result))
