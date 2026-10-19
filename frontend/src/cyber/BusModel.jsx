import {useMemo} from 'react';
import {useFrame} from '@react-three/fiber';
import {useGLTF} from '@react-three/drei';
import {animateBusRig,createBusRig,interactiveBusUrl} from './busArticulation.js';
import {sampleLiveBus} from './busInteraction.js';

export default function BusModel({asset,simulation,id}){
  const {scene}=useGLTF(interactiveBusUrl(asset));
  const rig=useMemo(()=>createBusRig(scene,asset.height),[scene,asset.height]);
  useFrame((_,delta)=>animateBusRig(rig,sampleLiveBus(simulation.current,id),delta));
  return <primitive object={rig.outer} dispose={null}/>;
}
