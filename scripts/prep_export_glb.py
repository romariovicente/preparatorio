"""Export selected PREP meshes through a temporary scene without altering originals."""
import bpy, json, struct
from pathlib import Path

def export_assets(objects,path,center_single=False):
    objects=list(objects); path=Path(path)
    if path.exists(): raise FileExistsError('Refusing overwrite: '+str(path))
    if not objects or any(o.type!='MESH' or not o.get('prep_asset') for o in objects):
        raise ValueError('Explicit PREP mesh selection required')
    if any(o.parent or o.animation_data for o in objects):
        raise ValueError('This static kit exporter requires independent roots')
    if center_single and len(objects)!=1: raise ValueError('Only individual assets may be centered')
    original_scene=bpy.context.window.scene
    temp=bpy.data.scenes.new('PREP_EXPORT_TEMP')
    copies=[]; names={}
    try:
        bpy.context.window.scene=temp
        for source in objects:
            copy=source.copy(); temp.collection.objects.link(copy); copies.append(copy)
            names[source.name]=source.name
            # Preserve exact exported name without renaming source objects.
            copy['prep_asset_name']=source.name
            if center_single: copy.location=(0,0,0)
            copy.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]
        path.parent.mkdir(parents=True,exist_ok=True)
        status=bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
          export_yup=True,export_apply=True,export_animations=False,export_cameras=False,
          export_lights=False,export_extras=True,export_materials='EXPORT',export_texcoords=True,export_normals=True)
        if status!={'FINISHED'} or not path.is_file(): raise RuntimeError('Export did not finish')
        # Copies receive Blender suffixes. Restore canonical names in GLB JSON only.
        raw=path.read_bytes(); length,kind=struct.unpack_from('<II',raw,12)
        doc=json.loads(raw[20:20+length])
        for node in doc.get('nodes',[]):
            canonical=node.get('extras',{}).get('prep_asset_name')
            if canonical: node['name']=canonical
        js=json.dumps(doc,separators=(',',':')).encode(); js+=b' '*((-len(js))%4)
        tail=raw[20+length:]
        path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(js)+len(tail))+struct.pack('<II',len(js),kind)+js+tail)
        return {'path':str(path),'bytes':path.stat().st_size,'assets':[o.name for o in objects]}
    finally:
        bpy.context.window.scene=original_scene
        for obj in copies: bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.scenes.remove(temp)

if __name__=='__main__':
    raise RuntimeError('Import export_assets and supply an explicit non-existing output path')
