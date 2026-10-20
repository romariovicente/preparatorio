import {useEffect,useMemo,useState} from 'react';
import {Html,useGLTF} from '@react-three/drei';
import {warpEnginePlan as engine} from './warpEngineWorld.js';
import CityAssetBoundary from './CityAssetBoundary.js';
import {setWorldShadows} from './modelLighting.js';

function EngineModel(){
  const {scene}=useGLTF(engine.url);
  const model=useMemo(()=>setWorldShadows(scene.clone(true)),[scene]);
  return <primitive object={model} dispose={null}/>;
}

export default function WarpEngine({simulation,onInspect}){
  const [nearby,setNearby]=useState(false);
  useEffect(()=>{
    const check=()=>{const p=simulation.current.position;setNearby(Math.hypot(p.x-engine.position[0],p.z-engine.position[2])<engine.loadRadius);};
    check();const timer=globalThis.setInterval(check,800);return()=>globalThis.clearInterval(timer);
  },[simulation]);
  if(!engine.ready||!nearby)return null;
  return <group position={engine.position} userData={{dynamicCollider:true}}>
    <CityAssetBoundary label={engine.label}><EngineModel/></CityAssetBoundary>
    <mesh position={[0,-.06,0]} receiveShadow><boxGeometry args={[4.6,.12,4.6]}/><meshStandardMaterial color="#293d4e" roughness={.45} metalness={.4}/></mesh>
    <Html position={[0,2.6,0]} center distanceFactor={14} zIndexRange={[3,0]}>
      <button className="cyber-world-label" onClick={()=>onInspect?.('Motor de dobra espacial: modelo de ficção científica para o laboratório PREPARATÓRIO.')}>
        {engine.label}
      </button>
    </Html>
  </group>;
}
