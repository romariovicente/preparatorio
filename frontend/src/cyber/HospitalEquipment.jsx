import {useEffect,useMemo,useState} from 'react';
import {Html,useGLTF} from '@react-three/drei';
import plan from '../config/hospitalEquipment.json';
import {assetUrl} from '../config/deploymentConfig.js';
import {setWorldShadows} from './modelLighting.js';
import CityAssetBoundary from './CityAssetBoundary.js';

const url=assetUrl(plan.asset);
function AmbientMonitor(){
  const {scene}=useGLTF(url);
  const model=useMemo(()=>setWorldShadows(scene.clone(true)),[scene]);
  return <primitive object={model} dispose={null}/>;
}

export default function HospitalEquipment({simulation,onInspect}){
  const [range,setRange]=useState('far');
  useEffect(()=>{
    const check=()=>{
      const p=simulation.current.position;
      const distance=Math.hypot(p.x-plan.worldPosition[0],p.z-plan.worldPosition[2]);
      setRange(distance<plan.labelRadius?'close':distance<plan.loadRadius?'near':'far');
    };
    check();const timer=globalThis.setInterval(check,700);return()=>globalThis.clearInterval(timer);
  },[simulation]);
  if(!plan.ready||range==='far')return null;
  const inspect=()=>onInspect?.(plan.notice);
  return <group name="PREP_HOSPITAL_AMBIENT_MONITOR" position={plan.localPosition} rotation={plan.localRotation}
    onClick={event=>{event.stopPropagation();inspect();}}>
    <CityAssetBoundary label="monitor de temperatura e umidade" assetUrls={[url]}><AmbientMonitor/></CityAssetBoundary>
    {range==='close'&&<Html position={[0,.29,0]} center distanceFactor={4} zIndexRange={[3,0]}>
      <button className="cyber-world-label" onClick={inspect}>Monitor de temperatura e umidade<br/>Peça de demonstração</button>
    </Html>}
  </group>;
}
