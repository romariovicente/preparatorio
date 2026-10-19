import {useMemo} from 'react';
import {useFrame} from '@react-three/fiber';
import {useGLTF} from '@react-three/drei';
import {animateMotorcycleRig,createMotorcycleRig,interactiveMotorcycleUrl} from './motorcycleArticulation.js';

export default function MotorcycleModel({asset,simulation,personal=false}) {
  const {scene}=useGLTF(interactiveMotorcycleUrl(asset));
  const rig=useMemo(()=>createMotorcycleRig(scene,asset.height??1.3),[scene,asset.height]);
  useFrame(()=>{
    const bike=personal?simulation?.current?.personalVehicles?.mototaxi:null;
    animateMotorcycleRig(rig,{wheelAngle:bike?.wheelAngle??0,steeringAngle:bike?.steeringAngle??0});
  });
  return <primitive object={rig.outer} dispose={null}/>;
}
