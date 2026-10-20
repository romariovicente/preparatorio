import {Component,useEffect,useMemo,useRef,useState} from 'react';
import {Html} from '@react-three/drei';
import {useFrame,useThree} from '@react-three/fiber';
import {Raycaster} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {nearbyCharacterPlacements} from '../config/characterRoster.js';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';
import {disposeAssetPreview} from '../world/assetPreviewResources.js';
import {collectGroundSurfaces,sampleGroundHeight} from './groundSupport.js';

class NPCBoundary extends Component{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?null:this.props.children;}
}

function PrivateNPCModel({entry}){
  const [model,setModel]=useState(null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    let active=true,prepared=null,loadedScene=null;
    const abort=new AbortController();
    async function load(){
      try{
        const response=await fetch(entry.displayUrl,{signal:abort.signal});
        if(!response.ok)throw new Error('Modelo indisponível.');
        const buffer=await response.arrayBuffer();
        const base=new URL('./',new URL(entry.displayUrl,globalThis.location.href)).href;
        const gltf=await new GLTFLoader().parseAsync(buffer,base);loadedScene=gltf.scene;
        if(!active){disposeAssetPreview(loadedScene);loadedScene=null;return;}
        const pose=entry.standingPose??(entry.controlMode==='native'?{clip:entry.asset.idleClip??'Idle',time:0}:null);
        prepared=createFrozenCharacterClone(gltf.scene,entry.height,gltf.animations,pose);
        setModel(prepared.group);
      }catch(error){
        if(active&&error.name!=='AbortError'){setModel(null);setFailed(true);}
      }
    }
    load();
    return()=>{
      active=false;abort.abort();
      if(prepared?.poseMixer){prepared.poseMixer.stopAllAction();prepared.poseMixer.uncacheRoot(prepared.group);}
      if(loadedScene)disposeAssetPreview([loadedScene,prepared?.group]);
      prepared=null;loadedScene=null;
    };
  },[entry.displayUrl,entry.height,entry.standingPose,entry.controlMode,entry.asset.idleClip]);
  return model?<primitive object={model} dispose={null}/>:failed?<Html position={[0,.5,0]} center><span style={{font:'10px system-ui',color:'#fff',background:'#612d2dcc',padding:4}}>Modelo indisponível · aproxime-se novamente para tentar</span></Html>:null;
}

// All actors have permanent, deterministic city positions, while only nearby
// models are loaded. Private loaders release GPU data when the player leaves.
// No procedural FK motion is run, including for NPCs with a legacy rig flag.
export default function CharacterRosterNPCs({placements,simulation,onSelect,onInspect,distance=18,maxVisible=4}){
  const [nearby,setNearby]=useState([]);
  const group=useRef(null),lastScan=useRef(-Infinity),{scene}=useThree();
  const ray=useMemo(()=>new Raycaster(),[]);
  useFrame(({clock})=>{
    if(!group.current||clock.elapsedTime-lastScan.current<1.5)return;
    lastScan.current=clock.elapsedTime;
    const surfaces=collectGroundSurfaces(scene);
    for(const child of group.current.children){
      const baseline=placements.find(entry=>entry.actorId===child.name)?.position;
      if(baseline)child.position.y=sampleGroundHeight(ray,surfaces,{x:baseline[0],y:baseline[1],z:baseline[2]},{radius:.32})+.01;
    }
  });
  useEffect(()=>{
    const interval=globalThis.setInterval(()=>{
      const next=nearbyCharacterPlacements(placements,simulation.current?.position,{distance,maxVisible});
      setNearby(previous=>previous.map(entry=>entry.id).join('|')===next.map(entry=>entry.id).join('|')?previous:next);
    },300);
    return()=>globalThis.clearInterval(interval);
  },[placements,simulation,distance,maxVisible]);
  const active=new Set(nearby.map(entry=>entry.id));
  return <group ref={group} name="PREP_CHARACTER_ROSTER" userData={{actor:true}}>
    {placements.filter(entry=>entry.position).map(entry=><group key={entry.id} name={entry.actorId} position={entry.position} rotation={[0,entry.heading,0]} userData={{actor:true}}>
      {active.has(entry.id)&&<NPCBoundary><PrivateNPCModel entry={entry}/></NPCBoundary>}
      {active.has(entry.id)&&<Html position={[0,entry.height+.35,0]} center distanceFactor={11} zIndexRange={[3,0]} style={{pointerEvents:'auto'}}>
        <button type="button" onClick={()=>entry.controllable?onSelect?.(entry.playerAsset):onInspect?.(entry)}
          title={`${entry.name} · ${entry.context}`}
          aria-label={`${entry.controllable?'Escolher personagem':'Conhecer morador'} · ${entry.name}`}
          style={{font:'10px system-ui',color:'#e8f5ff',background:'#0c2433dd',border:'1px solid #668a9f',borderRadius:5,padding:'5px 8px',whiteSpace:'nowrap',cursor:'pointer'}}>
          {entry.name}<span style={{display:'block',fontSize:8,color:'#b7d7e7'}}>{entry.statusLabel}</span>
        </button>
      </Html>}
    </group>)}
  </group>;
}
