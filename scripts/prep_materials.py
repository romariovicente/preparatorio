"""Reusable Principled PBR with deterministic procedurally generated packed ORM.
R=ambient occlusion (neutral 1); G=roughness; B=metallic. No baked AO claim.
Small packed textures preserve the procedural roughness in glTF.
"""
import bpy, math

PALETTE={
 'Concrete':((0.55,0.60,0.61,1),0.82,0.0),
 'Plaster':((0.84,0.86,0.81,1),0.72,0.0),
 'Metal':((0.085,0.13,0.16,1),0.34,0.8),
 'Glass':((0.075,0.30,0.38,1),0.18,0.15),
 'Asphalt':((0.065,0.08,0.09,1),0.92,0.0),
 'White':((0.88,0.91,0.88,1),0.66,0.0),
 'Yellow':((0.98,0.62,0.075,1),0.69,0.0),
 'Earth':((0.14,0.08,0.035,1),0.95,0.0),
 'Grass':((0.17,0.35,0.16,1),0.87,0.0),
 'Accent':((0.02,0.46,0.49,1),0.5,0.25)
}

def create_materials():
    result={}
    group=bpy.data.node_groups.get('glTF Material Output')
    if group is None:
        from io_scene_gltf2.blender.com.material_helpers import create_settings_group
        group=create_settings_group('glTF Material Output')
    for key,(color,rough,metal) in PALETTE.items():
        name='MAT_PREP_'+key
        if bpy.data.materials.get(name):
            mat=bpy.data.materials[name]
            if not mat.get('prep_generated'): raise ValueError('Existing material collision: '+name)
            result[key]=mat; continue
        mat=bpy.data.materials.new(name); mat.use_nodes=True; mat.diffuse_color=color
        mat['prep_generated']=True; mat['ORM']='R=1 (neutral AO), G=roughness, B=metallic'
        nodes=mat.node_tree.nodes; links=mat.node_tree.links
        bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Base Color'].default_value=color
        bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
        if key=='Glass':
            bs.inputs['Transmission Weight'].default_value=0.28
            bs.inputs['IOR'].default_value=1.45
        img=bpy.data.images.new('TEX_PREP_'+key+'_ORM',width=32,height=32,alpha=True)
        img.colorspace_settings.name='Non-Color'
        pixels=[]
        for y in range(32):
            for x in range(32):
                noise=math.sin(x*12.9898+y*78.233)*43758.5453
                r=max(0.02,min(1,rough+((noise%1)-0.5)*0.06))
                pixels.extend((1,r,metal,1))
        img.pixels.foreach_set(pixels); img.pack()
        tex=nodes.new('ShaderNodeTexImage'); tex.image=img; tex.location=(-600,0)
        split=nodes.new('ShaderNodeSeparateColor'); split.mode='RGB'; split.location=(-350,0)
        links.new(tex.outputs['Color'],split.inputs['Color'])
        links.new(split.outputs['Green'],bs.inputs['Roughness'])
        links.new(split.outputs['Blue'],bs.inputs['Metallic'])
        ao=nodes.new('ShaderNodeGroup'); ao.node_tree=group; ao.location=(-100,-350)
        links.new(split.outputs['Red'],ao.inputs['Occlusion'])
        result[key]=mat
    return result

if __name__=='__main__': print(list(create_materials()))
