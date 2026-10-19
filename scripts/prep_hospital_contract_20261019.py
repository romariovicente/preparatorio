"""Derive runtime collision and door coordinates from the real Blender module."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
assert Path(bpy.data.filepath).resolve()==(ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend').resolve()
scene=bpy.data.scenes['PREP_HOSPITAL_RECEPTION_20261015']
previous=[(w,w.scene) for w in bpy.context.window_manager.windows]
old_frame=scene.frame_current
for w,_ in previous:w.scene=scene
scene.frame_set(1);bpy.context.view_layer.update()
def collider(obj):
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    return {'id':obj.name,'x':round((low[0]+high[0])/2,6),'z':round(-(low[1]+high[1])/2,6),
            'w':round(high[0]-low[0],6),'d':round(high[1]-low[1],6),
            'minY':round(low[2],6),'maxY':round(high[2],6)}
obstacles=[o for o in scene.objects if o.type=='MESH' and o.get('walk_obstacle')]
public=[o for o in obstacles if o.name.startswith('HSP15_DOOR_PUBLIC_')]
rooms=[o for o in obstacles if o.name.startswith('HSP15_DOOR_ROOM_') and o.name.endswith('_LEAF')]
static=[collider(o) for o in obstacles if o not in public and o not in rooms]
doors={o.name:{'closedCollider':collider(o)} for o in public+rooms}
hinges={}
for obj in rooms:
    hinge=obj.parent
    p=hinge.matrix_world.translation
    hinges[obj.name]={'hingeName':hinge.name,'hingePosition':[round(p.x,6),round(p.z,6),round(-p.y,6)],
                     'closedAngle':round(hinge.rotation_euler.z,6),'side':-1 if p.x<0 else 1}
scene.frame_set(31);bpy.context.view_layer.update()
for o in public+rooms:doors[o.name]['openCollider']=collider(o)
room_doors=[]
labels=['Triagem 01','Triagem 02','Entrevista','Enfermagem']
for index,o in enumerate(sorted(rooms,key=lambda o:o.name)):
    key=o.name.split('DOOR_ROOM_')[1].split('_')[0]
    info=hinges[o.name]
    room_doors.append({'id':key,'label':labels[index],'leafName':o.name,**info,
                       'openAngle':round(o.parent.rotation_euler.z,6),**doors[o.name]})
contract={'version':1,'sourceScene':scene.name,'asset':'/assets/environments/ENV_Hospital_Reception_Module_20261015.glb',
          'position':[48,0,-38],'width':36,'depth':24,'height':4.2,'opening':2.4,
          'floorY':0.012,'floorPrefixes':['HSP15_FLOOR_TILES','HSP15_SLAB'],
          'staticColliders':static,'publicDoor':{'z':12.15,'duration':1.0,'opening':2.4,
             'leaves':[{'name':o.name,**doors[o.name]} for o in public]},'roomDoors':room_doors,
          'provenance':'Derived from evaluated Blender mesh bounds in metres; glTF Y-up, Z=-BlenderY',
          'certifiedClinicalOrArchitectural':False}
scene.frame_set(old_frame);bpy.context.view_layer.update()
for window,old_scene in previous:window.scene=old_scene
target=ROOT/'frontend/src/config/hospitalReception.json'
target.write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'staticColliders':len(static),'publicDoors':len(public),'rooms':len(room_doors),
                  'roomDoorIds':[d['id'] for d in room_doors]}))
