import {useMemo} from 'react';
import {useFrame} from '@react-three/fiber';
import {useGLTF} from '@react-three/drei';
import {animateCarRig,createCarRig,interactiveCarUrl} from './carArticulation.js';

export default function CarModel({asset,simulation,personal=false,open}) {
  const {scene}=useGLTF(interactiveCarUrl(asset));
  const sourceId=asset.sourceId??asset.id;
  const prepared=useMemo(()=>createCarRig(scene,asset.height,{sourceId}),[scene,asset.height,sourceId]);
  useFrame((_,delta)=>{
    const state=simulation?.current;
    const car=personal?state?.personalVehicles?.car:null;
    animateCarRig(prepared,{
      doorOpen:personal?Boolean(state?.carControls?.doorOpen??open):Boolean(open),
      windowsOpen:personal&&Boolean(state?.carControls?.windowsOpen),
      steeringAngle:car?.steeringAngle??0,
      wheelAngle:car?.wheelAngle??0,
    },delta);
  });
  return <primitive object={prepared.outer} dispose={null}/>;
}
