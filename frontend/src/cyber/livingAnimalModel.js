import {AnimationMixer,Box3,Group,Vector3} from 'three';

const empty=new Vector3();
export function visibleAnimalBounds(scene){
  scene.updateMatrixWorld(true);
  scene.traverse(o=>{if(o.isSkinnedMesh){o.skeleton.update();o.computeBoundingBox();}});
  const box=new Box3();
  scene.traverse(o=>{if(o.isMesh&&o.visible&&!/^Icosphere(?:\.\d+)?$/.test(o.name))box.expandByObject(o,true);});
  return box;
}

// This runtime owns a privately fetched GLB. Uniform wrappers preserve source
// skins, inverse binds and clips; only horizontal root drift is compensated.
export function createLivingAnimal(gltf,habitat){
  const placement=new Group(),scale=new Group(),origin=new Group(),motion=new Group();
  placement.name=`RESIDENT_${habitat.id}`;placement.userData.actor=true;
  placement.add(scale);scale.add(origin);origin.add(motion);motion.add(gltf.scene);
  gltf.scene.traverse(o=>{
    if(/^Icosphere(?:\.\d+)?$/.test(o.name))o.visible=false;
    if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}
    if(o.isSkinnedMesh)o.frustumCulled=false;
  });
  const clip=gltf.animations.find(candidate=>candidate.name===habitat.clip);
  if(!clip)throw new Error(`Animação original ausente: ${habitat.assetId}/${habitat.clip}`);
  const mixer=new AnimationMixer(gltf.scene);mixer.clipAction(clip).play();mixer.setTime(0);
  const box=visibleAnimalBounds(placement),size=box.getSize(new Vector3()),center=box.getCenter(new Vector3());
  if(box.isEmpty()||![size.x,size.y,size.z].every(Number.isFinite)||size.y<=0)throw new Error(`Modelo animal inválido: ${habitat.assetId}`);
  const factor=habitat.targetLengthMeters?habitat.targetLengthMeters/Math.max(size.x,size.z):habitat.height/size.y;
  scale.scale.setScalar(factor);origin.position.set(-center.x,-box.min.y,-center.z);
  placement.updateMatrixWorld(true);
  const anchor=habitat.anchorBone?gltf.scene.getObjectByName(habitat.anchorBone):null;
  const reference=anchor?origin.worldToLocal(anchor.getWorldPosition(new Vector3())).clone():null;
  let head=null;gltf.scene.traverse(o=>{if(!head&&o.isBone&&/^head(?:[_\d]|$)/i.test(o.name))head=o;});
  const forward=head&&anchor?head.getWorldPosition(new Vector3()).sub(anchor.getWorldPosition(new Vector3())):new Vector3(0,0,1);
  // World axes are currently unrotated. Forward adjustment is around Y only.
  const forwardYaw=forward.x*forward.x+forward.z*forward.z>1e-8?Math.atan2(forward.x,forward.z):0;
  const sample=new Vector3();
  function update(delta,path){
    mixer.update(Math.max(0,Math.min(.1,delta)));
    motion.position.copy(empty);placement.updateMatrixWorld(true);
    if(anchor){origin.worldToLocal(anchor.getWorldPosition(sample));motion.position.set(reference.x-sample.x,0,reference.z-sample.z);}
    placement.position.set(path.x,path.y,path.z);placement.rotation.y=path.heading-forwardYaw;
    placement.updateMatrixWorld(true);
    gltf.scene.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.update();});
  }
  return {object:placement,mixer,scaleFactor:factor,clipName:clip.name,forwardYaw,update,
    stop(){mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);}};
}
