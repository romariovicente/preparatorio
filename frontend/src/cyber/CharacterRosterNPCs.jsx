import {Component,useEffect,useMemo,useRef,useState} from 'react';
import {Html} from '@react-three/drei';
import {useFrame,useThree} from '@react-three/fiber';
import {AnimationMixer,Raycaster} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {nearbyCharacterPlacements} from '../config/characterRoster.js';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';
import {disposeAssetPreview} from '../world/assetPreviewResources.js';
import {collectGroundSurfaces,sampleGroundHeight} from './groundSupport.js';
import {createUprightPosture} from './posture.js';
import {characterNpcMotionSample} from './characterNpcMotion.js';

class NPCBoundary extends Component{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?null:this.props.children;}
}

function PrivateNPCModel({entry}){
  const [model,setModel]=useState(null);
  const [failed,setFailed]=useState(false);
  const motion=useRef(null);
  useFrame((_,delta)=>{
    const current=motion.current;if(!current)return;
    current.mixer.update(Math.min(.05,Math.max(0,delta)));
    current.upright('Walk');
  });
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
        const pose=entry.standingPose??(entry.walkingAnimationAvailable?{clip:entry.playerAsset?.idleClip??entry.asset.idleClip??'Idle',time:0}:null);
        prepared=createFrozenCharacterClone(gltf.scene,entry.height,gltf.animations,pose);
        if(entry.walkingAnimationAvailable){
          const clipName=entry.playerAsset?.walkClip??entry.asset.walkClip??'Walk';
          const clip=gltf.animations.find(candidate=>candidate.name===clipName);
          if(clip){
            const mixer=new AnimationMixer(prepared.group),action=mixer.clipAction(clip).play();
            motion.current={mixer,action,upright:createUprightPosture(prepared.group)};
          }
        }
        setModel(prepared.group);
      }catch(error){
        if(active&&error.name!=='AbortError'){setModel(null);setFailed(true);}
      }
    }
    load();
    return()=>{
      active=false;abort.abort();
      motion.current?.action.stop();motion.current?.mixer.stopAllAction();
      if(prepared?.group)motion.current?.mixer.uncacheRoot(prepared.group);
      motion.current=null;
      if(prepared?.poseMixer){prepared.poseMixer.stopAllAction();prepared.poseMixer.uncacheRoot(prepared.group);}
      if(loadedScene)disposeAssetPreview([loadedScene,prepared?.group]);
      prepared=null;loadedScene=null;
    };
  },[entry.displayUrl,entry.height,entry.standingPose,entry.walkingAnimationAvailable,entry.playerAsset?.idleClip,entry.playerAsset?.walkClip,entry.asset.idleClip,entry.asset.walkClip]);
  return model?<primitive object={model} dispose={null}/>:failed?<Html position={[0,.5,0]} center><span style={{font:'10px system-ui',color:'#fff',background:'#612d2dcc',padding:4}}>Modelo indisponível · aproxime-se novamente para tentar</span></Html>:null;
}

// All actors have permanent, deterministic city positions, while only nearby
// models are loaded. Private loaders release GPU data when the player leaves.
// No procedural FK motion is run, including for NPCs with a legacy rig flag.
export default function CharacterRosterNPCs({placements,simulation,onSelect,onInspect,distance=18,maxVisible=4}){
  const [nearby,setNearby]=useState([]);
  const group=useRef(null),lastScan=useRef(-Infinity),groundYByActor=useRef(new Map()),{scene}=useThree();
  const ray=useMemo(()=>new Raycaster(),[]);
  const placementByActor=useMemo(()=>new Map(placements.map(entry=>[entry.actorId,entry])),[placements]);
  useFrame(({clock})=>{
    if(!group.current)return;
    for(const child of group.current.children){
      const entry=placementByActor.get(child.name);if(!entry)continue;
      const sample=characterNpcMotionSample(entry,clock.elapsedTime);
      // Keep the last raycast result between scans. Re-applying the authored Y
      // here made animated residents jump back into the air every frame.
      const groundedY=groundYByActor.current.get(entry.actorId)??sample.position[1];
      child.position.set(sample.position[0],groundedY,sample.position[2]);child.rotation.y=sample.heading;
    }
    if(clock.elapsedTime-lastScan.current<1.5)return;
    lastScan.current=clock.elapsedTime;
    const surfaces=collectGroundSurfaces(scene);
    for(const child of group.current.children){
      const entry=placementByActor.get(child.name);
      if(entry){
        const groundedY=sampleGroundHeight(ray,surfaces,{x:child.position.x,y:entry.position[1],z:child.position.z},{radius:.32})+.01;
        groundYByActor.current.set(entry.actorId,groundedY);child.position.y=groundedY;
      }
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
