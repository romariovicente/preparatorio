"""Blender 5.2: prepare explicitly supplied static assets; never apply location."""
import bpy, re

def prepare(objects, apply_transforms=False):
    report=[]
    for obj in objects:
        if obj.type!='MESH' or not obj.get('prep_asset'): continue
        if obj.library or obj.data.library: raise ValueError('Linked asset is read-only')
        name=re.sub(r'[^A-Za-z0-9_.-]', '_', obj.name)
        if name!=obj.name and bpy.data.objects.get(name): raise ValueError('Name collision: '+name)
        obj.name=name
        if obj.data.users>1: obj.data=obj.data.copy()
        obj.data.name='MESH_'+obj.name[4:]
        if apply_transforms:
            if obj.parent or obj.children or obj.constraints or obj.animation_data or obj.data.shape_keys:
                raise ValueError('Unsafe transform application: '+obj.name)
            with bpy.context.temp_override(object=obj,active_object=obj,selected_objects=[obj],selected_editable_objects=[obj]):
                bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        for face in obj.data.polygons: face.use_smooth=True
        bevel=obj.modifiers.get('PREP_Bevel') or obj.modifiers.new('PREP_Bevel','BEVEL')
        bevel.width=0.015; bevel.segments=2; bevel.limit_method='ANGLE'
        bevel.harden_normals=True
        normal=obj.modifiers.get('PREP_WeightedNormals') or obj.modifiers.new('PREP_WeightedNormals','WEIGHTED_NORMAL')
        normal.keep_sharp=True; normal.weight=50
        report.append(obj.name)
    return report

if __name__=='__main__': print(prepare(list(bpy.context.selected_objects)))
