import {setWorldShadows} from './modelLighting.js';
import {assetUrl} from '../config/deploymentConfig.js';

export const hospitalChairAssetUrl=plan=>assetUrl(plan.asset);

export const hospitalOriginalChairRootNames=Object.freeze([
  ...[0,1].flatMap(row=>[0,1,2,3,4].map(column=>`HSP15_CHAIR_${row}_${column}`)),
  ...['01','02','03','04'].map(room=>`HSP15_CHAIR_ROOM_${room}`),
]);

function setHospitalChairRootVisibility(scene,visible,names){
  const allowed=new Set(hospitalOriginalChairRootNames);
  const selected=new Set(names.filter(name=>allowed.has(name))),hidden=[];
  scene.traverse(object=>{
    const name=[object.userData?.name,object.userData?.asset_node_name,object.name].find(name=>selected.has(name));
    if(name){
      object.visible=visible;
      hidden.push(name);
    }
  });
  return hidden;
}

export function hideHospitalChairRoots(scene,names=hospitalOriginalChairRootNames){
  return setHospitalChairRootVisibility(scene,false,names);
}

export function restoreHospitalChairRoots(scene,names=hospitalOriginalChairRootNames){
  return setHospitalChairRootVisibility(scene,true,names);
}

export function createHospitalChairClone(source){
  // Chair instances own transforms and visibility; GPU resources remain shared
  // with the loader cache and are never disposed by an individual instance.
  return setWorldShadows(source.clone(true));
}
