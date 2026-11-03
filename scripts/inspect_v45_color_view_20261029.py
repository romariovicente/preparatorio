import bpy,json,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'reports/CHARACTER_THAI_REMAINING_REVIEW_V45_20261029.json').read_text())
body=bpy.data.objects[r['actor']];attrs=body.data.color_attributes
out={'activeColor':attrs.active_color.name,'activeColorIndex':attrs.active_color_index,'renderColorIndex':attrs.render_color_index,'attributes':[a.name for a in attrs],'viewports':[{'type':a.spaces.active.shading.type,'colorType':a.spaces.active.shading.color_type} for a in bpy.context.window.screen.areas if a.type=='VIEW_3D']}
with np.load(r['archive']) as z:
    ids=np.unique(z['actualTriangles'][z['actualFaceAnyMask']]);q=z['Idle_101_corrected_studyQ'][ids]
    out['markedVertexPoseBounds']=[[float(q[:,i].min()),float(q[:,i].max())] for i in range(3)]
print(json.dumps(out))
