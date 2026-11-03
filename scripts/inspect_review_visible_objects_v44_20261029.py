import bpy,json,numpy as np
from mathutils import Vector
window=bpy.context.window or bpy.context.window_manager.windows[0];layer=window.view_layer
rows=[]
for obj in window.scene.objects:
    if obj.type!='MESH' and obj.visible_get(view_layer=layer):
        rows.append({'name':obj.name,'type':obj.type,'displayType':obj.display_type,'instanceType':obj.instance_type,'dimensions':list(obj.dimensions),'inFront':obj.show_in_front,'armatureDisplay':obj.data.display_type if obj.type=='ARMATURE' else None})
    if obj.type=='MESH' and obj.visible_get(view_layer=layer):
        points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
        bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
        ev=obj.evaluated_get(layer.depsgraph);mesh=ev.to_mesh();P=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',P);M=np.array(ev.matrix_world);Q=P.reshape(-1,3)@M[:3,:3].T+M[:3,3];ev.to_mesh_clear()
        rows.append({'name':obj.name,'dimensions':list(obj.dimensions),'worldBounds':bounds,'evaluatedBounds':[[float(Q[:,i].min()),float(Q[:,i].max())] for i in range(3)],'vertexCount':len(obj.data.vertices),'hideRender':obj.hide_render,'parent':None if obj.parent is None else obj.parent.name})
print(json.dumps(rows))
