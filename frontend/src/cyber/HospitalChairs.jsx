import {useEffect,useMemo} from 'react';
import {useGLTF} from '@react-three/drei';
import {createHospitalChairClone,hospitalChairAssetUrl} from './hospitalChairs.js';

export default function HospitalChairs({plan,onReady}){
  const {scene}=useGLTF(hospitalChairAssetUrl(plan));
  const chairs=useMemo(()=>plan.placements.map(placement=>({placement,model:createHospitalChairClone(scene)})),[scene,plan]);
  useEffect(()=>{onReady?.(true);return()=>onReady?.(false);},[onReady]);
  return <group name="PREP_HOSPITAL_CHAIRS" dispose={null}>
    {chairs.map(({placement,model})=><group key={placement.id} name={placement.id}
      position={placement.position} rotation={placement.rotation??[0,0,0]}>
      <primitive object={model} dispose={null}/>
    </group>)}
  </group>;
}
