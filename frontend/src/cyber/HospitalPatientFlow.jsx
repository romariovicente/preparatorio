import {useRef,useState} from 'react';
import {Html} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {isNearHospitalPatientRoute,sampleHospitalPatientRoute} from './hospitalPatientFlow.js';
import CostumedCharacter from './CostumedCharacter.jsx';
import CityAssetBoundary from './CityAssetBoundary.js';

const deferredPatientId='SUP_character_cyberpunk_free_3d_by_oscar_cre';

function Patient({entry,index,onInspect}){
  const root=useRef(null),phase=useRef('walking'),[waiting,setWaiting]=useState(false);
  useFrame(({clock})=>{
    const sample=sampleHospitalPatientRoute(clock.elapsedTime,{phaseOffset:index*12.5});
    if(root.current){root.current.position.fromArray(sample.position);root.current.rotation.y=sample.heading;}
    const next=sample.phase==='waiting';if(phase.current!==sample.phase){phase.current=sample.phase;setWaiting(next);}
  });
  return <group ref={root} name={`HOSPITAL_PATIENT_${index+1}`} userData={{actor:true,patient:true}}
    onClick={event=>{event.stopPropagation();onInspect?.(`${entry.name} · ${waiting?'aguardando acolhimento':'a caminho da triagem'}.`);}}>
    <CostumedCharacter asset={entry.playerAsset} height={entry.height??1.7} playing
      clip={waiting?entry.playerAsset.idleClip:entry.playerAsset.walkClip}/>
    {waiting&&<Html position={[0,(entry.height??1.7)+.28,0]} center distanceFactor={12} zIndexRange={[2,0]} style={{pointerEvents:'none'}}>
      <span className="cyber-world-label">Paciente · aguardando triagem</span>
    </Html>}
  </group>;
}

export default function HospitalPatientFlow({entries,onInspect,simulation,ready}){
  const [deferredPatientStarted,setDeferredPatientStarted]=useState(false);
  useFrame(()=>{
    if(ready&&!deferredPatientStarted&&isNearHospitalPatientRoute(simulation.current.position)){
      setDeferredPatientStarted(true);
    }
  });

  return <group name="PREP_HOSPITAL_PATIENT_FLOW">
    {entries.map((entry,index)=>(entry.id===deferredPatientId?deferredPatientStarted:ready)&&
      <CityAssetBoundary key={entry.id} label={`paciente · ${entry.name}`} assetUrls={[entry.playerAsset.url]}>
      <Patient entry={entry} index={index} onInspect={onInspect}/>
    </CityAssetBoundary>)}
  </group>;
}
