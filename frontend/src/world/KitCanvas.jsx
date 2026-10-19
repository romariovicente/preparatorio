import {assetUrl} from '../config/deploymentConfig.js';
import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { Bounds, OrbitControls, useGLTF } from '@react-three/drei';
function Kit() {
  const {scene}=useGLTF(assetUrl('/assets/models/PREP_Modular_City_Kit_01.glb'));
  return <primitive object={scene}/>;
}
export default function KitCanvas(){return <Canvas camera={{position:[75,55,85],fov:45}} dpr={[1,1.5]}>
  <color attach="background" args={['#183340']}/><ambientLight intensity={2}/><directionalLight position={[40,80,60]} intensity={3}/>
  <Suspense fallback={null}><Bounds fit clip observe margin={1.25}><Kit/></Bounds></Suspense><OrbitControls makeDefault/>
</Canvas>;}
