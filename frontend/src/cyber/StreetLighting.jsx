import {useMemo,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {collectStreetLampSites,selectStreetLampSites,STREET_LIGHT_DISTANCE,STREET_LIGHT_LIMIT} from './streetLighting.js';

const LIGHT_SLOTS=Array.from({length:STREET_LIGHT_LIMIT},(_,index)=>index);

export default function StreetLighting({model,simulation,active}) {
  const sites=useMemo(()=>collectStreetLampSites(model),[model]);
  const lights=useRef([]);
  const nextSample=useRef(0);

  useFrame(({clock})=>{
    if(!active){
      nextSample.current=0;
      return;
    }
    if(clock.elapsedTime<nextSample.current)return;
    nextSample.current=clock.elapsedTime+.15;
    const nearby=selectStreetLampSites(sites,simulation.current.position);
    for(const index of LIGHT_SLOTS){
      const light=lights.current[index];
      const site=nearby[index];
      if(site)light.position.copy(site);
      light.intensity=site?85:0;
    }
  });

  return <group visible={active}>
    {LIGHT_SLOTS.map(index=><pointLight key={index} ref={light=>{lights.current[index]=light;}}
      color="#ffe1b4" intensity={0} distance={STREET_LIGHT_DISTANCE} decay={2}/>)}
  </group>;
}
