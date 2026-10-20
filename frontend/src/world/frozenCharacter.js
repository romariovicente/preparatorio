import {AnimationMixer,Box3,Vector3} from 'three';
import {createCharacterClone,isCharacterHelper} from './characterModel.js';

// Apply one reviewed sample on a private skeleton copy, then normalize that
// pose. Never run a legacy FK cycle or change loader-cache bones/materials.
export function createFrozenCharacterClone(source,height=1.7,animations=[],standingPose=null){
  const prepared=createCharacterClone(source,0);
  if(standingPose?.clip){
    const clip=animations.find(clip=>clip.name===standingPose.clip);
    if(!clip)throw new Error('A pose revisada não existe no modelo.');
    const mixer=new AnimationMixer(prepared.group),action=mixer.clipAction(clip).play();
    action.time=Math.min(clip.duration,Math.max(0,standingPose.time??0));action.paused=true;mixer.update(0);
    // Bone transforms remain at this sample; no mixer updates follow it.
    prepared.poseMixer=mixer;
  }
  prepared.group.updateMatrixWorld(true);
  const bounds=new Box3();
  prepared.group.traverse(object=>{
    if(object.isSkinnedMesh){object.skeleton.update();object.computeBoundingBox();object.computeBoundingSphere();}
    if(object.isMesh&&!isCharacterHelper(object))bounds.expandByObject(object,true);
  });
  const size=bounds.getSize(new Vector3()),center=bounds.getCenter(new Vector3());
  if(height>0&&!bounds.isEmpty()&&Number.isFinite(size.y)&&size.y>.001){
    prepared.offset.position.set(-center.x,-bounds.min.y,-center.z);
    prepared.group.scale.setScalar(height/size.y);
  }
  prepared.group.userData.actor=true;prepared.group.updateMatrixWorld(true);
  prepared.authoredBounds=bounds;
  return prepared;
}
