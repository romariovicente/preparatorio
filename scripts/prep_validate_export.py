"""Export 32 individual GLBs and the catalog; reimport catalog and compare evaluated geometry."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from prep_export_glb import export_assets

scene=bpy.data.scenes['PREP_CITY']; bpy.context.window.scene=scene
assets=sorted([o for o in scene.objects if o.get('prep_asset')],key=lambda o:o.name)
out=ROOT/'frontend/public/assets/models'
exports=[]
for obj in assets:
    exports.append(export_assets([obj],out/(obj.name+'.glb'),center_single=True))
exports.append(export_assets(assets,out/'PREP_Modular_City_Kit_01.glb'))
(ROOT/'reports/exports.json').write_text(json.dumps(exports,indent=2),encoding='utf-8')

def bounds(obj):
    dg=bpy.context.evaluated_depsgraph_get(); ev=obj.evaluated_get(dg)
    points=[ev.matrix_world@Vector(v) for v in ev.bound_box]
    return [min(p[k] for p in points) for k in range(3)]+[max(p[k] for p in points) for k in range(3)]

expected={o.name:{'bounds':bounds(o),'pivot':list(o.location),'materials':sorted(set(p.material_index for p in o.data.polygons))} for o in assets}
validation=bpy.data.scenes.new('PREP_GLB_VALIDATION'); bpy.context.window.scene=validation
validation.unit_settings.system='METRIC'; validation.unit_settings.scale_length=1
bpy.ops.import_scene.gltf(filepath=str(out/'PREP_Modular_City_Kit_01.glb'))
imported=[o for o in validation.objects if o.type=='MESH']
assert len(imported)==32,(len(imported),'unexpected mesh count')
checks=[]
for obj in imported:
    name=obj.get('prep_asset_name'); assert name in expected,name
    exp=expected[name]; delta=max(abs(a-b) for a,b in zip(bounds(obj),exp['bounds']))
    pivot_delta=max(abs(a-b) for a,b in zip(obj.location,exp['pivot']))
    assert delta<0.001,(name,delta)
    assert pivot_delta<0.001,(name,pivot_delta)
    assert obj.data.uv_layers and all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    checks.append({'name':name,'bounds_error_m':delta,'pivot_error_m':pivot_delta,'materials':len(obj.data.materials),'uv':True,'vertices':len(obj.data.vertices)})
bpy.context.window.scene=scene
for o in bpy.context.selected_objects: o.select_set(False)
for o in assets: o.select_set(True)
bpy.context.view_layer.objects.active=assets[0]
report={'blender':bpy.app.version_string,'catalog_meshes_reimported':len(imported),'checks':checks,'files':[{'name':Path(e['path']).name,'bytes':Path(e['path']).stat().st_size,'sha256':hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()} for e in exports]}
(ROOT/'reports/glb_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/blender/PREPARATORIO_CITY_KIT_01.blend'))
print(json.dumps({'exports':len(exports),'reimported':len(imported),'max_bounds_error_m':max(c['bounds_error_m'] for c in checks)}))
