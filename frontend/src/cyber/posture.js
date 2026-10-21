import {Quaternion,Vector3} from 'three';
const up=new Vector3(0,1,0);
function straighten(bone,tip,maxAngle,strength){
  if(!bone||!tip||!bone.parent)return;
  const from=bone.getWorldPosition(new Vector3()),to=tip.getWorldPosition(new Vector3()).sub(from).normalize();
  const angle=to.angleTo(up);
  if(angle<.002||angle>Math.PI/3)return;
  const delta=new Quaternion().setFromUnitVectors(to,up);
  delta.slerp(new Quaternion(),1-Math.min(1,maxAngle/angle)*strength);
  const parent=bone.parent.getWorldQuaternion(new Quaternion());
  const local=parent.clone().invert().multiply(delta).multiply(parent);
  bone.quaternion.premultiply(local);bone.updateWorldMatrix(false,true);
}
export function createUprightPosture(group){
  const named={};group.traverse(o=>{if(o.isBone){const key=o.name.replace(/^mixamorig\d*[:_]?/i,'');named[key]=o;named[key.toLowerCase()]=o;}});
  return clip=>{
    if(clip!=='Idle'&&clip!=='Walk')return;
    group.updateMatrixWorld(true);
    straighten(named.Spine1??named.Spine??named.spine1??named.spine,named.Neck??named.neck,8*Math.PI/180,clip==='Idle'?.8:.35);
    straighten(named.Neck??named.neck,named.Head??named.head,5*Math.PI/180,clip==='Idle'?.7:.25);
  };
}
