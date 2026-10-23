"""Prepare surface-aware upper-body weights in an isolated staging asset.

No Blender/window or runtime changes. Bone landmarks remain staged guides until
their deformations are inspected. Geodesic paths follow the triangle surface,
with explicit topological separation of the raised hand and head above 1.34 m.
"""
import heapq,hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'reports/thai_upper_refit_20261023'
base=np.load(FOLDER/'baseline_mesh.npz');P=base['vertices'].astype(float);T=base['triangles'];old=base['weights'];names=base['group_names'].tolist()
info=json.loads((FOLDER/'baseline.json').read_text());bones=info['bones']
mask=np.load(FOLDER/'head_hand_graph_masks.npz')
assert str(mask['sourceSha256'])=='01f46cfeef24dc77705e63780f27e1b4583040efc53c433ccbe7f6c5e27d4b02'
head_ids=mask['head'];right_ids=mask['rightHand']
# Surface measurements and front/side review guide these points. This is NOT a
# claim that surface sections alone establish exact anatomical joint centres.
landmarks={'hips':(0,.28,.84),'spine':(0,.20,1.04),'chest':(0,.085,1.25),'neck':(.01,.01,1.43),'head':(.03,-.035,1.51),'crown':(.055,-.07,1.67),
 'L_shoulder':(.22,.13,1.32),'L_elbow':(.27,.32,1.10),'L_wrist':(.36,.32,.91),'L_tip':(.41,.31,.83),
 'R_shoulder':(-.17,-.075,1.34),'R_elbow':(-.25,-.30,1.33),'R_wrist':(-.17,-.40,1.55),'R_tip':(-.16,-.43,1.65)}
defs={n:{k:list(v) for k,v in row.items()} for n,row in bones.items()}
for n,end in [('hips','spine'),('spine','chest'),('chest','neck'),('neck','head'),('head','crown')]:defs[n]={'head':list(landmarks[n]),'tail':list(landmarks[end])}
defs['root']={'head':[0,0,0],'tail':[0,0,.12]}
for side,sign in [('L',1),('R',-1)]:
    defs[side+'_clavicle']={'head':list(landmarks['chest']),'tail':list(landmarks[side+'_shoulder'])}
    for n,a,b in [('upper_arm','shoulder','elbow'),('forearm','elbow','wrist'),('hand','wrist','tip')]:defs[side+'_'+n]={'head':list(landmarks[side+'_'+a]),'tail':list(landmarks[side+'_'+b])}
    # Existing knee/ankle/boot joints and V2 skin weights are retained. Move
    # only the proximal thigh anchor with the newly fitted pelvis.
    defs[side+'_thigh']['head']=[sign*.11,.28,.84]
assert set(defs)==set(bones)
deform=[n for n in names if n!='root'];assert len(deform)==19
distances=[]
for n in deform:
    a=np.array(defs[n]['head']);b=np.array(defs[n]['tail']);d=b-a
    t=np.clip(((P-a)@d)/(d@d),0,1);distances.append(np.linalg.norm(P-(a+t[:,None]*d),axis=1))
distances=np.stack(distances,axis=1)
allowed=np.ones_like(distances,dtype=bool)
arm_names=[n for n in deform if any(n.endswith('_'+p) for p in ['clavicle','upper_arm','forearm','hand'])]
for n in arm_names:allowed[head_ids,deform.index(n)]=False
for n in deform:
    if n not in ['R_upper_arm','R_forearm','R_hand']:allowed[right_ids,deform.index(n)]=False
central=(np.abs(P[:,0])<.10)&(P[:,2]>.76)&(P[:,2]<1.29)
for n in arm_names:allowed[central,deform.index(n)]=False
# Pin the actual upper head (including face/hair) as one rigid anatomical
# region; the lower neck keeps gradual weights and its original topology.
rigid_head=np.zeros(len(P),dtype=bool);rigid_head[head_ids]=P[head_ids,2]>1.48
for n in deform:
    if n!='head':allowed[rigid_head,deform.index(n)]=False
nearest=np.argmin(np.where(allowed,distances,np.inf),axis=1)
# Weld coincident UV-seam vertices only for the temporary graph. Exported mesh,
# vertex order, UVs and triangles are never welded or rewritten.
U,inverse=np.unique(np.round(P,6),axis=0,return_inverse=True)
ut=inverse[T];edge=np.concatenate([ut[:,[0,1]],ut[:,[1,2]],ut[:,[2,0]]]);edge.sort(axis=1);edge=np.unique(edge,axis=0)
edge=edge[edge[:,0]!=edge[:,1]];adj=[[] for _ in U]
for a,b in edge:
    w=float(np.linalg.norm(U[a]-U[b]));adj[int(a)].append((int(b),w));adj[int(b)].append((int(a),w))
def dijkstra(seeds):
    d=np.full(len(U),np.inf);queue=[]
    for i in seeds:d[int(i)]=0;heapq.heappush(queue,(0.,int(i)))
    while queue:
        cost,i=heapq.heappop(queue)
        if cost>d[i]+1e-12:continue
        for j,w in adj[i]:
            nc=cost+w
            if nc<d[j]:d[j]=nc;heapq.heappush(queue,(nc,j))
    return d[inverse]
geodesic=[];seed_counts={}
for j,n in enumerate(deform):
    pool=np.flatnonzero((nearest==j)&allowed[:,j])
    assert len(pool),f'No anatomical seed surface for {n}'
    limit=float(np.min(distances[pool,j])+.025)
    seeds=np.unique(inverse[pool[distances[pool,j]<=limit]])
    seed_counts[n]=len(seeds);geodesic.append(dijkstra(seeds))
G=np.stack(geodesic,axis=1)
# Tiny disconnected scan accessories use distance as a fallback. The fallback
# still honors the head/hand exclusions, and its extent is reported explicitly.
fallback=~np.isfinite(G)
G=np.where(fallback,distances+.15,G)
score=1/(G*G+.0025)**2
score[~allowed]=0
top=np.argsort(score,axis=1)[:,-4:];chosen=np.take_along_axis(score,top,axis=1);chosen/=chosen.sum(1)[:,None]
new=np.zeros_like(old)
for slot in range(4):
    cols=np.array([names.index(deform[int(j)]) for j in top[:,slot]]);new[np.arange(len(P)),cols]=chosen[:,slot]
# Preserve accepted lower weights exactly, with a short transition to the
# refitted pelvis. Retain at most four influences after the blend.
alpha=np.clip((P[:,2]-.66)/.10,0,1)
new=old*(1-alpha[:,None])+new*alpha[:,None]
top=np.argsort(new,axis=1)[:,-4:];limited=np.zeros_like(new)
for slot in range(4):limited[np.arange(len(P)),top[:,slot]]=new[np.arange(len(P)),top[:,slot]]
limited/=limited.sum(1)[:,None];limited[P[:,2]<=.66]=old[P[:,2]<=.66]
assert np.allclose(limited.sum(1),1,atol=2e-6)
assert np.max((limited>1e-8).sum(1))<=4
assert np.array_equal(limited[P[:,2]<=.66],old[P[:,2]<=.66])
np.savez_compressed(FOLDER/'prepared_weights.npz',weights=limited.astype(np.float32),group_names=np.array(names),vertices=P.astype(np.float32))
report={'status':'staged-guide-fit-and-surface-weights-awaiting-blender-review','landmarks':landmarks,'boneDefinitions':defs,
 'vertices':len(P),'graphVertices':len(U),'graphEdges':len(edge),'seedCounts':seed_counts,'fallbackBoneVertexPairs':int(fallback.sum()),
 'headGraphVertices':len(head_ids),'raisedArmGraphVertices':len(right_ids),'rigidUpperHeadVertices':int(rigid_head.sum()),
 'lowerWeightVerticesPreserved':int((P[:,2]<=.66).sum()),'changedWeightVertices':int(np.count_nonzero(np.max(np.abs(limited-old),axis=1)>1e-6)),
 'sourceGeometryPreserved':True,'nativeWalkValidated':False,'neutralPoseValidated':False,
 'limits':['Head/hand graph separation starts at Z>1.34m. Lower hair strands remain a later visual/weight review.','Hand has no individual finger bones.','Surface-derived landmarks require Blender deformation review before repose.']}
(FOLDER/'prepared_weights.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','graphVertices','graphEdges','rigidUpperHeadVertices','changedWeightVertices','lowerWeightVerticesPreserved','fallbackBoneVertexPairs']}))
