import {useLayoutEffect,useMemo,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {useGLTF} from '@react-three/drei';
import {animateTruckRig,createTruckRig} from './truckArticulation.js';
import CityAssetBoundary from './CityAssetBoundary.js';
import {resolveTruckProfile} from './truckInteraction.js';

function TrailerModel({definition,simulation,profile,onTrailerPositioned}){
  const {scene}=useGLTF(definition.url),group=useRef(null);
  const rig=useMemo(()=>createTruckRig(scene,definition.height,0,definition.normalized,true),[scene,definition.height,definition.normalized]);
  const trailerId=definition.id;
  useLayoutEffect(()=>()=>onTrailerPositioned(trailerId,false),[onTrailerPositioned,trailerId]);
  useFrame(()=>{
    const truck=simulation.current.personalVehicles.truck;
    const model=group.current;
    if(!model)return;
    model.visible=truck?.trailer===trailerId&&resolveTruckProfile(truck.sourceId)?.id===profile.id;
    if(!model.visible)return;
    const angle=truck.articulationAngle??0;
    model.rotation.y=angle;
    model.position.set(profile.hitch[0]-Math.cos(angle)*definition.hitch[0]-Math.sin(angle)*definition.hitch[2],profile.hitch[1]-definition.hitch[1],
      profile.hitch[2]+Math.sin(angle)*definition.hitch[0]-Math.cos(angle)*definition.hitch[2]);
    model.visible=[model.position.x,model.position.y,model.position.z,angle].every(Number.isFinite);
    onTrailerPositioned(trailerId,model.visible);
    animateTruckRig(rig,{wheelAngle:truck.trailerWheelAngle},definition);
  });
  const drawbarLength=definition.hitch[2]-definition.length/2;
  return <group ref={group} visible={false}><primitive object={rig.outer} dispose={null}/>
    {drawbarLength>0&&<mesh castShadow receiveShadow position={[0,definition.hitch[1],(definition.hitch[2]+definition.length/2)/2]}>
      <boxGeometry args={[.16,.14,drawbarLength]}/><meshStandardMaterial color="#42464b" metalness={.7} roughness={.4}/>
    </mesh>}
  </group>;
}
export default function TruckModel({simulation,profile,definition,onTrailerPositioned}){
  const {scene}=useGLTF(profile.url);
  const rig=useMemo(()=>createTruckRig(scene,profile.height,profile.sourceYaw??0,profile.normalized),[scene,profile.height,profile.sourceYaw,profile.normalized]);
  useFrame(()=>{
    const truck=simulation.current.personalVehicles.truck;
    if(resolveTruckProfile(truck?.sourceId)?.id!==profile.id)return;
    animateTruckRig(rig,truck,profile);
  });
  return <group><primitive object={rig.outer} dispose={null}/>{definition&&
    <CityAssetBoundary key={definition.id} label={definition.label} assetUrls={[definition.url]}>
      <TrailerModel definition={definition} simulation={simulation} profile={profile} onTrailerPositioned={onTrailerPositioned}/>
    </CityAssetBoundary>}
  </group>;
}
