import bpy,json
from mathutils import Vector
print(json.dumps({'contextScene':bpy.context.scene.name,'window':str(bpy.context.window),'windows':[(w.scene.name,w.view_layer.name) for w in bpy.context.window_manager.windows],'viewLayer':bpy.context.view_layer.name}))
for sn in ['PREP_FAUNA_FOX_20261016','PREP_FAUNA_QA_FOX_20261016']:
 s=bpy.data.scenes[sn]; w=list(bpy.context.window_manager.windows)[0];w.scene=s
 with bpy.context.temp_override(window=w,scene=s,view_layer=s.view_layers[0]):
  dg=bpy.context.evaluated_depsgraph_get()
  print('DG',dg.scene.name,dg.view_layer.name)
  print(json.dumps([{'name':o.name,'type':o.type,'vertices':len(o.data.vertices) if o.type=='MESH' else None,'mods':[(m.type,m.object.name if m.type=='ARMATURE' and m.object else None) for m in o.modifiers],'loc':list(o.location),'scale':list(o.scale)} for o in s.objects]))
  for frame in [1,12,35]:
   s.frame_set(frame);bpy.context.view_layer.update()
   pts=[];ad=[]
   for o in s.objects:
    if o.type=='MESH':
     ev=o.evaluated_get(dg);m=ev.to_mesh();pts.extend(ev.matrix_world@v.co for v in m.vertices);ev.to_mesh_clear()
    elif o.type=='ARMATURE':ad.append({'action':o.animation_data.action.name,'slot':str(o.animation_data.action_slot),'bones':[list(b.matrix.translation) for b in list(o.pose.bones)[10:15]]})
   print(json.dumps({'scene':sn,'frame':frame,'lo':[min(p[i] for p in pts) for i in range(3)],'hi':[max(p[i] for p in pts) for i in range(3)],'pose':ad}))
