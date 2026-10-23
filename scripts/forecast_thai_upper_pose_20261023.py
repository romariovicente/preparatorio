"""CPU forecast of the prepared binding; no GLB/Blender/runtime writes.

This does not substitute for the independent exported/reimported Blender test.
It makes large-arm movements reviewable while the RNA operation is running.
"""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'reports/thai_upper_refit_20261023'
base=np.load(F/'baseline_mesh.npz');prepared=np.load(F/'prepared_weights.npz');masks=np.load(F/'head_hand_graph_masks.npz')
P=base['vertices'].astype(float);W=prepared['weights'].astype(float);names=prepared['group_names'].tolist();defs=json.loads((F/'prepared_weights.json').read_text())['boneDefinitions']
def swing(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);c=float(a@b);s=float(np.linalg.norm(v))
    if s<1e-10:return np.eye(3)
    K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+K+K@K*((1-c)/(s*s))
def sample(label):
    rotations={n:np.eye(3) for n in names};offset={n:np.zeros(3) for n in names}
    if label=='head_turn_15':
        a=math.radians(15);R=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
        anchor=np.array(defs['head']['head']);rotations['head']=R;offset['head']=anchor-R@anchor
    elif label in ['right_arm_lowered','both_arms_lowered']:
        for side in (['R'] if label=='right_arm_lowered' else ['R','L']):
            sign=1 if side=='L' else -1;pos=np.array(defs[side+'_upper_arm']['head'])
            for part,target in [('upper_arm',(sign*.10,0,-1)),('forearm',(sign*.03,-.08,-1)),('hand',(0,-.12,-1))]:
                n=side+'_'+part;a=np.array(defs[n]['head']);d=np.array(defs[n]['tail'])-a;target=np.array(target,dtype=float);target/=np.linalg.norm(target)
                R=swing(d,target);rotations[n]=R;offset[n]=pos-R@a;pos+=target*np.linalg.norm(d)
    posed=np.zeros_like(P)
    for j,n in enumerate(names):posed+=(P@rotations[n].T+offset[n])*W[:,j,None]
    return posed
labels=['rest','head_turn_15','right_arm_lowered','both_arms_lowered'];poses={s:sample(s) for s in labels};records=[]
for label,posed in poses.items():
    delta=np.linalg.norm(posed-P,axis=1)
    protected={k:float(delta[masks[k]].max()) for k in ['faceFrontCandidate','hairRearCandidate','rightHand153']}
    if 'arm_lowered' in label or label=='both_arms_lowered':assert protected['faceFrontCandidate']<1e-5 and protected['hairRearCandidate']<1e-5
    if label=='head_turn_15':assert protected['rightHand153']<1e-5
    records.append({'sample':label,'protectedRegionMaxDisplacements':protected,'acceptedAsBlenderOrRuntimeValidation':False})
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
im=Image.new('RGB',(2400,1800),'#f4f7fb');draw=ImageDraw.Draw(im)
draw.text((25,18),'PREVISÃO CPU — binding preparado; NÃO é aprovação do Blender ou de caminhada',font=font,fill='#192c3e')
for col,label in enumerate(labels):
    draw.text((col*600+20,65),label,font=font,fill='#192c3e')
    for row,mode in enumerate(['front','side']):
        ox=col*600+300;oy=row*800+870;scale=420
        draw.text((col*600+20,row*800+110),mode,font=small,fill='#536478')
        for zz in np.arange(0,1.81,.2):
            yy=oy-zz*scale;draw.line((col*600+10,yy,col*600+590,yy),fill='#dbe3ed')
        for i,p in enumerate(poses[label]):
            h=p[0] if mode=='front' else p[1];x=int(ox+h*scale);y=int(oy-p[2]*scale)
            color='#536478'
            draw.point((x,y),fill=color)
dest=F/'prepared_pose_forecast.png';im.save(dest)
report={'status':'cpu-forecast-only-blender-operation-still-required','samples':records,'image':str(dest),'runtimeChanged':False,'nativeWalkValidated':False}
(F/'prepared_pose_forecast.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'samples':records}))
