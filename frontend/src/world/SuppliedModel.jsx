import { useEffect, useMemo } from 'react';
import { useAnimations, useGLTF } from '@react-three/drei';
import {createCarryAnimations} from './carryAnimation.js';
import {createCharacterClone,findCharacterAction,startCharacterAction} from './characterModel.js';

export default function SuppliedModel({asset, height, playing=false,clip='Idle',holding=false}){
  const gltf=useGLTF(asset.url);
  const model=useMemo(()=>{
    return createCharacterClone(gltf.scene,height).group;
  },[gltf.scene,height]);
  const carry=useMemo(()=>createCarryAnimations(gltf.animations),[gltf.animations]);
  const {actions,mixer}=useAnimations(carry.clips,model);
  useEffect(()=>{
    const locomotion=clip?.toLowerCase().endsWith('walk')?'Walk':'Idle';
    const requested=holding&&carry.overlayName?carry.holdingNames[locomotion]??clip:clip;
    const action=findCharacterAction(actions,playing?requested:'Idle');
    startCharacterAction(action,mixer,playing);
    return ()=>action?.stop();
  },[actions,mixer,playing,clip,holding,carry]);
  useEffect(()=>{
    const overlay=carry.overlayName&&actions[carry.overlayName];
    if(!overlay)return;
    if(holding&&playing){
      overlay.reset().setEffectiveWeight(1).play();
      // Three.js AnimationAction is an imperative mixer object, independent of
      // React render data. Holding the sampled arm pose leaves leg timing intact.
      /* eslint-disable react-hooks/immutability -- This effect samples mutable Three.js AnimationAction state. */
      overlay.time=carry.overlayTime;
      overlay.paused=true;
      /* eslint-enable react-hooks/immutability */
    }else overlay.stop();
    return()=>overlay.stop();
  },[actions,holding,playing,carry]);
  return <primitive object={model} dispose={null}/>;
}
