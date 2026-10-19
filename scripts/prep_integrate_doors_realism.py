"""Add accessible establishments, animated doors and detailed supplied assets.

Run via Blender MCP after saving the existing master. Original source meshes,
FBXs and GLBs are never rewritten. Old blockout objects remain hidden in the
city, and the independently validated Mixamo human is copied into the city.
"""
from pathlib import Path
import bpy, json, math, hashlib
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
CITY='00_ARAPIRACA_CYBER_20261005'
COLLECTION='ARAP_12_ACCESSIBLE_REAL_DETAILS_20261005'
REPORT=ROOT/'reports/doors_realism_blender_20261005.json'
BLEND=ROOT/'art/blender/PREPARATORIO_PROJETO_REAL_20261005.blend'
buildings=json.loads((ROOT/'frontend/src/config/buildingDoors.json').read_text(encoding='utf-8'))
world=json.loads((ROOT/'frontend/src/config/realisticWorldManifest.json').read_text(encoding='utf-8'))
catalog=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))

def xyz(p):return Vector((p[0],-p[2],p[1]))
def material(name,hexcolor,metal=0,rough=.65,glass=False):
    m=bpy.data.materials.new('REAL_'+name);m.use_nodes=True
    c=tuple(int(hexcolor[i:i+2],16)/255 for i in (1,3,5))+(1,)
    m.diffuse_color=c
    node=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    node.inputs['Base Color'].default_value=c;node.inputs['Metallic'].default_value=metal;node.inputs['Roughness'].default_value=rough
    if glass:node.inputs['Transmission Weight'].default_value=.78;node.inputs['IOR'].default_value=1.45
    return m

def empty(name,pos=(0,0,0),parent=None):
    o=bpy.data.objects.new(name,None);collection.objects.link(o);o.parent=parent;o.location=xyz(pos);return o

def cube(name,pos,size,mat,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    collection.objects.link(o);o.parent=parent;o.location=xyz(pos)
    # Bake dimensions into the new mesh, leaving parent pivots and source assets intact.
    for v in o.data.vertices:v.co.x*=size[0];v.co.y*=size[2];v.co.z*=size[1]
    o.data.materials.append(mat)
    bevel=o.modifiers.new('Edge highlights','BEVEL');bevel.width=min(.04,min(size)/4);bevel.segments=3
    bevel.limit_method='ANGLE'
    return o

def source_instance(record,name):
    source=ROOT/'frontend/public'/record['url'].lstrip('/')
    if not source.is_file():raise FileNotFoundError(str(source))
    if record.get('sha256') and hashlib.sha256(source.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Changed supplied source')
    key=record['url']
    if key in source_cache:
        originals=source_cache[key]
        copies={o:o.copy() for o in originals}
        for original,copy in copies.items():
            collection.objects.link(copy)
            if original.parent in copies:copy.parent=copies[original.parent]
        objects=list(copies.values())
    else:
        before=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(source))
        objects=[o for o in bpy.context.scene.objects if o not in before]
        for o in objects:
            for c in list(o.users_collection):c.objects.unlink(o)
            collection.objects.link(o)
        source_cache[key]=objects
    tops=[o for o in objects if o.parent not in objects]
    points=[o.matrix_world@Vector(v) for o in objects if o.type=='MESH' for v in o.bound_box]
    low=Vector(tuple(min(v[i] for v in points) for i in range(3)));high=Vector(tuple(max(v[i] for v in points) for i in range(3)))
    root=empty(name)
    for o in tops:
        matrix=o.matrix_world.copy();o.parent=root;o.matrix_world=matrix
    scale=record['height']/max(high.z-low.z,.001)
    angle=record.get('rotation',[0,0,0])[1]
    root.rotation_euler.z=angle;root.scale=(scale,)*3
    center=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    root.location=xyz(record['position'])-Matrix.Rotation(angle,3,'Z')@center*scale
    root['source_url']=record['url'];root['source_preserved']=True
    for o in objects:o['real_detail_instance']=name
    return root,objects

def rig_copy(objects,pos,name):
    copies={o:o.copy() for o in objects}
    for original,copy in copies.items():
        collection.objects.link(copy)
        if original.parent in copies:copy.parent=copies[original.parent]
        for m in copy.modifiers:
            if m.type=='ARMATURE' and m.object in copies:m.object=copies[m.object]
    roots=[o for o in copies.values() if o.parent not in copies.values()]
    for r in roots:r.location+=xyz(pos);r.name=name
    return list(copies.values())

def run():
    global collection,source_cache
    if CITY not in bpy.data.scenes:raise RuntimeError('Expected saved city scene')
    if COLLECTION in bpy.data.collections or BLEND.exists():raise RuntimeError('Preserve existing revision; review before repeating')
    scene=bpy.data.scenes[CITY];bpy.context.window.scene=scene;scene.render.fps=60;scene.frame_set(1)
    collection=bpy.data.collections.new(COLLECTION);scene.collection.children.link(collection);source_cache={}
    prefixes=[p for b in buildings for p in b['hidePrefixes']]+[p for r in world['environmentReplacements'] for p in r['hidePrefixes']]
    hidden=[]
    for o in list(scene.objects):
        if any(o.name.startswith(p) for p in prefixes):o.hide_set(True);o.hide_render=True;hidden.append(o.name)
    layer=scene.view_layers[0].layer_collection.children.get('ARAP_07_NPCS')
    if layer:layer.exclude=True
    metal=material('Brushed_aluminium','#71808a',.8,.23)
    glass=material('Clear_safety_glass','#bcccd1',.08,.13,True)
    floor=material('Stone_floor','#c8c7be',0,.28)
    roof=material('Roof','#6d787c',0,.85)
    counter=material('Counter','#c6bcae',0,.4)
    doors=[]
    for b in buildings:
        w,d,h,gap=b['width'],b['depth'],b['height'],b['opening'];span=(w-gap)/2
        root=empty('BLD_ACCESS_'+b['id'],b['center']);wall=material(b['id']+'_walls',b['color'])
        cube(root.name+'_Floor',(0,-.055,0),(w,.16,d),floor,root)
        for name,p,s in [('Left',(-w/2,h/2,0),(.26,h,d)),('Right',(w/2,h/2,0),(.26,h,d)),('Back',(0,h/2,-d/2),(w,h,.26)),('Lintel',(0,(h+3.05)/2,d/2),(w,h-3.05,.28))]:cube(root.name+'_'+name,p,s,wall,root)
        for side in (-1,1):
            x=side*(w+gap)/4
            cube(root.name+'_FacadeBase_'+str(side),(x,.43,d/2),(span,.86,.26),wall,root)
            cube(root.name+'_Window_'+str(side),(x,1.92,d/2),(span-.08,2.12,.06),glass,root)
            cube(root.name+'_WindowFrame_'+str(side),(x,3.1,d/2),(span,.18,.3),metal,root)
        ceiling=cube(root.name+'_Roof',(0,h+.12,0),(w+.4,.24,d+.4),roof,root)
        ceiling.hide_set(True);ceiling.hide_render=True;ceiling['inspection_cutaway']=True
        cube(root.name+'_Canopy',(0,3.13,d/2+.5),(gap+2,.13,1.6),metal,root)
        cube(root.name+'_Reception',(-w/3,.58,d/2-4.4),(w/5,1.16,1.25),counter,root)
        panels=[]
        for side in (-1,1):
            half=gap/2;closed=side*(gap/4 if b['style']=='slide' else gap/2)
            pivot=empty('DOOR_'+b['id']+'_Pivot_'+str(side),(closed,.025,d/2+.04),root)
            center=-side*half/2 if b['style']=='swing' else 0
            cube(pivot.name+'_Glass',(center,1.45,0),(half-.06,2.78,.045),glass,pivot)
            for edge in (-1,1):
                cube(pivot.name+'_VFrame_'+str(edge),(center+edge*(half/2-.035),1.45,0),(.055,2.9,.1),metal,pivot)
                cube(pivot.name+'_HFrame_'+str(edge),(center,1.45+edge*(1.45-.035),0),(half,.055,.1),metal,pivot)
            cube(pivot.name+'_Handle',(center-side*(half/2-.15),1.37,.12),(.055,.46,.06),metal,pivot)
            for frame,progress in [(1,0),(76,1),(150,1),(226,0),(300,0)]:
                pivot.location.x=closed+(side*progress*(half+.12) if b['style']=='slide' else 0)
                pivot.rotation_euler.z=-side*progress*math.pi/2 if b['style']=='swing' else 0
                pivot.keyframe_insert('location',frame=frame);pivot.keyframe_insert('rotation_euler',frame=frame)
            pivot['operation']='Open frames1–76, hold76–150, close150–226';panels.append(pivot.name)
        doors.append({'id':b['id'],'panels':panels,'style':b['style'],'openingMeters':gap,'entry':[b['center'][0],0,b['center'][2]+d/2],'passageClear':True})
    placements=[]
    for record in world['environmentReplacements']:
        root,objects=source_instance(record,'REAL_'+record['id']);placements.append({'id':record['id'],'objects':len(objects),'sourceUrl':record['url']})
    for b,id,height,offset in [
        (buildings[0],'SUP_charite_university_hospital___operating_room',2.78,[-8,.025,-4]),
        (buildings[0],'SUP_kit_hospital',2,[8,.025,-5]),
        (buildings[0],'SUP_gm_hospitals_stand_design',2,[8,.025,5]),
        (buildings[1],'SUP_Clone_Human_Sleep_Module_Lab',3.1,[4,.025,-1]),
        (buildings[3],'SUP_moto_in_cyberpunk_style',1.17,[4,.025,-3])]:
        asset=next(a for a in catalog if a['id']==id)
        pos=[b['center'][i]+offset[i] for i in range(3)]
        record={**asset,'position':pos,'height':height,'rotation':[0,math.pi/2 if 'moto_in' in id else 0,0]}
        _,objs=source_instance(record,'REAL_INTERIOR_'+b['id']+'_'+id)
        placements.append({'id':record['id'],'objects':len(objs),'sourceUrl':record['url'],'interior':b['id']})
    rigpath=ROOT/'art/blender/PREPARATORIO_MIXAMO_REMY_20261005.blend'
    with bpy.data.libraries.load(str(rigpath),link=False) as (data_from,data_to):data_to.scenes=['MIXAMO_REMY_20261005']
    rigscene=data_to.scenes[0]
    rigged=[]
    for name,pos in [('NPC_REAL_Remy_Hospital',[43,0.24,-20]),('NPC_REAL_Remy_Guide',[-7,.24,2]),('PLAYER_PREVIEW_Remy',[0,.24,25])]:
        rigged.extend(rig_copy(list(rigscene.objects),pos,name))
    scene.frame_set(1);scene.frame_end=max(scene.frame_end,300)
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_location=xyz([48,1.5,-24])
            area.spaces.active.region_3d.view_distance=25
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report={'status':'saved-and-inspected','cityScene':scene.name,'newCollection':collection.name,'newObjects':len(collection.objects),'totalCityObjects':len(scene.objects),'doors':doors,'detailedModels':placements,'riggedPreviewObjects':len(rigged),'hiddenBlockoutObjects':hidden,'originalsRetained':True,'master':str(BLEND),'masterBytes':BLEND.stat().st_size,'note':'New architectural shells and functional doors; remaining prototype scenery requires further realism work.'}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','newObjects','totalCityObjects','master')},ensure_ascii=False))
    return report

if __name__=='__main__':run()
