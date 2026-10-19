"""Resume only verification/render after an interrupted motorcycle save.

Reads the saved revision and preserves the derivative GLB and .blend bytes.
"""
from pathlib import Path
import bpy,json,math,hashlib,struct
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1]
SOURCE_ID='SUP_cyberpunk_kawasaki_ninja';ASSET='VEH_Kawasaki_Interactive_20261007'
SOURCE=ROOT/'frontend/public/assets/supplied'/(SOURCE_ID+'.glb')
GLB=ROOT/'frontend/public/assets/vehicles'/(ASSET+'.glb')
BLEND=ROOT/'art/blender/PREPARATORIO_MOTORCYCLE_INTERACTIVE_20261007.blend'
REPORT=ROOT/'reports/motorcycle_interactive_validation_20261007.json'
CATALOG=json.loads((ROOT/'frontend/src/config/suppliedAssets.json').read_text(encoding='utf-8'))
record=next(a for a in CATALOG if a['id']==SOURCE_ID)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if REPORT.exists():raise FileExistsError('Preserve completed motorcycle report')
if sha(SOURCE)!=record['sha256']:raise RuntimeError('Source changed')
bpy.ops.wm.open_mainfile(filepath=str(BLEND));scene=bpy.context.scene
bpy.context.view_layer.update()
groups={o.get('asset_node_name',o.name):o for o in scene.objects if o.type=='EMPTY'}
root=groups[ASSET];steering=groups['Steering_F'];wheel_groups={side:groups['Wheel_'+side] for side in ('F','R')}
head=steering.matrix_world.translation.copy();steering_axis=steering.matrix_world.to_quaternion()@Vector((0,0,1))
stats={}
for name in ('Motorcycle_Body','Steering_F','Wheel_F','Wheel_R'):
    meshes=[o for o in groups[name].children if o.type=='MESH']
    stats[name]={'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'vertices':sum(len(o.data.vertices) for o in meshes)}
total=sum(row['triangles'] for row in stats.values())
if total!=record['triangles']:raise RuntimeError('Saved derivative lost source faces')
fork_components=[None]*4;steering_components=[None]*38
# The reusable verification tail checks actual reimported vertices and local
# quaternion rotation, then saves the report before short visual proof renders.
text=(ROOT/'scripts/prep_articulate_motorcycle_20261007.py').read_text(encoding='utf-8')
marker="validation=bpy.data.scenes.new('VERIFY_REAL_MOTORCYCLE');bpy.context.window.scene=validation"
exec(marker+text.split(marker,1)[1],globals())
