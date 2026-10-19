"""Append only verified game derivatives to the existing live city through MCP."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005']
catalog={a['id']:a for a in json.loads((ROOT/'frontend/src/config/newDeliveryAssets.json').read_text(encoding='utf-8'))}
config=json.loads((ROOT/'frontend/src/config/newDeliveryWorld.json').read_text(encoding='utf-8'))
parent=bpy.data.collections.get('ARAP_14_NEW_DELIVERY_20261007')
if not parent:
    parent=bpy.data.collections.new('ARAP_14_NEW_DELIVERY_20261007');scene.collection.children.link(parent)
loaded={};created=[]
def get_collection(asset):
    if asset['id'] in loaded:return loaded[asset['id']]
    assert asset['status']=='validated'
    with bpy.data.libraries.load(asset['blend'],link=False) as (available,items):
        assert asset['collection'] in available.collections
        items.collections=[asset['collection']]
    collection=items.collections[0];loaded[asset['id']]=collection
    return collection
def make_instance(name,asset,point,yaw=0):
    current=bpy.data.objects.get(name)
    if current:return current
    obj=bpy.data.objects.new(name,None);parent.objects.link(obj);obj.instance_type='COLLECTION';obj.instance_collection=get_collection(asset)
    obj.location=(point[0],-point[2],point[1]);obj.rotation_euler.z=yaw;obj['asset_id']=asset['id'];obj['sha256']=asset['sha256'];created.append(name)
    return obj
for item in config['compositions']:
    asset=catalog[item['assetId']];obj=make_instance('DELIVERY_'+item['id'],asset,item['position'],item.get('rotation',[0,0,0])[1])
    if 'height' in item:obj.scale*=item['height']/asset['height']
route=config['routeOverrides']['bus'];bus=make_instance('DELIVERY_BUS_CIRCULAR',catalog[config['dynamicReplacements']['bus']],[0,.02,35])
seconds=0;frame=1;fps=scene.render.fps;points=route['points']
for i,p in enumerate(points+[points[0]]):
    if i:
        previous=points[(i-1)%len(points)];seconds+=math.hypot(p['x']-previous['x'],p['z']-previous['z'])/route['speed']
    next_point=points[(i+1)%len(points)];yaw=math.atan2(next_point['x']-p['x'],next_point['z']-p['z'])
    frame=1+round(seconds*fps);bus.location=(p['x'],-p['z'],.02);bus.rotation_euler.z=yaw
    bus.keyframe_insert(data_path='location',frame=frame);bus.keyframe_insert(data_path='rotation_euler',frame=frame)
    if any(math.hypot(s['position']['x']-p['x'],s['position']['z']-p['z'])<.01 for s in route['stops']):
        seconds+=route['dwell'];bus.keyframe_insert(data_path='location',frame=1+round(seconds*fps));bus.keyframe_insert(data_path='rotation_euler',frame=1+round(seconds*fps))
bus['timeline_route']='Circular PREPARATÓRIO, stops matched to frontend'
scene.frame_end=max(scene.frame_end,frame)
# Blender 5.2 stores curves in channel bags under action layers.
if bus.animation_data and bus.animation_data.action:
    action=bus.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
for obj in scene.objects:
    if any(obj.name.startswith(p) for p in config['hidePrefixes']) or obj.name.startswith('VEH_Bus_Circular'):
        obj.hide_set(True);obj.hide_render=True
scene.frame_set(1)
for window in bpy.context.window_manager.windows:window.scene=scene
dest=ROOT/'art/blender/PREPARATORIO_PROJETO_20261007.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'saved':str(dest),'created':created,'sceneObjects':len(scene.objects),'cityDeliveryCollection':parent.name,'busAnimationEndFrame':frame,'placements':config['compositions']}
(ROOT/'reports/live_delivery_20261007.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='placements'},ensure_ascii=False))
