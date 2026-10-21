import {useEffect,useMemo,useRef,useState} from 'react';
import {Html,useAnimations,useGLTF} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {createCharacterClone,findCharacterAction,startCharacterAction} from '../world/characterModel.js';
import {sampleHospitalPatientRoute} from './hospitalPatientFlow.js';

function Patient({entry,index,onInspect}){
  const root=useRef(null),phase=useRef('walking'),[waiting,setWaiting]=useState(false);
  const gltf=useGLTF(entry.playerAsset.url);
  const prepared=useMemo(()=>createCharacterClone(gltf.scene,entry.height??1.7),[gltf.scene,entry.height]);
  const {actions,mixer}=useAnimations(gltf.animations,prepared.group);
  useEffect(()=>{
    const clip=waiting?entry.playerAsset.idleClip:entry.playerAsset.walkClip;
    const action=findCharacterAction(actions,clip);startCharacterAction(action,mixer,true);
    return()=>action?.stop();
  },[actions,mixer,waiting,entry.playerAsset.idleClip,entry.playerAsset.walkClip]);
  useFrame(({clock})=>{
    const sample=sampleHospitalPatientRoute(clock.elapsedTime,{phaseOffset:index*12.5});
    if(root.current){root.current.position.fromArray(sample.position);root.current.rotation.y=sample.heading;}
    const next=sample.phase==='waiting';if(phase.current!==sample.phase){phase.current=sample.phase;setWaiting(next);}
  });
  return <group ref={root} name={`HOSPITAL_PATIENT_${index+1}`} userData={{actor:true,patient:true}}
    onClick={event=>{event.stopPropagation();onInspect?.(`${entry.name} · ${waiting?'aguardando acolhimento':'a caminho da triagem'}.`);}}>
    <primitive object={prepared.group} dispose={null}/>
    {waiting&&<Html position={[0,(entry.height??1.7)+.28,0]} center distanceFactor={12} zIndexRange={[2,0]} style={{pointerEvents:'none'}}>
      <span className="cyber-world-label">Paciente · aguardando triagem</span>
    </Html>}
  </group>;
}

export default function HospitalPatientFlow({entries,onInspect}){
  return <group name="PREP_HOSPITAL_PATIENT_FLOW">
    {entries.map((entry,index)=><Patient key={entry.id} entry={entry} index={index} onInspect={onInspect}/>)}
  </group>;
}
