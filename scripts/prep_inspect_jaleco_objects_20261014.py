import bpy,json
rows=[]
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and obj.name.startswith('ROMARIO_'):
        rows.append({'name':obj.name,'source_node':obj.get('asset_node_name'),'dimensions':list(obj.dimensions),
                     'data_name':obj.data.name,'vertices':len(obj.data.vertices),'hidden':obj.hide_render,
                     'modifiers':[m.type for m in obj.modifiers]})
print(json.dumps(rows))
