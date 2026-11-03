import {useMemo,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {useGLTF} from '@react-three/drei';
import {animateTruckRig,createTruckRig} from './truckArticulation.js';
import {resolveTruckProfile,resolveTruckTrailer} from './truckInteraction.js';

function TrailerModel({definition,simulation,profile}){
  const {scene}=useGLTF(definition.url),group=useRef(null);
  const rig=useMemo(()=>createTruckRig(scene,definition.height,0,definition.normalized,true),[scene,definition.height,definition.normalized]);
  useFrame(()=>{
    const truck=simulation.current.personalVehicles.truck;if(!truck||!group.current)return;
    group.current.visible=truck.trailer===definition.id&&resolveTruckProfile(truck.sourceId)?.id===profile.id;
    if(!group.current.visible)return;
    const angle=truck.articulationAngle??0;
    group.current.rotation.y=angle;
    group.current.position.set(profile.hitch[0]-Math.cos(angle)*definition.hitch[0]-Math.sin(angle)*definition.hitch[2],profile.hitch[1]-definition.hitch[1],
      profile.hitch[2]+Math.sin(angle)*definition.hitch[0]-Math.cos(angle)*definition.hitch[2]);
    animateTruckRig(rig,{wheelAngle:truck.trailerWheelAngle},definition);
  });
  const drawbarLength=definition.hitch[2]-definition.length/2;
  return <group ref={group}><primitive object={rig.outer} dispose={null}/>
    {drawbarLength>0&&<mesh castShadow receiveShadow position={[0,definition.hitch[1],(definition.hitch[2]+definition.length/2)/2]}>
      <boxGeometry args={[.16,.14,drawbarLength]}/><meshStandardMaterial color="#42464b" metalness={.7} roughness={.4}/>
    </mesh>}
  </group>;
}
export default function TruckModel({simulation,personal=false,profile:givenProfile,trailerId}){
  const profile=givenProfile??resolveTruckProfile(),{scene}=useGLTF(profile.url);
  const rig=useMemo(()=>createTruckRig(scene,profile.height,profile.sourceYaw??0,profile.normalized),[scene,profile.height,profile.sourceYaw,profile.normalized]);
  const definition=personal?resolveTruckTrailer({sourceId:profile.id,trailer:trailerId}):null;
  useFrame(()=>{
    const truck=personal?simulation.current.personalVehicles.truck:{};
    if(personal&&resolveTruckProfile(truck?.sourceId)?.id!==profile.id)return;
    animateTruckRig(rig,truck,profile);
  });
  return <group><primitive object={rig.outer} dispose={null}/>{personal&&definition&&<TrailerModel key={definition.id} definition={definition} simulation={simulation} profile={profile}/>}</group>;
}
