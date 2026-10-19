import bpy, runpy, sys, json, traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1]
entries=json.loads((root/'reports/supplied_assets_inventory.json').read_text(encoding='utf-8'))
pending=[];seen=set()
for i,e in sorted(enumerate(entries),key=lambda x:x[1]['triangles']):
    if e['relative'].endswith('Meshy_AI_Island_Game_Map_0929153753_image-to-3d-texture.glb') or e['sha256'] in seen:continue
    seen.add(e['sha256'])
    key='SUP_'+Path(e['relative']).stem.strip().replace(' ','_').replace('-','_')
    rp=root/'reports/supplied'/f'{key}.json'
    if rp.exists() and json.loads(rp.read_text(encoding='utf-8')).get('status')=='validated':continue
    pending.append(i)
original_scene=bpy.context.window.scene
def next_asset():
    if not pending:
        bpy.context.window.scene=original_scene
        return None
    index=pending.pop(0)
    bpy.context.window.scene=bpy.data.scenes.new('PREP_TEMP_ASSET')
    types=['objects','scenes','collections','meshes','materials','images','armatures','actions','cameras','lights','worlds','node_groups']
    before={k:set(getattr(bpy.data,k)) for k in types}
    temp=bpy.context.scene
    temp.world=bpy.data.worlds.new('PREP_TEMP_WORLD')
    saved_args=sys.argv[:]
    try:
        sys.argv=['blender','--',str(index)]
        runpy.run_path(str(root/'scripts/prep_import_supplied.py'),run_name='__main__')
    except Exception:
        (root/'reports'/f'batch_error_{index}.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        sys.argv=saved_args
        bpy.context.window.scene=original_scene
        for kind in types:
            created=set(getattr(bpy.data,kind))-before[kind]
            if created:bpy.data.batch_remove(ids=created)
        bpy.data.scenes.remove(temp)
    return 1.0
bpy.app.timers.register(next_asset,first_interval=1.0)
print('Queued',len(pending),'assets in isolated temporary scenes')

