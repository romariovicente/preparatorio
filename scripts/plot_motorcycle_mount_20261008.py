"""CPU geometry review. First run inspect_motorcycle_mount_20261008.mjs --vertices.

The optional large intermediate vertex JSON is disposable after this PNG is made.
"""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'reports/motorcycle_mount_vertices_20261008.json').read_text())
points=data['points']
image=Image.new('RGB',(1700,1150),'#fafafa');draw=ImageDraw.Draw(image)
colors={'1001':'#647c91','1002':'#9c608e','1003':'#22a493','1004':'#3c434a'}
scale=550
def side(p):return (int(800+p[2]*scale),int(870-p[1]*scale))
def top(p):return (int(800+p[2]*scale),int(1020+p[0]*scale))
for y in [0,.2,.4,.6,.8,1,1.2,1.4]:
    a,b=side([0,y,-1.3]),side([0,y,1.3]);draw.line([a,b],fill='#dddddd');draw.text((a[0]-30,a[1]-8),f'{y:.1f}',fill='#222222')
for z in [-1.2,-1,-.8,-.6,-.4,-.2,0,.2,.4,.6,.8,1,1.2]:
    a,b=side([0,0,z]),side([0,1.4,z]);draw.line([a,b],fill='#dddddd');draw.text((a[0]-12,a[1]+6),f'{z:.1f}',fill='#222222')
for row in points:
    p=row['point'];color=colors[row['material']]
    draw.point(side(p),fill=color)
draw.text((20,20),'Normalized Kawasaki side view: rear -Z (left), front +Z (right), Y up',fill='#222222')
for i,(key,color) in enumerate(colors.items()):
    draw.rectangle((20+i*220,45,40+i*220,65),fill=color);draw.text((48+i*220,47),f'Material {key}',fill='#222222')
image.save(ROOT/'reports/motorcycle_mount_geometry_side_20261008.png')
for material in colors:
    rows=[r['point'] for r in points if r['material']==material and abs(r['point'][0])<.16]
    print(material)
    for z in [-.8,-.7,-.6,-.5,-.4,-.3,-.2,-.1,0,.1,.2,.3,.4,.5,.6,.7]:
        band=[p for p in rows if z-.025<p[2]<z+.025]
        if band:
            highest=max(band,key=lambda p:p[1]);print(round(z,2),[round(v,4) for v in highest])
