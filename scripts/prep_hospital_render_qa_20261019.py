"""Inspect actual skinned actors and render the integrated hospital stage."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\Senac\Documents\Codex\2026-09-28\referenced-chatgpt-conversation-this-is-an\outputs\preparatorio')
MASTER=ROOT/'art/blender/PREPARATORIO_PROJETO_20261016.blend'
assert Path(bpy.data.filepath).resolve()==MASTER.resolve()
scene=bpy.data.scenes['PREP_HOSPITAL_CITY_20261019']
for window in bpy.context.window_manager.windows:window.scene=scene
checkpoint=json.loads((ROOT/'reports/HOSPITAL_CITY_CHECKPOINT_20261019.json').read_text())
old=json.loads(Path(checkpoint['stateSnapshot']).read_text())
sys.path.insert(0,str(ROOT/'scripts'))
from prep_object_state_20261015 import object_state,state_hash
contract=json.loads((ROOT/'frontend/src/config/hospitalReception.json').read_text())
assert contract['position']==[48,.26,-38]
samples=[];vertices_checked=0;actors=[]
for key in ('ROMARIO','ANA'):
    root=bpy.data.objects['HSC19_'+key+'_CHAR_'+key+'_DEMO_ROOT']
    tree=[root]+list(root.children_recursive)
    assert len(tree)==31, 'Unexpected retained/duplicated actor descendants'
    rigs=[o for o in tree if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==55
    actors.append({'name':root['demo_name'],'root':root.name,'rig':rigs[0].name,'objects':len(tree),'bones':55,
        'visibleHelpers':[o.name for o in tree if o.get('character_helper_hidden') and not o.hide_render]})
    assert not actors[-1]['visibleHelpers']
    visible=[o for o in tree if o.type=='MESH' and not o.hide_render]
    for frame in (1,61,121,181,301,361,416,450):
        scene.frame_set(frame);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        points=[]
        for obj in visible:
            evaluated=obj.evaluated_get(dg);mesh=evaluated.to_mesh()
            for vertex in mesh.vertices:
                p=evaluated.matrix_world@vertex.co
                assert all(math.isfinite(c) for c in p), 'Non-finite skinned vertex'
                points.append(p)
            vertices_checked+=len(mesh.vertices);evaluated.to_mesh_clear()
        low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
        samples.append({'actor':key,'frame':frame,'minXYZ':low,'maxXYZ':high,'height':high[2]-low[2],
                        'footFromFloor':low[2]-.272,'width':high[0]-low[0],'depth':high[1]-low[1]})
assert all(-.007<s['footFromFloor']<.08 for s in samples), 'Foot contact requires review before delivery'
scene.frame_set(180);scene.camera=bpy.data.objects['HSC19_CAM_RECEPTION']
assert state_hash(object_state([o for o in bpy.data.objects if o.name in old]))==checkpoint['stateHash']
previews=[]
for key,camera,frame in [('reception','HSC19_CAM_RECEPTION',180),('uniform','HSC19_CAM_UNIFORM',180),('entrance','HSC19_CAM_ENTRANCE',75)]:
    path=ROOT/f'reports/hospital_city_{key}_20261019.png'
    assert not path.exists(), 'Inspect the existing preview instead of overwriting it'
    scene.camera=bpy.data.objects[camera];scene.frame_set(frame);scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True,scene=scene.name);assert path.exists();previews.append(str(path))
scene.frame_set(180);scene.camera=bpy.data.objects['HSC19_CAM_RECEPTION']
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER),check_existing=False)
report={'scene':scene.name,'actors':actors,'framesSampled':8,'skinnedVerticesChecked':vertices_checked,
        'samples':samples,'minFootOffset':min(s['footFromFloor'] for s in samples),
        'maxFootOffset':max(s['footFromFloor'] for s in samples),'originalObjectsPreserved':len(old),
        'originalStateHash':checkpoint['stateHash'],'previews':previews,'master':str(MASTER),
        'masterBytes':MASTER.stat().st_size,'passedNumerical':True,'renderInspectionPending':True,
        'limitations':['Finite vertices and foot placement do not prove absence of every cloth/body intersection',
                       'Demonstration actors do not establish production multiplayer or NPC intelligence']}
(ROOT/'reports/HOSPITAL_CITY_QA_20261019.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('samples','actors')}))
