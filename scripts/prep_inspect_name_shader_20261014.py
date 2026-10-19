import bpy,json
rows=[]
for obj in bpy.context.scene.objects:
    if 'COAT_NAME' in obj.name:
        for mat in obj.data.materials:
            rows.append({'object':obj.name,'nodes':[(n.name,n.type) for n in mat.node_tree.nodes],
                         'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links],
                         'images':[(n.image.name,list(n.image.size)) for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
print(json.dumps(rows))
