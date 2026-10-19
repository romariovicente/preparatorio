"""Create 32 editable urban modules. Existing scenes and assets are preserved."""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prep_materials import create_materials
from prep_prepare_asset import prepare

def build():
    if bpy.data.scenes.get('PREP_CITY'): raise RuntimeError('PREP_CITY exists; inspect before rebuilding')
    scene=bpy.data.scenes.new('PREP_CITY'); bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1; scene.unit_settings.length_unit='METERS'
    scene.tool_settings.use_snap=True; scene.tool_settings.snap_elements={'INCREMENT'}; scene.tool_settings.use_snap_grid_absolute=True
    scene['prep_grid_primary_m']=0.5; scene['prep_grid_secondary_m']=0.25
    scene['prep_grid_note']='Viewport grid is zoom-dependent; module dimensions and origins use 0.25/0.5 m increments.'
    main=bpy.data.collections.new('PREP_CITY'); scene.collection.children.link(main)
    cats={}
    for name in ['Facades','Structure','Details','Streets','Presentation']:
        col=bpy.data.collections.new('PREP_'+name); main.children.link(col); cats[name]=col
    mats=create_materials(); assets=[]
    def module(name,cat,parts,custom=None):
        verts=[]; faces=[]; mi=[]; keys=list(mats)
        for x,y,z,w,d,h,mat in parts:
            n=len(verts)
            verts.extend([(x+dx*w/2,y+dy*d/2,z+dz*h) for dx,dy,dz in [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]])
            faces.extend([tuple(n+i for i in f) for f in [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]])
            mi.extend([keys.index(mat)]*6)
        if custom:
            v,f,mat=custom; n=len(verts); verts.extend(v); faces.extend([tuple(n+i for i in face) for face in f]); mi.extend([keys.index(mat)]*len(f))
        mesh=bpy.data.meshes.new('MESH_'+name[4:]); mesh.from_pydata(verts,[],faces); mesh.update()
        obj=bpy.data.objects.new(name,mesh); cats[cat].objects.link(obj)
        for mat in mats.values(): mesh.materials.append(mat)
        uv=mesh.uv_layers.new(name='UVMap')
        for poly,index in zip(mesh.polygons,mi):
            poly.material_index=index
            axis=max(range(3),key=lambda k:abs(poly.normal[k])); axes=[k for k in range(3) if k!=axis]
            for loop in poly.loop_indices:
                co=mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv=(co[axes[0]],co[axes[1]])
        i=len(assets); obj.location=((i%8)*10,(i//8)*12,0)
        obj['prep_asset']=True; obj['prep_asset_name']=name; obj['prep_pivot']='bottom center; Blender Z up, front -Y'
        obj['prep_grid_m']=0.25; obj['prep_category']=cat
        assets.append(obj); return obj
    def box(w,d,h,mat='Concrete',x=0,y=0,z=0): return (x,y,z,w,d,h,mat)
    def frame(w=4,h=3):
        return [box(.125,.25,h,'Metal',x=-w/2+.0625),box(.125,.25,h,'Metal',x=w/2-.0625),box(w-.25,.25,.125,'Metal',z=h-.125),box(w-.25,.25,.125,'Metal'),box(.0625,.25,h-.25,'Metal',z=.125)]
    module('MOD_Facade_Glass_A','Facades',frame()+[box(3.75,.06,2.75,'Glass',z=.125)])
    module('MOD_Facade_Concrete_A','Facades',[box(4,.25,.75),box(4,.25,.5,z=2.5),box(.5,.25,1.75,x=-1.75,z=.75),box(.5,.25,1.75,x=1.75,z=.75),box(3,.06,1.75,'Glass',z=.75),box(.075,.3,1.75,'Metal',z=.75)])
    module('MOD_Wall_Solid_01','Facades',[box(4,.25,3,'Plaster')])
    module('MOD_Wall_Half_01','Facades',[box(2,.25,3,'Plaster')])
    module('MOD_Wall_Window_01','Facades',[box(4,.25,1),box(4,.25,.5,z=2.5),box(1,.25,1.5,x=-1.5,z=1),box(1,.25,1.5,x=1.5,z=1)])
    module('MOD_Window_01','Facades',frame(2,1.5)+[box(1.75,.06,1.25,'Glass',z=.125)])
    module('MOD_Door_01','Facades',[box(.125,.25,2.25,'Metal',x=-.6875),box(.125,.25,2.25,'Metal',x=.6875),box(1.25,.25,.125,'Metal',z=2.125),box(1.25,.08,2.125,'Glass'),box(.04,.06,.4,'Metal',x=.45,y=-.07,z=.8)])
    module('MOD_Storefront_01','Facades',frame(4,3)+[box(3.75,.06,2.75,'Glass',z=.125),box(4,.4,.5,'Accent',z=2.5),box(.1,.25,2.4,'Metal',x=.7)])
    module('MOD_Corner_Outer_01','Structure',[box(2,.25,3,x=.875),box(.25,1.75,3,y=.875)])
    module('MOD_Corner_Inner_01','Structure',[box(2,.25,3,x=-.875),box(.25,1.75,3,y=.875)])
    module('MOD_Pillar_01','Structure',[box(.5,.5,3)])
    module('MOD_Beam_01','Structure',[box(4,.5,.5)])
    module('MOD_Slab_01','Structure',[box(4,4,.25)])
    module('MOD_Roof_01','Structure',[box(4,4,.25,'Metal'),box(4,.125,.125,'Accent',y=-1.9375,z=.25)])
    module('MOD_Parapet_01','Structure',[box(4,.25,1),box(4,.35,.1,'Metal',z=1)])
    module('MOD_Panel_Glass_01','Details',[box(2,.125,3,'Glass')])
    module('MOD_Panel_Metal_01','Details',[box(2,.125,3,'Metal')]+[box(.05,.05,3,'Accent',x=x,y=-.0875) for x in [-.75,-.25,.25,.75]])
    module('MOD_Brise_Horizontal_01','Details',[box(.125,.25,3,'Metal',x=-1.9375),box(.125,.25,3,'Metal',x=1.9375)]+[box(4,.5,.1,'White',z=z) for z in [.25,.75,1.25,1.75,2.25,2.75]])
    module('MOD_Brise_Vertical_01','Details',[box(4,.25,.125,'Metal'),box(4,.25,.125,'Metal',z=2.875)]+[box(.1,.5,3,'White',x=x) for x in [-1.75,-1.25,-.75,-.25,.25,.75,1.25,1.75]])
    module('MOD_Balcony_01','Details',[box(4,1.5,.25),box(4,.075,1,'Glass',y=-.7125,z=.25),box(.075,1.5,1,'Glass',x=-1.9625,z=.25),box(.075,1.5,1,'Glass',x=1.9625,z=.25),box(4,.1,.075,'Metal',y=-.7,z=1.25)])
    module('MOD_Railing_01','Details',[box(4,.1,.075,'Metal',z=1.05)]+[box(.075,.1,1.05,'Metal',x=x) for x in [-1.95,-1,0,1,1.95]])
    module('MOD_Canopy_01','Details',[box(4,2,.25,'Accent'),box(.125,1.75,.25,'Metal',x=-1.75,z=.25),box(.125,1.75,.25,'Metal',x=1.75,z=.25)])
    module('MOD_Sidewalk_01','Streets',[box(4,2,.25,'Concrete')])
    module('MOD_Sidewalk_Corner_01','Streets',[box(4,4,.25,'Concrete')])
    module('MOD_Curb_01','Streets',[box(4,.25,.25,'White')])
    module('MOD_Road_01','Streets',[box(4,8,.125,'Asphalt')]+[box(.9,.1,.006,'Yellow',x=x,z=.125) for x in [-1.25,1.25]])
    module('MOD_Road_Intersection_01','Streets',[box(8,8,.125,'Asphalt')])
    module('MOD_Crosswalk_01','Streets',[box(4,8,.125,'Asphalt')]+[box(2.5,.5,.006,'White',y=y,z=.125) for y in [-3.25,-2.25,-1.25,-.25,.75,1.75,2.75]])
    module('MOD_Planter_01','Streets',[box(4,.25,.5,y=-.875),box(4,.25,.5,y=.875),box(.25,1.5,.5,x=-1.875),box(.25,1.5,.5,x=1.875),box(3.5,1.5,.35,'Earth'),box(3.4,1.4,.08,'Grass',z=.35)])
    rampv=[(-1,-1.5,0),(1,-1.5,0),(1,1.5,0),(-1,1.5,0),(-1,-1.5,.01),(1,-1.5,.01),(1,1.5,.25),(-1,1.5,.25)]
    rampf=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    module('MOD_Ramp_PCD_01','Streets',[],(rampv,rampf,'Concrete'))
    module('MOD_Tactile_Paving_01','Streets',[box(2,.5,.05,'Yellow')]+[box(.05,.375,.018,'Yellow',x=x,z=.05) for x in [-.875,-.625,-.375,-.125,.125,.375,.625,.875]])
    module('MOD_Grass_Infill_01','Streets',[box(4,2,.2,'Earth'),box(4,2,.05,'Grass',z=.2)])
    prepare(assets)
    # Presentation objects are excluded from all asset exports.
    def text_obj(body,loc,size,name):
        curve=bpy.data.curves.new(name,'FONT'); curve.body=body; curve.size=size; curve.extrude=0
        ob=bpy.data.objects.new(name,curve); cats['Presentation'].objects.link(ob); ob.location=loc
        curve.materials.append(mats['Metal']); return ob
    for i,ob in enumerate(assets):
        text_obj(f'{i+1:02d} / '+ob.name[4:].replace('_',' '),(ob.location.x-4,ob.location.y-4.7,.01),.31,'LABEL_'+ob.name)
    text_obj('PREPARATORIO / CITY KIT 01',(-4,46,0),1.5,'PREP_Title')
    text_obj('32 MODULES     /     METRIC 1:1     /     PHASE 01',(-4,43.8,0),.7,'PREP_Subtitle')
    camdata=bpy.data.cameras.new('PREP_Camera'); cam=bpy.data.objects.new('PREP_Camera',camdata); cats['Presentation'].objects.link(cam)
    cam.location=(81,-78,107); target=Vector((34,20,0)); cam.rotation_euler=(target- cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO'; camdata.ortho_scale=99; scene.camera=cam
    ld=bpy.data.lights.new('PREP_Sun','SUN'); lo=bpy.data.objects.new('PREP_Sun',ld); cats['Presentation'].objects.link(lo)
    lo.rotation_euler=(.45,-.5,-.5); ld.energy=3; ld.angle=.35
    world=bpy.data.worlds.new('PREP_World'); world.use_nodes=True
    bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs[0].default_value=(.64,.72,.8,1); bg.inputs[1].default_value=.5; scene.world=world
    scene.render.engine='CYCLES'; scene.cycles.samples=16
    scene.render.resolution_x=1800; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.overlay.grid_scale=.5; area.spaces.active.overlay.grid_subdivisions=2
                area.spaces.active.region_3d.view_distance=90; area.spaces.active.region_3d.view_location=target
    bpy.context.view_layer.update()
    manifest={'blender':bpy.app.version_string,'modules':[{'name':o.name,'category':o['prep_category'],'dimensions_m':list(o.dimensions),'location_m':list(o.location),'vertices':len(o.data.vertices),'polygons':len(o.data.polygons)} for o in assets], 'materials':[m.name for m in mats.values()],'collections':[main.name]+[c.name for c in cats.values()]}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/kit_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    path=ROOT/'art/blender/PREPARATORIO_CITY_KIT_01.blend'
    if path.exists(): raise FileExistsError(path)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print(json.dumps({'file':str(path),'modules':len(assets),'materials':len(mats),'collections':manifest['collections']}))

if __name__=='__main__': build()
