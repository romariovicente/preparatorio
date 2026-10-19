"""Persist matching phone/billboard digits with keyframes, without auto-run code.

The same 240-second day / 120-second orbit as the game is used. This is an
accelerated educational clock, not a calculation of real ephemerides.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.data.scenes['00_ARAPIRACA_CYBER_20261005'];bpy.context.window.scene=scene
col=bpy.data.collections['ARAP_07_TRANSIT']
manifest=json.loads((ROOT/'frontend/src/config/cyberWorldManifest.json').read_text(encoding='utf-8'))
clock=manifest['clock'];fps=60;day_frames=int(clock['dayPeriodSeconds']*fps)
assert day_frames%1440==0
minute_frames=day_frames//1440
from datetime import datetime,timezone,timedelta
epoch=datetime.fromtimestamp(clock['epochMs']/1000,timezone.utc)-timedelta(hours=3)
start_minutes=epoch.hour*60+epoch.minute
assert not any(o.name.startswith('CLOCK_BAKED_') for o in scene.objects),'Inspect existing baked clock before repeating'

def curves(obj):
 if not obj.animation_data or not obj.animation_data.action:return []
 return [fc for layer in obj.animation_data.action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]

for handler in list(bpy.app.handlers.frame_change_post):
 if handler.__name__=='prep_visual_clock':bpy.app.handlers.frame_change_post.remove(handler)
created=[]
for device in ['BILLBOARD','PHONE']:
 template=scene.objects['CLOCK_'+device+'_Q0'];size=template.data.size
 for quarter in range(4):
  label=scene.objects['CLOCK_'+device+'_Q'+str(quarter)]
  label.data.body='CHRONOVITAE | ORBITA '+str(quarter+1)+'/4'
  for fc in curves(label):
   for point in fc.keyframe_points:point.interpolation='CONSTANT'
   if not any(m.type=='CYCLES' for m in fc.modifiers):fc.modifiers.new('CYCLES')
 for slot,x in enumerate([-1.25,-.48,.48,1.25]):
  for digit in range(10):
   obj=template.copy();obj.data=template.data.copy();obj.animation_data_clear()
   obj.name=f'CLOCK_BAKED_{device}_DIGIT_{slot}_{digit}';obj.data.body=str(digit)
   obj.location=template.location+Vector((x*size,0,-1.25*size));col.objects.link(obj)
   last=None
   for minute in range(1441):
    total=(start_minutes+minute)%1440;h,m=divmod(total,60)
    selected=[h//10,h%10,m//10,m%10][slot];hidden=selected!=digit
    if hidden!=last or minute in [0,1440]:
     obj.hide_render=hidden;obj.hide_viewport=hidden
     frame=1+minute*minute_frames
     obj.keyframe_insert(data_path='hide_render',frame=frame);obj.keyframe_insert(data_path='hide_viewport',frame=frame)
     last=hidden
   for fc in curves(obj):
    for point in fc.keyframe_points:point.interpolation='CONSTANT'
    fc.modifiers.new('CYCLES')
   created.append(obj)
 colon=template.copy();colon.data=template.data.copy();colon.animation_data_clear()
 colon.name='CLOCK_BAKED_'+device+'_COLON';colon.data.body=':'
 colon.location=template.location+Vector((0,0,-1.25*size));colon.hide_render=False;colon.hide_viewport=False
 col.objects.link(colon);created.append(colon)

# Existing optional text documents the baked implementation; no saved runtime
# handler or preference change is needed for frame updates after re-opening.
txt=bpy.data.texts.get('PREP_VISUAL_CLOCK.py')
if txt:
 txt.clear();txt.write('# Clock baked into visibility keyframes. No script execution is needed.\n# 60 fps, one day in 240 seconds, Earth orbit in 120 seconds.\n')
scene['visual_clock_note']='Phone and billboard digits and orbit phases baked into looping visibility keyframes; no auto-run code required.'
scene.frame_end=day_frames+1
checks=[]
for seconds in [0,1/6,18,30,60,90,120,180,240,260.5,500]:
 frame=1+round(seconds*fps);scene.frame_set(frame)
 total=(start_minutes+int(round(seconds*fps)/minute_frames))%1440
 expected=f'{total//60:02d}:{total%60:02d}'
 displays=[]
 for device in ['BILLBOARD','PHONE']:
  digits=[]
  for slot in range(4):
   visible=[d for d in range(10) if not scene.objects[f'CLOCK_BAKED_{device}_DIGIT_{slot}_{d}'].hide_render]
   assert len(visible)==1,(device,slot,seconds,visible)
   digits.append(str(visible[0]))
  actual=''.join(digits[:2])+':'+''.join(digits[2:]);assert actual==expected,(seconds,actual,expected)
  phases=[q for q in range(4) if not scene.objects['CLOCK_'+device+'_Q'+str(q)].hide_render]
  assert phases==[int((seconds%120)//30)]
  displays.append(actual)
 assert displays[0]==displays[1]
 checks.append({'seconds':seconds,'frame':frame,'phone':displays[0],'billboard':displays[1],'phase':int((seconds%120)//30)+1})
scene.frame_set(1)
report={'objectsCreated':len(created),'checks':checks,'requiresAutoRun':False,'dayPeriodSeconds':clock['dayPeriodSeconds'],'orbitPeriodSeconds':clock['orbitPeriodSeconds'],'fps':fps,'savedScene':scene.name}
(ROOT/'reports/visual_clock_baked_validation_20261005.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
scenes={scene,bpy.data.scenes['01_ARAPIRACA_PROPS_20261005'],*[s for s in bpy.data.scenes if s.name.startswith('BIOME_')]}
bpy.data.libraries.write(str(ROOT/'art/blender/PREPARATORIO_ARAPIRACA_CYBER_20261005.blend'),scenes,fake_user=True,compress=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/PREPARATORIO_PROJETO_20261005.blend'))
print(json.dumps(report))
