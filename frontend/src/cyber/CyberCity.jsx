import {clockSourceLabel,sharedServiceLabel} from '../config/serviceStatus.js';
import {deployment,resolveAssetReferences} from '../config/deploymentConfig.js';
import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Bounds, Html, Line, OrbitControls, useGLTF } from '@react-three/drei';
import { PCFShadowMap, Raycaster, Vector3 } from 'three';
import { playableCharacters as catalogCharacters } from '../config/runtimeAssets.js';
import manifestRaw from '../config/cyberWorldManifest.json';
const manifest=resolveAssetReferences(manifestRaw);
import costumesRaw from '../config/costumeAssets.json';
const costumes=resolveAssetReferences(costumesRaw);
import realisticWorldRaw from '../config/realisticWorldManifest.json';
const realisticWorld=resolveAssetReferences(realisticWorldRaw);
import buildings from '../config/buildingDoors.json';
import monumentsRaw from '../config/monumentAssets.json';
const monuments=resolveAssetReferences(monumentsRaw);
import BuildingDoors from './BuildingDoors.jsx';
import DetailedWorld from './DetailedWorld.jsx';
import NewDeliveryWorld from './NewDeliveryWorld.jsx';
import FuturisticClassroom from './FuturisticClassroom.jsx';
import {createClassroomRuntime,classroomColliders,classroomZones,openClassroomDoor} from './classroomWorld.js';
import {getDeliveryReplacement,newDeliveryColliders,newDeliveryZones,newDeliveryHidePrefixes,resolveDeliveryParking} from './newDeliveryWorld.js';
import CarModel from './CarModel.jsx';
import BusModel from './BusModel.jsx';
import BusControls from './BusControls.jsx';
import {BUS_IDS,BUS_DEFINITIONS,sampleLiveBus,nearestBus,busFootprint,busDoorPosition} from './busInteraction.js';
import {nearestInteractiveCar,resolveCarSource,canEnterCar,listInteractiveCars} from './carInteraction.js';
import {setDirectionKey,textEntryTarget} from './directionControls.js';
import {carMotion,wheelRotation} from './vehicleMotion.js';
import {cycleItem} from './itemSelection.js';
import {nearestMotorcycle,resolveMotorcycle} from './motorcycleInteraction.js';
import MotorcycleModel from './MotorcycleModel.jsx';
import {GameAudioLoop,useGameAudio} from './GameAudio.jsx';
import {cityColliders,doorApproach,doorPosition} from './doorGeometry.js';
import {createSolidIndex,solidMovement,footprintCollider} from './collisions.js';
import {collectGroundSurfaces,sampleGroundHeight} from './groundSupport.js';
import suppliedCatalogRaw from '../config/suppliedAssets.json';
const suppliedCatalog=resolveAssetReferences(suppliedCatalogRaw);
import SuppliedModel from '../world/SuppliedModel.jsx';
import CostumedCharacter from './CostumedCharacter.jsx';
import SolarSky from './SolarSky.jsx';
import {useServerClock} from './useServerClock.js';
import {setWorldShadows} from './modelLighting.js';
import { carriedObject } from '../world/interactionState.js';
import { useSharedObjects } from '../network/useSharedObjects.js';
import {readPlayerName,savePlayerName} from '../network/playerIdentity.js';
import { interactionRooms } from '../network/roomConfig.js';
import { rewardBalance, readProgress } from '../world/progress.js';
import { locationIds } from '../world/locations.js';
import { askJarvis, unlockHome, getPrivateHomeLayout, getPrivateHomeAsset } from './rpgApi.js';
import { createSeatedClone } from './seating.js';
import { createTrafficLightController } from './traffic.js';
import { advanceCityPosition, applyCyberAction, CITY_START, DEFAULT_PARKING, DRIVE_VEHICLES, ELEVATOR_POSITION, FARM_PLOTS, FLOWER_BASES, restoreCyberState, sampleTransit, sampleWorldClock, saveCyberState, tickCyberState, TRANSIT_ROUTES } from './simulation.js';
import './cyber.css';

const benches = [{id:'bench-west',position:{x:-12,y:0,z:8}},{id:'bench-east',position:{x:12,y:0,z:8}}];
const initialTractor = {x:12,y:0,z:96};
const prop = id => manifest.props.find(item => item.id === id);
const near = (position,target,radius=12) => Math.hypot(position.x-target[0],position.z-target[2]) <= radius;
const shadowSettings = {type:PCFShadowMap};
const zones = manifest.zones;
const parkingPlaces=resolveDeliveryParking(manifest.parking??DEFAULT_PARKING).map(p=>({...p,label:p.label??p.id.replace(/-/g,' · ')}));
const costumeFor = asset => costumes.find(item=>item.baseId===asset?.id&&item.reimportValidated);
const realismDirectionKey = 'prep.realism.direction.v1';
const currentDirection = '20261005';
const isRealisticHuman = asset => asset?.reimportValidated&&
  (asset.id==='CHR_Remy_Mixamo_20261005'||asset.visualStyle==='realistic');
const realisticHumans=catalogCharacters.filter(isRealisticHuman);
// The old FK and stylized assets remain in the separate Acervo 3D viewer.
// Once real human motion capture is validated, only those bodies enter gameplay.
const playableCharacters=realisticHumans.length?realisticHumans:catalogCharacters;
const uniformCharacters=playableCharacters.filter(costumeFor);
// Prefer a verified human motion-capture asset when it becomes available. The
// complete supplied catalog remains selectable and its originals are untouched.
const preferredCharacter = playableCharacters.find(isRealisticHuman)
  ??playableCharacters.find(asset=>asset.id==='SUP_doctor_horror_hospital')
  ??playableCharacters.find(asset=>asset.id==='SUP_woman_standing_v16')??playableCharacters[0];
function initialCharacter() {
  try {
    if(isRealisticHuman(preferredCharacter)&&localStorage.getItem(realismDirectionKey)!==currentDirection) {
      // A single migration establishes the new art direction, then deliberate
      // catalog-preview selections continue to persist normally.
      localStorage.setItem(realismDirectionKey,currentDirection);
      localStorage.setItem('prep.character.v1',preferredCharacter.id);
      return preferredCharacter;
    }
    return playableCharacters.find(asset=>asset.id===localStorage.getItem('prep.character.v1'))??preferredCharacter;
  } catch { return preferredCharacter; }
}
const transportDestinations = Object.entries(TRANSIT_ROUTES).map(([id,route])=>({id:`${id}-boarding`,label:`Parada inicial · ${route.label}`,position:[route.stops[0].position.x+6,0,route.stops[0].position.z+3]}));
const elevatorDestination={id:'elevator-entry',label:'Elevador da galeria',position:[ELEVATOR_POSITION.x,0,ELEVATOR_POSITION.z+2]};

function PlayerNameForm({value,onChange,onSubmit}) {
  return <form onSubmit={onSubmit}>
    <label>Nome do usuário<input value={value} maxLength={96} onChange={event=>onChange(event.target.value)} autoComplete="nickname"/></label>
    <button type="submit">Salvar nome no jaleco</button>
  </form>;
}

class CityBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?<div className="cyber-loading" role="status">Não foi possível abrir este modelo 3D. As ações e os terminais continuam disponíveis.</div>:this.props.children;}
}
function Environment({onReady,simulation}) {
  const {scene}=useGLTF(manifest.sceneUrl);
  const model=useMemo(()=>{
    const copy=setWorldShadows(scene.clone(true));
    const prefixes=[...buildings.flatMap(b=>b.hidePrefixes),...realisticWorld.environmentReplacements.flatMap(r=>r.hidePrefixes),...monuments.flatMap(r=>r.hidePrefixes),...newDeliveryHidePrefixes,'NPC_','CLOCK_','CYCLE_'];
    copy.traverse(object=>{if(prefixes.some(p=>object.name.startsWith(p)))object.visible=false;});
    return copy;
  },[scene]);
  const traffic=useMemo(()=>createTrafficLightController(model),[model]);
  useEffect(()=>{onReady();},[onReady]);
  useEffect(()=>()=>traffic.dispose(),[traffic]);
  useFrame(()=>traffic.update(simulation.current.elapsed));
  return <primitive object={model} dispose={null}/>;
}
function SunLight({simulation,night}) {
  const light=useRef(null);
  useFrame(()=>{
    if(!light.current)return;
    const position=simulation.current.position;
    // Keep a useful shadow resolution around the player rather than spreading
    // the same map over the entire 236 m city. The source clock still drives day.
    light.current.position.set(position.x+35,position.y+55,position.z+25);
    light.current.target.position.set(position.x,position.y,position.z);
    light.current.target.updateMatrixWorld();
  });
  return <directionalLight ref={light} position={[35,55,25]} color={night?'#b5cced':'#fff0d8'} intensity={night?.35:2.4} castShadow
    shadow-mapSize={[1024,1024]} shadow-camera-left={-40} shadow-camera-right={40}
    shadow-camera-top={40} shadow-camera-bottom={-40} shadow-camera-near={1} shadow-camera-far={180}
    shadow-bias={-.00015} shadow-normalBias={.025} shadow-radius={2}/>;
}
function AssetProp({id,height,...props}) {
  const asset=prop(id);
  if(!asset)return null;
  return <group {...props}><ShadowedModel asset={asset} height={height}/></group>;
}
function ShadowedModel({asset,height}) {
  const group=useRef(null);
  useEffect(()=>{if(group.current)setWorldShadows(group.current);},[asset.url,height]);
  return <group ref={group}><SuppliedModel asset={asset} height={height}/></group>;
}
function Part({position,size,color,emissive=false}) {
  return <mesh position={position} castShadow receiveShadow><boxGeometry args={size}/><meshStandardMaterial color={color} roughness={.65} emissive={emissive?color:'#000000'} emissiveIntensity={emissive?.6:0}/></mesh>;
}
function SeatedModel({asset}) {
  const {scene}=useGLTF(asset.url),pose=useMemo(()=>{const copy=createSeatedClone(scene);setWorldShadows(copy.group);return copy;},[scene]);
  return <group position={[0,pose.offset,0]}><primitive object={pose.group} dispose={null}/></group>;
}
function Actor({asset,snapshot,simulation,tractorRef,held,displayName}) {
  const group=useRef(null);
  const {scene}=useThree(),floorSurfaces=useRef([]),lastGroundScan=useRef(-Infinity);
  const ray=useMemo(()=>new Raycaster(),[]);
  useFrame(()=>{
    if(!group.current)return;
    const current=simulation.current;
    if(current.elapsed-lastGroundScan.current>1.5){floorSurfaces.current=collectGroundSurfaces(scene);lastGroundScan.current=current.elapsed;}
    let floor=current.position.y;
    if(['foot','mototaxi'].includes(current.mode)&&!current.elevator){
      floor=sampleGroundHeight(ray,floorSurfaces.current,current.position,{radius:current.mode==='foot'?.32:0})+.01;
    }
    if(BUS_IDS.includes(current.mode)){
      const bus=sampleLiveBus(current,current.mode);
      floor=current.position.y+sampleGroundHeight(ray,floorSurfaces.current,{x:bus.x,y:0,z:bus.z},{radius:0})+.01;
    }
    const riderOffset=current.mode==='mototaxi'?-.4:0;
    group.current.position.set(current.position.x+Math.sin(current.heading)*riderOffset,floor+(current.jumpHeight??0)+(current.mode==='mototaxi'?.24:0),current.position.z+Math.cos(current.heading)*riderOffset);
    group.current.rotation.y=current.heading;
    if(current.mode==='tractor')tractorRef.current={x:current.position.x,y:0,z:current.position.z,heading:current.heading};
  });
  return <group ref={group} position={[CITY_START.x,0,CITY_START.z]} userData={{actor:true}}>
    <group visible={snapshot.mode!=='car'}><CostumedCharacter asset={asset} height={1.7} outfit={snapshot.outfit} displayName={displayName} playing clip={snapshot.jump?'Idle':snapshot.action} holding={Boolean(held)} sitting={snapshot.sitting} riding={snapshot.mode==='mototaxi'}/></group>
    {snapshot.fishing&&<AssetProp id="fishing-rod" height={1.45} position={[.35,.9,.3]} rotation={[0,0,-.45]}/>}
    {held&&<AssetProp id={interactionRooms.cyber.templates.find(t=>t.id===held.templateId)?.kind} height={held.templateId==='cyber_fishing_rod'?1.4:.45} position={[0,1,.4]}/>}
  </group>;
}
function Vehicle({id,simulation,personal=false,onAsk,onSelect}) {
  const group=useRef(null),asset=id==='car'&&personal?(resolveCarSource(simulation.current.personalVehicles.car?.sourceId??'car')?.asset??realisticWorld.dynamicReplacements.car):getDeliveryReplacement(id)??realisticWorld.dynamicReplacements[id]??prop(id);
  const {scene}=useThree(),surfaces=useRef([]),lastGroundScan=useRef(-Infinity),ray=useMemo(()=>new Raycaster(),[]);
  useFrame(()=>{
    if(!group.current)return;
    const position=BUS_IDS.includes(id)?sampleLiveBus(simulation.current,id):TRANSIT_ROUTES[id]?sampleTransit(TRANSIT_ROUTES[id],simulation.current.elapsed):personal?simulation.current.personalVehicles[id]:DRIVE_VEHICLES[id].position;
    if(!position)return;
    if(simulation.current.elapsed-lastGroundScan.current>1.5){surfaces.current=collectGroundSurfaces(scene);lastGroundScan.current=simulation.current.elapsed;}
    const floor=sampleGroundHeight(ray,surfaces.current,{...position,y:position.y??0},{radius:0});
    group.current.position.set(position.x,floor+.01,position.z);
    group.current.rotation.y=position.heading ?? 0;
  });
  const driver=preferredCharacter;
  const liveBus=BUS_IDS.includes(id)?sampleLiveBus(simulation.current,id):null;
  return asset?<group ref={group} userData={{dynamicCollider:true}} onClick={['car','mototaxi',...BUS_IDS].includes(id)?event=>{event.stopPropagation();onSelect?.(personal?id==='car'?'personal-car':'personal-moto':id);}:undefined}>
    {id==='car'?<CarModel asset={asset} simulation={simulation} personal={personal} open={personal&&simulation.current.carControls?.doorOpen}/>:id==='mototaxi'?<MotorcycleModel asset={asset} simulation={simulation} personal={personal}/>:liveBus?<BusModel asset={asset} simulation={simulation} id={id}/>:<ShadowedModel asset={asset} height={asset.height??(id==='tractor'?2.2:id==='harvester'?3.5:3.2)}/>}
    {personal&&id==='truck'&&<AssetProp id={`truck-trailer-${simulation.current.trailer}`} height={simulation.current.trailer==='flatbed'?1.6:3} position={[0,0,-7.5]}/>}
    {TRANSIT_ROUTES[id]&&driver&&liveBus?.control!=='player'&&<group position={liveBus?BUS_DEFINITIONS[id].driverSeat:[.6,1.1,6]}><SeatedModel asset={driver}/><Html position={[0,1.8,0]} center distanceFactor={12} zIndexRange={[1,0]}><button className="cyber-world-label" onClick={event=>{event.stopPropagation();onAsk('guide',liveBus?'Motorista do ônibus':'Maquinista do trem');}}>Conversar com {liveBus?'motorista':'maquinista'}</button></Html></group>}
  </group>:null;
}
function GrowthPlot({plot,planted,elapsed,onSelect}) {
  const progress=planted?Math.min(1,(elapsed-planted.plantedAt)/20):0;
  return <group position={[plot.position.x,0,plot.position.z]} onClick={event=>{event.stopPropagation();onSelect(plot.id);}}>
    <Part position={[0,.025,0]} size={[3,.05,3]} color="#3b241f"/>
    {!!progress&&[-.8,0,.8].flatMap(x=>[-.7,.6].map(z=><group key={`${x}-${z}`} position={[x,0,z]} scale={[1,Math.max(.1,progress),1]}>
      <mesh position={[0,.5,0]}><cylinderGeometry args={[.04,.055,1,6]}/><meshStandardMaterial color="#4cab53"/></mesh>
      <mesh position={[.1,.6,0]} rotation={[0,0,.65]}><sphereGeometry args={[.2,6,4]}/><meshStandardMaterial color={progress===1?'#eac84c':'#5cbc64'}/></mesh>
    </group>))}
  </group>;
}
function RuntimeLoop({simulationRef,input:inputRef,controls,onSnapshot,onNotice,tractorRef,spaceView,doors,worldObjects,classroomRuntime}) {
  const accumulator=useRef(0);
  const {scene}=useThree(),solids=useRef([]),lastIndex=useRef(-Infinity);
  const detailed=useMemo(()=>realisticWorld.environmentReplacements.filter(r=>r.position[1]<1).map(r=>{const box=footprintCollider(r,suppliedCatalog);return box?{...box,id:r.id}:null;}).filter(Boolean),[]);
  useFrame(({camera},delta)=>{
    const previous=simulationRef.current;
    let jumping=previous;
    if(inputRef.current.jumpPressed){inputRef.current.jumpPressed=false;const result=applyCyberAction(previous,{type:'JUMP'});if(result.ok)jumping=result.state;else onNotice(result.message);}
    const parked=Object.entries(DRIVE_VEHICLES).map(([id,definition])=>{
      const p=jumping.personalVehicles[id]??definition.position;
      return {id,x:p.x,z:p.z,w:id==='mototaxi'?1:2.8,d:id==='truck'?7:4};
    });
    const transitObstacles=[...cityColliders(manifest.colliders??[],buildings,doors),...newDeliveryColliders,...classroomColliders(classroomRuntime),...detailed,...parked];
    let next=tickCyberState(jumping,delta,{obstacles:transitObstacles});
    const keys=inputRef.current;
    if(next.elapsed-lastIndex.current>1.5){solids.current=createSolidIndex(scene);lastIndex.current=next.elapsed;}
    if(!spaceView&&BUS_IDS.includes(next.mode)&&next.busControls?.role==='driver'&&sampleLiveBus(next,next.mode).engineOn){
      const otherBuses=BUS_IDS.filter(id=>id!==next.mode).map(id=>busFootprint(sampleLiveBus(next,id)));
      const obstacles=[...transitObstacles,...otherBuses];
      const result=applyCyberAction(next,{type:'BUS_DRIVE',keys,delta},{obstacles});
      if(result.ok)next=result.state;
    }
    if(!spaceView&&((next.mode==='foot'&&!next.sitting&&!next.elevator)||DRIVE_VEHICLES[next.mode]&&(next.mode!=='car'||next.carControls?.engineOn&&!next.carControls?.doorOpen)&&(next.mode!=='mototaxi'||next.motorcycleControls?.engineOn))) {
      const forward=new Vector3();camera.getWorldDirection(forward);forward.y=0;forward.normalize();
      const right=new Vector3().crossVectors(forward,new Vector3(0,1,0));
      let direction=forward.multiplyScalar((keys.w?1:0)-(keys.s?1:0)).add(right.multiplyScalar((keys.d?1:0)-(keys.a?1:0)));
      if(keys.target&&next.mode==='foot'){
        const aim=new Vector3(keys.target.x-next.position.x,0,keys.target.z-next.position.z);
        if(aim.length()<.18)inputRef.current={};else direction=aim;
      }
      if(direction.lengthSq()>0) {
        const drive=DRIVE_VEHICLES[next.mode];
        const motion=['car','mototaxi'].includes(next.mode)?carMotion(next.heading,keys,delta,drive.speed,next.mode==='mototaxi'?1.4:2.7):null;
        if(motion)direction=new Vector3(motion.direction.x,0,motion.direction.z);
        const moving=[];
        for(const [id,definition]of Object.entries(DRIVE_VEHICLES))for(const [personal,p]of [[false,definition.position],[true,next.personalVehicles[id]]]){
          if(!p||personal&&next.mode===id||!personal&&next.personalVehicles[id])continue;
          const source=id==='car'&&personal?resolveCarSource(p.sourceId??'car')?.asset:realisticWorld.dynamicReplacements[id],shape=source?footprintCollider({...source,position:[p.x,0,p.z],rotation:[0,p.heading??0,0]},suppliedCatalog):{x:p.x,z:p.z,w:id==='mototaxi'?1:2.8,d:id==='truck'?7:4};if(shape)moving.push(shape);
        }
        for(const id of BUS_IDS)moving.push(busFootprint(sampleLiveBus(next,id)));
        const train=sampleTransit(TRANSIT_ROUTES.train,next.elapsed);
        moving.push({x:train.x,z:train.z,w:Math.abs(Math.cos(train.heading))*3+Math.abs(Math.sin(train.heading))*12,d:Math.abs(Math.sin(train.heading))*3+Math.abs(Math.cos(train.heading))*12});
        for(const o of worldObjects??[])if(o.position&&interactionRooms.cyber.templates.find(t=>t.id===o.templateId)?.kind==='bench')moving.push({x:o.position.x,z:o.position.z,w:2,d:.8});
        const obstacles=[...cityColliders(manifest.colliders??[],buildings,doors),...newDeliveryColliders,...classroomColliders(classroomRuntime),...detailed.filter(r=>r.id!==next.personalVehicles.car?.sourceId&&r.id!==next.personalVehicles.mototaxi?.sourceId),...moving];
        let position=advanceCityPosition(next.position,direction,delta,motion?motion.speed:drive?drive.speed:keys.shift?9:5,obstacles,drive&&drive.id!=='mototaxi'?next.mode==='car'?2.35:1.3:.4);
        position=solidMovement(solids.current,next.position,position,next.mode==='mototaxi'?.42:drive?1.1:.38);
        if(drive?.farmOnly)position={...position,x:Math.max(-22,Math.min(22,position.x)),z:Math.max(86,Math.min(114,position.z))};
        if(next.position.y<-.1){const bounds=manifest.undergroundBounds??{minX:-28,maxX:-8,minZ:49,maxZ:69};position={...position,x:Math.max(bounds.minX,Math.min(bounds.maxX,position.x)),z:Math.max(bounds.minZ,Math.min(bounds.maxZ,position.z))};}
        const dx=position.x-next.position.x,dz=position.z-next.position.z;
        const heading=motion?Math.hypot(dx,dz)>.00001?motion.heading:next.heading:Math.hypot(dx,dz)>.00001?Math.atan2(dx,dz):next.heading;
        const originalVehicle=next.personalVehicles[next.mode];
        const wheelAngle=motion?wheelRotation(originalVehicle?.wheelAngle,next.position,position,heading,next.mode==='mototaxi'?.3:.34):0;
        next={...next,position,heading,action:next.mode==='foot'?'Walk':'Idle',...(drive?{personalVehicles:{...next.personalVehicles,[next.mode]:{...originalVehicle,x:position.x,y:0,z:position.z,heading,...(motion?{steeringAngle:motion.steeringAngle,wheelAngle}:{})}}}:{})};
      }else if(next.action==='Walk')next={...next,action:'Idle'};
    }
    if(BUS_IDS.includes(next.mode))next={...next,heading:sampleLiveBus(next,next.mode).heading};
    else if(TRANSIT_ROUTES[next.mode])next={...next,heading:sampleTransit(TRANSIT_ROUTES[next.mode],next.elapsed).heading};
    const dx=next.position.x-previous.position.x,dy=next.position.y-previous.position.y,dz=next.position.z-previous.position.z;
    if(!spaceView){camera.position.add(new Vector3(dx,dy,dz));if(next.position.y<-1)camera.position.y=Math.min(camera.position.y,next.position.y+2.8);controls.current?.target.set(next.position.x,next.position.y+1,next.position.z);}
    if(!spaceView&&['car','mototaxi'].includes(next.mode)&&previous.mode!==next.mode){camera.position.set(next.position.x-Math.sin(next.heading)*9+Math.cos(next.heading)*4,3.6,next.position.z-Math.cos(next.heading)*9-Math.sin(next.heading)*4);controls.current?.update();}
    if(['car','mototaxi'].includes(next.mode)&&next.personalVehicles[next.mode]){const motion=carMotion(next.heading,keys,delta);next={...next,personalVehicles:{...next.personalVehicles,[next.mode]:{...next.personalVehicles[next.mode],steeringAngle:motion.steeringAngle}}};}
    simulationRef.current=next;
    if(next.lastMessage!==previous.lastMessage)onNotice(next.lastMessage);
    if(next.mode==='tractor')tractorRef.current={x:next.position.x,y:0,z:next.position.z,heading:next.heading};
    accumulator.current+=delta;
    if(accumulator.current>.12){accumulator.current=0;onSnapshot(next);}
  });
  return null;
}
function NPC({id,position,name,onAsk}) {
  const asset=preferredCharacter;
  return <group position={position}>
    {asset&&<CostumedCharacter asset={asset} height={1.7} outfit={{color:'#247fba',coat:true}} displayName={name} playing clip="Idle"/>}
    <Html position={[0,2.1,0]} center distanceFactor={12} zIndexRange={[1,0]}><button className="cyber-world-label" onClick={()=>onAsk(id,name)}>{name} · conversar</button></Html>
  </group>;
}
function SharedProp({object,template,selected,onSelect}) {
  return <group position={[object.position.x,object.position.y,object.position.z]} onClick={event=>{event.stopPropagation();onSelect(object.id);}}>
    <AssetProp id={template.kind} height={template.kind==='bench'?1:template.kind==='fishing-rod'?1.4:.6}/>
    {selected&&<mesh rotation={[-Math.PI/2,0,0]} position={[0,.01,0]}><ringGeometry args={[.65,.75,32]}/><meshBasicMaterial color="#6cf0e5" transparent opacity={.8}/></mesh>}
    <Html position={[0,template.kind==='bench'?1.5:2,0]} center distanceFactor={10} zIndexRange={[1,0]}><button className="cyber-world-label" onClick={()=>onSelect(object.id)}>{template.name}{object.kind==='copy'?' · cópia':''}</button></Html>
  </group>;
}
function RemoteActor({player,actorId,world}) {
  const asset=playableCharacters.find(a=>a.id===player.characterId)??preferredCharacter,held=carriedObject(world,actorId);
  const template=interactionRooms.cyber.templates.find(t=>t.id===held?.templateId);
  const group=useRef(null),{scene}=useThree(),surfaces=useRef([]),lastScan=useRef(-Infinity),ray=useMemo(()=>new Raycaster(),[]);
  useFrame(({clock})=>{
    if(!group.current||!player.position)return;
    if(clock.elapsedTime-lastScan.current>1.5){surfaces.current=collectGroundSurfaces(scene);lastScan.current=clock.elapsedTime;}
    const jump=player.jumpHeight??0,base={...player.position,y:player.position.y-jump};
    const y=!player.sitting?sampleGroundHeight(ray,surfaces.current,base,{radius:.32})+.01+jump:player.position.y;
    group.current.position.set(player.position.x,y,player.position.z);
  });
  if(!asset||!player.position)return null;
  return <group ref={group} userData={{actor:true}} position={[player.position.x,player.position.y,player.position.z]} rotation={[0,player.heading??0,0]}>
    <CostumedCharacter asset={asset} height={1.7} outfit={player.outfit} displayName={player.displayName??'Jogador'} playing clip={player.animation??'Idle'} holding={Boolean(held)} sitting={Boolean(player.sitting)} riding={player.mode==='mototaxi'}/>
    {template&&<AssetProp id={template.kind} height={template.kind==='fishing-rod'?1.4:.45} position={[0,1,.4]}/>}
    <Html position={[0,2.1,0]} center zIndexRange={[1,0]}><span className="cyber-remote-label">{player.displayName??'Outro jogador'}</span></Html>
  </group>;
}
function AuthorizedHomeModel({url}) {
  const {scene}=useGLTF(url);
  const model=useMemo(()=>{
    const copy=scene.clone(true),door=copy.getObjectByName('PRIVATE_Door');
    if(door)door.position.x+=3.5;
    return copy;
  },[scene]);
  return <primitive object={model} dispose={null}/>;
}
function PrivateHome({url,onClose}) {
  return <section className="cyber-private" aria-label="Casa privada autorizada">
    <div><h3>Casa do criador · acesso autorizado</h3><button onClick={onClose}>Sair da casa</button></div>
    <CityBoundary><Canvas camera={{position:[9,7,12],fov:45}} dpr={[1,1.5]}><color attach="background" args={['#111e30']}/><ambientLight intensity={2}/><directionalLight position={[8,12,8]} intensity={3}/><Suspense fallback={<Html center zIndexRange={[1,0]}>Carregando casa autorizada…</Html>}><Bounds fit clip observe margin={1.2}><AuthorizedHomeModel url={url}/></Bounds></Suspense><OrbitControls makeDefault/></Canvas></CityBoundary>
    <p>O acesso foi validado para esta sessão. Sua senha não é salva neste navegador.</p>
  </section>;
}

export default function CyberCity() {
  const shared=useSharedObjects('cyber');
  const {publishPosition}=shared;
  const [snapshot,setSnapshot]=useState(()=>{try{return restoreCyberState(window.localStorage);}catch{return restoreCyberState({getItem:()=>null});}});
  const simulation=useRef(snapshot),input=useRef({}),controls=useRef(null),tractorRef=useRef({...initialTractor}),keyboardActions=useRef({}),gameSurface=useRef(null),directionKeys=useRef(new Set());
  const classroomRuntime=useRef(createClassroomRuntime());
  const [character,setCharacter]=useState(initialCharacter);
  const [playerName,setPlayerName]=useState(()=>readPlayerName(globalThis.sessionStorage)),[nameDraft,setNameDraft]=useState(()=>readPlayerName(globalThis.sessionStorage));
  const [tab,setTab]=useState('actions'),[phoneOpen,setPhoneOpen]=useState(false),[ready,setReady]=useState(false),[spaceView,setSpaceView]=useState(false),[notice,setNotice]=useState('Clique em Jogar agora para ativar o teclado. WASD ou setas para caminhar.');
  const [gameActive,setGameActive]=useState(false);
  const [selectedObjectId,setSelectedObjectId]=useState(null),[objectBusy,setObjectBusy]=useState(false),[placement,setPlacement]=useState(null);
  const [driveId,setDriveId]=useState('mototaxi');
  const [garageCarId,setGarageCarId]=useState('car');
  const [parkingDestination,setParkingDestination]=useState(parkingPlaces[0].id);
  const audio=useGameAudio();
  const [selectedMotoId,setSelectedMotoId]=useState(null);
  const [selectedCarId,setSelectedCarId]=useState(null);
  const [selectedBusId,setSelectedBusId]=useState(null);
  const [plotId,setPlotId]=useState('plot-1'),[destination,setDestination]=useState('hospital'),[npc,setNpc]=useState({id:'jarvis',name:'JARVIS · consulta de fontes'});
  const [question,setQuestion]=useState('Como estudar anatomia?'),[answer,setAnswer]=useState(null),[asking,setAsking]=useState(false);
  const [password,setPassword]=useState(''),[homeBusy,setHomeBusy]=useState(false),[privateUrl,setPrivateUrl]=useState(null);
  const homeUrlRef=useRef(null),mounted=useRef(true);
  const [points]=useState(()=>{try{return rewardBalance(readProgress(localStorage,locationIds));}catch{return 0;}});
  const serverClock=useServerClock(manifest.clock);
  const clockConfig=serverClock.getClockConfig();
  const clock=sampleWorldClock(snapshot.elapsed,clockConfig);
  const bus=sampleLiveBus(snapshot,'bus'),brt=sampleLiveBus(snapshot,'bus-brt'),train=sampleTransit(TRANSIT_ROUTES.train,snapshot.elapsed);
  const onReady=useCallback(()=>setReady(true),[]);
  const farm=near(snapshot.position,[0,0,100],25),beach=near(snapshot.position,[100,0,0],20),elevatorNear=near(snapshot.position,[ELEVATOR_POSITION.x,0,ELEVATOR_POSITION.z],9);
  const closestFlower=FLOWER_BASES.reduce((best,flower)=>Math.hypot(snapshot.position.x-flower.position.x,snapshot.position.z-flower.position.z)<Math.hypot(snapshot.position.x-best.position.x,snapshot.position.z-best.position.z)?flower:best,FLOWER_BASES[0]);
  const closestBench=benches.reduce((best,bench)=>Math.hypot(snapshot.position.x-bench.position.x,snapshot.position.z-bench.position.z)<Math.hypot(snapshot.position.x-best.position.x,snapshot.position.z-best.position.z)?bench:best,benches[0]);
  const planted=snapshot.plots[plotId],growth=planted?Math.min(100,Math.floor((snapshot.elapsed-planted.plantedAt)/20*100)):0;
  const selectedObject=shared.state.objects.find(object=>object.id===selectedObjectId),held=carriedObject(shared.state,shared.actorId);
  const selectedTemplate=interactionRooms.cyber.templates.find(template=>template.id===selectedObject?.templateId);
  const objectOwned=selectedObject&&(selectedObject.kind==='base'||selectedObject.ownerId===shared.actorId);
  const objectNear=selectedObject&&(selectedObject.carriedBy===shared.actorId||selectedObject.position&&Math.hypot(snapshot.position.x-selectedObject.position.x,snapshot.position.z-selectedObject.position.z)<=2.25&&Math.abs(snapshot.position.y-(selectedObject.position.y??0))<=1.6);
  const others=Object.entries(shared.state.players).filter(([id,player])=>id!==shared.actorId&&player.online);
  const closestCar=nearestInteractiveCar(snapshot.position,snapshot.personalVehicles.car);
  const selectedCar=selectedCarId==='personal-car'&&snapshot.personalVehicles.car?{...resolveCarSource(snapshot.personalVehicles.car.sourceId??'car'),id:'personal-car',position:snapshot.personalVehicles.car}:resolveCarSource(selectedCarId);
  const contextCar=snapshot.mode==='car'?{...resolveCarSource(snapshot.personalVehicles.car?.sourceId??'car'),id:'personal-car',position:snapshot.personalVehicles.car}:selectedCar??closestCar;
  const closestMoto=nearestMotorcycle(snapshot.position,snapshot.personalVehicles.mototaxi);
  const contextMoto=snapshot.mode==='mototaxi'?nearestMotorcycle(snapshot.position,snapshot.personalVehicles.mototaxi):selectedMotoId==='personal-moto'?nearestMotorcycle(snapshot.position,snapshot.personalVehicles.mototaxi):resolveMotorcycle(selectedMotoId)??closestMoto;
  const showMotoContext=Boolean(contextMoto&&(snapshot.mode==='mototaxi'||snapshot.mode==='foot'&&(selectedMotoId||!selectedCarId&&(!contextCar||Math.hypot(snapshot.position.x-contextMoto.position.x,snapshot.position.z-contextMoto.position.z)<Math.hypot(snapshot.position.x-contextCar.position.x,snapshot.position.z-contextCar.position.z)))));
  const closestBus=nearestBus(snapshot);
  const contextBus=BUS_IDS.includes(snapshot.mode)?sampleLiveBus(snapshot,snapshot.mode):selectedBusId?sampleLiveBus(snapshot,selectedBusId):closestBus;
  const busNearby=contextBus&&Math.hypot(snapshot.position.x-busDoorPosition(contextBus).x,snapshot.position.z-busDoorPosition(contextBus).z)<=7;
  const showBusContext=Boolean(contextBus&&(BUS_IDS.includes(snapshot.mode)||snapshot.mode==='foot'&&(selectedBusId||!selectedCarId&&!selectedMotoId)));

  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(homeUrlRef.current)URL.revokeObjectURL(homeUrlRef.current);};},[]);
  useEffect(()=>{try{saveCyberState(localStorage,{inventory:snapshot.inventory,outfit:snapshot.outfit,garage:snapshot.garage});}catch{/* local demo works without storage */}},[snapshot.inventory,snapshot.outfit,snapshot.garage]);
  useEffect(()=>{if(shared.status==='connected')publishPosition({...snapshot.position,y:snapshot.position.y+(snapshot.jumpHeight??0)},{heading:snapshot.heading,animation:snapshot.jump?'Idle':snapshot.action,characterId:character.id,displayName:playerName,outfit:snapshot.outfit,sitting:snapshot.sitting,mode:snapshot.mode,jumpHeight:snapshot.jumpHeight??0});},[publishPosition,snapshot.position,snapshot.jump,snapshot.jumpHeight,snapshot.heading,snapshot.action,snapshot.outfit,snapshot.sitting,snapshot.mode,character.id,playerName,shared.status]);
  useEffect(()=>{
    const heldKeys=directionKeys.current;
    const key=(event,down)=>{
      if(down&&(document.activeElement!==gameSurface.current||textEntryTarget(event.target)||document.querySelector('dialog[open]')))return;
      if(down&&['f','q','e'].includes(event.key.toLowerCase())){event.preventDefault();if(!event.repeat){if(event.key.toLowerCase()==='f')keyboardActions.current.vehicle?.();else keyboardActions.current.item?.(event.key.toLowerCase()==='q'?-1:1);}return;}
      if(event.code==='Space'){if(event.target.tagName==='BUTTON')return;event.preventDefault();if(down&&!event.repeat)input.current.jumpPressed=true;return;}
      const change=setDirectionKey(heldKeys,event.key,down);
      if(change){event.preventDefault();if(down)delete input.current.target;input.current[change.direction]=change.pressed;}
    };
    const down=event=>key(event,true),up=event=>key(event,false),blur=()=>{heldKeys.clear();input.current={};};
    window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',blur);
    return()=>{window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',blur);};
  },[]);
  function focusGame(){
    gameSurface.current?.focus({preventScroll:true});
    void audio.unlock();
  }
  function closePhone(){input.current={};setPhoneOpen(false);focusGame();}
  function openAssetCatalog(category='Todos'){
    input.current={};setPhoneOpen(false);
    window.dispatchEvent(new CustomEvent('prep:open-assets',{detail:{category}}));
  }
  function saveUniformName(event){
    event.preventDefault();
    const name=savePlayerName(globalThis.sessionStorage,nameDraft);
    setPlayerName(name);setNameDraft(name);setNotice(`Nome no jaleco: ${name}.`);
  }
  function resumeGame(){
    input.current={};setPhoneOpen(false);
    if(spaceView)togglePlanetarium();
    focusGame();
    setNotice('Controles ativos: WASD ou setas para caminhar, Espaço para pular e F para entrar ou sair de veículos.');
  }
  function commit(action) {
    const parkingZones=parkingPlaces.map(p=>({id:p.id,label:p.label,position:[p.position[0]+3,0,p.position[2]+2]}));
    const drives=Object.entries(DRIVE_VEHICLES).map(([id,vehicle])=>{const point=simulation.current.personalVehicles[id]??vehicle.position;return{id:`drive-${id}`,label:vehicle.label,position:[point.x+3,0,point.z+2]};});
    const actualBenches=[...benches,...shared.state.objects.filter(object=>object.position&&interactionRooms.cyber.templates.find(t=>t.id===object.templateId)?.kind==='bench').map(object=>({id:object.id,position:object.position}))];
    const obstacles=[...cityColliders(manifest.colliders??[],buildings,shared.state.doors),...newDeliveryColliders,...classroomColliders(classroomRuntime),...realisticWorld.environmentReplacements.filter(r=>r.position[1]<1).map(r=>footprintCollider(r,suppliedCatalog)).filter(Boolean)];
    if(BUS_IDS.includes(simulation.current.mode)||action.type==='BOARD'&&BUS_IDS.includes(action.vehicle)){
      obstacles.push(...BUS_IDS.map(id=>busFootprint(sampleLiveBus(simulation.current,id))));
      for(const [id,definition]of Object.entries(DRIVE_VEHICLES)){
        const p=simulation.current.personalVehicles[id]??definition.position;
        obstacles.push({id,x:p.x,z:p.z,w:id==='mototaxi'?1:2.8,d:id==='truck'?7:4});
      }
    }
    const result=applyCyberAction(simulation.current,action,{zones:[...zones,...newDeliveryZones,...classroomZones,...transportDestinations,elevatorDestination,...drives,...parkingZones],benches:actualBenches,tractor:tractorRef.current,parking:parkingPlaces,obstacles,carrying:Boolean(held)});
    if(result.ok){
      const from=simulation.current.position,to=result.state.position;
      if(!spaceView)controls.current?.object.position.add(new Vector3(to.x-from.x,to.y-from.y,to.z-from.z));
      simulation.current=result.state;setSnapshot(result.state);
      audio.play(action.type,{...result.state.carControls,engineOn:BUS_IDS.includes(result.state.mode)?sampleLiveBus(result.state,result.state.mode).engineOn:result.state.mode==='mototaxi'?result.state.motorcycleControls?.engineOn:result.state.carControls?.engineOn});
      if(!phoneOpen)focusGame();
    }
    if(result.message)setNotice(result.message);
    return result;
  }
  async function changeCharacter(id) {
    const next=playableCharacters.find(a=>a.id===id);if(!next)return;
    if(next.id===character.id)return;
    let current=simulation.current;
    if(current.mode!=='foot'||current.elevator){setNotice('Saia do veículo ou aguarde o elevador para trocar de personagem.');return;}
    if(held){
      if(shared.status!=='connected'){setNotice('Reconecte a sala para devolver o objeto antes de trocar de personagem.');return;}
      const returned=await shared.dispatch({type:'RETURN',objectId:held.id,expectedRevision:held.revision});
      if(!returned.ok){setNotice(returned.message??'Devolva o objeto antes de trocar de personagem.');return;}
    }
    current=simulation.current;
    if(current.mode!=='foot'||current.elevator){setNotice('Aguarde até estar a pé para trocar de personagem.');return;}
    input.current={};
    const position={...current.position,y:current.position.y<-.1?-6:0,z:current.position.z+(current.sitting?1:0)};
    const reset={...current,position,sitting:false,action:'Idle',actionUntil:null,fishing:null};
    if(!spaceView)controls.current?.object.position.add(new Vector3(0,position.y-current.position.y,position.z-current.position.z));
    simulation.current=reset;setSnapshot(reset);
    setCharacter(next);try{localStorage.setItem('prep.character.v1',id);window.dispatchEvent(new CustomEvent('prep:character',{detail:id}));}catch{/* session remains active */}
  }
  function converse(id,name) {setNpc({id,name});setTab('jarvis');setPhoneOpen(true);input.current={};}
  function selectCar(id){setSelectedCarId(id);setSelectedMotoId(null);setSelectedBusId(null);setPhoneOpen(false);input.current={};setNotice('Carro selecionado. Aproxime-se e escolha Entrar no carro.');}
  function selectBus(id){setSelectedBusId(id);setSelectedCarId(null);setSelectedMotoId(null);setPhoneOpen(false);input.current={};setNotice('Ônibus selecionado. Aproxime-se da porta na parada para embarcar.');}
  function boardBus(id){input.current={};setPhoneOpen(false);const result=commit({type:'BOARD',vehicle:id});if(result.ok){setSelectedBusId(id);focusGame();}}
  function operateBus(type){input.current={};commit({type});}
  function enterCar(id){input.current={};setPhoneOpen(false);const result=commit({type:'CAR_ENTER',carId:id});if(result.ok){setSelectedCarId('personal-car');focusGame();}}
  function toggleVehicle(){
    if(spaceView||privateUrl)return;
    const current=simulation.current;
    if(BUS_IDS.includes(current.mode)){operateBus('EXIT');return;}
    if(current.mode==='car'){input.current={};commit({type:'CAR_EXIT'});return;}
    if(current.mode==='mototaxi'){input.current={};commit({type:'MOTO_EXIT'});return;}
    if(DRIVE_VEHICLES[current.mode]){input.current={};commit({type:'EXIT'});return;}
    const car=nearestInteractiveCar(current.position,current.personalVehicles.car);
    const moto=nearestMotorcycle(current.position,current.personalVehicles.mototaxi);
    const nearbyBus=nearestBus(current);
    if(nearbyBus&&(selectedBusId===nearbyBus.id||nearbyBus.distance<=Math.min(car?.distance??Infinity,moto?.distance??Infinity)))boardBus(nearbyBus.id);
    else if(moto&&(!car||moto.distance<car.distance))enterMoto(moto.id);else if(car)enterCar(car.id);else setNotice('Aproxime-se de um veículo para entrar com F.');
  }
  function selectMoto(id){setSelectedMotoId(id);setSelectedCarId(null);setSelectedBusId(null);setPhoneOpen(false);input.current={};setNotice('Moto selecionada. Aproxime-se e escolha Pilotar moto ou pressione F.');}
  function enterMoto(id){input.current={};setPhoneOpen(false);const result=commit({type:'MOTO_ENTER',motoId:id});if(result.ok){setSelectedMotoId('personal-moto');setSelectedCarId(null);focusGame();}}
  function summonVehicle(){
    input.current={};
    const result=commit({type:'SUMMON_VEHICLE',vehicle:driveId,sourceId:driveId==='car'?garageCarId:driveId});
    if(result.ok){setSelectedCarId(driveId==='car'?'personal-car':null);setSelectedMotoId(driveId==='mototaxi'?'personal-moto':null);}
  }
  function enterPersonalVehicle(){
    if(snapshot.personalVehicles.car)enterCar('personal-car');
    else if(snapshot.personalVehicles.mototaxi)enterMoto('personal-moto');
    else{const id=Object.keys(snapshot.personalVehicles)[0];if(id)commit({type:'DRIVE',vehicle:id});}
  }
  function alternateItem(direction){
    if(spaceView||privateUrl)return;
    const object=cycleItem(shared.state.objects,selectedObjectId,direction,shared.actorId);
    if(!object){setNotice('Não há itens disponíveis para selecionar.');return;}
    setSelectedObjectId(object.id);setPlacement(null);
    audio.play('MENU');
    setNotice(`Item selecionado: ${interactionRooms.cyber.templates.find(t=>t.id===object.templateId)?.name??'Objeto'}. Abra Objetos para usar ou pegar.`);
  }
  useEffect(()=>{keyboardActions.current={vehicle:toggleVehicle,item:alternateItem};});
  function selectObject(id){setSelectedObjectId(id);setTab('objects');setPhoneOpen(true);setPlacement(null);input.current={};}
  async function objectAction(type,object=selectedObject,position){
    if(!object||objectBusy)return;
    setObjectBusy(true);
    try{
      const result=await shared.dispatch({type,objectId:object.id,expectedRevision:object.revision,...(position?{position}:{})});
      setNotice(result.message);
      if(result.ok){setPlacement(null);if(result.createdId)setSelectedObjectId(result.createdId);if(type==='RETURN')setSelectedObjectId(`base:${object.templateId}`);if(type==='USE')commit(interactionRooms.cyber.templates.find(t=>t.id===object.templateId)?.kind==='bench'?{type:'SIT',benchId:object.id}:{type:'INTERACT'});}
    }finally{setObjectBusy(false);}
  }
  async function ask(event) {
    event.preventDefault();setAsking(true);setAnswer(null);
    const result=await askJarvis(question,npc.id);
    if(mounted.current){setAnswer(result);setAsking(false);}
  }
  async function openHome(event) {
    event.preventDefault();setHomeBusy(true);const secret=password;setPassword('');
    const unlocked=await unlockHome(secret);
    if(!unlocked.ok){if(mounted.current){setNotice(unlocked.message ?? 'Acesso não autorizado.');setHomeBusy(false);}return;}
    const layout=await getPrivateHomeLayout();
    if(!layout.ok){if(mounted.current){setNotice(layout.message ?? 'Casa não autorizada.');setHomeBusy(false);}return;}
    const result=await getPrivateHomeAsset();
    if(!mounted.current){if(result.url)URL.revokeObjectURL(result.url);return;}
    if(result.ok&&result.url){if(homeUrlRef.current)URL.revokeObjectURL(homeUrlRef.current);homeUrlRef.current=result.url;input.current={};setPrivateUrl(result.url);setNotice('Modelo privado recebido após autorização.');}
    else setNotice(result.message ?? 'O modelo privado está indisponível.');
    setHomeBusy(false);
  }
  function closeHome(){if(homeUrlRef.current)URL.revokeObjectURL(homeUrlRef.current);homeUrlRef.current=null;setPrivateUrl(null);focusGame();}
  function visitEntrance(building){
    const point=doorApproach(building);
    if(simulation.current.mode!=='foot'){setNotice('Saia do veículo antes de visitar a entrada.');return;}
    input.current={};
    const current=simulation.current;
    const next={...current,position:point,heading:Math.PI,sitting:false,action:'Idle',fishing:null,elevator:null};
    simulation.current=next;setSnapshot(next);setSpaceView(false);
    if(controls.current){controls.current.object.position.set(point.x+2.2,2.5,point.z+4);controls.current.target.set(point.x,1.5,point.z-4);controls.current.update();}
    setNotice(`Entrada de ${building.label}. Abra a porta e use os controles para entrar.`);
  }
  function enterBuilding(building){
    if(!shared.state.doors?.[building.id]?.open){setNotice('Abra a porta antes de entrar.');return;}
    const entry=doorPosition(building),p=simulation.current.position;
    if(simulation.current.mode!=='foot'||Math.hypot(p.x-entry[0],p.z-entry[2])>5){setNotice('Visite a entrada primeiro.');return;}
    setPhoneOpen(false);focusGame();input.current={target:{x:entry[0],z:entry[2]-3.5}};setNotice('Entrando pelo vão aberto. Use os controles para explorar o interior.');
  }
  async function toggleDoor(building){
    const p=simulation.current.position,entry=doorPosition(building);
    if(simulation.current.mode!=='foot'||Math.hypot(p.x-entry[0],p.z-entry[2])>5){setNotice('Aproxime-se da porta a pé para abrir ou fechar.');return;}
    await shared.publishPosition(p,{heading:simulation.current.heading,animation:simulation.current.action,characterId:character.id});
    const result=await shared.door(building.id,!shared.state.doors?.[building.id]?.open);
    setNotice(result?.message??'O serviço compartilhado precisa estar conectado.');
  }
  function togglePlanetarium(){
    const current=simulation.current.position,sun=sampleWorldClock(simulation.current.elapsed,clockConfig).sunCenter;
    input.current={};
    if(controls.current){
      controls.current.object.position.set(...(spaceView?[current.x+3.5,current.y+2.6,current.z+5.5]:[sun[0]+60,sun[1]+50,sun[2]+80]));
      controls.current.target.set(...(spaceView?[current.x,current.y+1,current.z]:sun));
    }
    setSpaceView(value=>!value);
    setNotice(spaceView?'De volta à cidade.':'Planetário didático: tamanhos, distâncias e períodos foram acelerados para visualização.');
  }
  function visitClassroom(){
    if(!commit({type:'TELEPORT',zoneId:'futuristic-classroom'}).ok)return;
    openClassroomDoor(classroomRuntime);
    setPhoneOpen(false);setSelectedCarId(null);setSelectedMotoId(null);setSpaceView(false);
    const point=simulation.current.position;
    if(controls.current){
      controls.current.object.position.set(point.x,point.y+2.1,point.z-4.8);
      controls.current.target.set(point.x,point.y+1,point.z);
      controls.current.update();
    }
    focusGame();
  }
  function viewCharacter(){
    const current=simulation.current.position;
    input.current={};setSpaceView(false);setPhoneOpen(false);
    if(controls.current){
      controls.current.object.position.set(current.x+2.4,current.y+1.75,current.z+3.6);
      controls.current.target.set(current.x,current.y+.95,current.z);
      controls.current.update();
    }
    focusGame();
    setNotice('Personagem em destaque. Arraste para girar a câmera; abra o smartphone para escolher ações.');
  }
  const tabs=[['actions','Ações'],['buildings','Portas'],['routes','Rotas'],['objects','Objetos'],['inventory','Bolsa'],['clothes','Loja'],['jarvis','JARVIS'],['home','Criador']];
  if(!character)return <p>Carregando personagens do acervo.</p>;

  return <section ref={gameSurface} className="cyber-city" tabIndex={0} onFocus={event=>setGameActive(event.target===event.currentTarget)} onBlur={()=>{setGameActive(false);directionKeys.current.clear();input.current={};}} onPointerDown={event=>{if(event.target.tagName==='CANVAS')focusGame();}} aria-label="Arapiraca PREP · cidade futurista em desenvolvimento" data-game-active={gameActive&&!spaceView&&!privateUrl} data-cyber-ready={ready} data-cyber-character={character.id} data-cyber-view={spaceView?'planetarium':'city'} data-cyber-mode={snapshot.mode} data-cyber-x={snapshot.position.x.toFixed(2)} data-cyber-y={snapshot.position.y.toFixed(2)} data-cyber-z={snapshot.position.z.toFixed(2)} data-cyber-jump={Number(snapshot.jumpHeight??0).toFixed(3)} data-cyber-jumps={snapshot.jumpCount??0} data-car-steering={snapshot.personalVehicles.car?.steeringAngle??0} data-car-wheel-angle={snapshot.personalVehicles.car?.wheelAngle??0} data-moto-steering={snapshot.personalVehicles.mototaxi?.steeringAngle??0} data-moto-wheel-angle={snapshot.personalVehicles.mototaxi?.wheelAngle??0} data-personal-vehicle-count={Object.keys(snapshot.personalVehicles).length} data-selected-item={selectedObjectId??''} data-cyber-clock={clock.text} data-cyber-flowers={snapshot.inventory.flowers}>
    <CityBoundary><Canvas shadows={shadowSettings} dpr={1} camera={{position:[CITY_START.x+3.5,2.6,CITY_START.z+5.5],fov:50,far:450}}>
      <color attach="background" args={[spaceView?'#010207':clock.night?'#080f1c':'#b5d3e1']}/>{!spaceView&&<fog attach="fog" args={[clock.night?'#080f1c':'#c3d9df',110,330]}/>}
      <ambientLight intensity={clock.night?.08:.1}/><hemisphereLight args={[clock.night?'#6380aa':'#dbeeff',clock.night?'#262a2c':'#64614f',clock.night?.22:.65]}/>
      <SunLight simulation={simulation} night={clock.night}/>
      <Suspense fallback={<Html center zIndexRange={[1,0]}><span className="cyber-loading">Abrindo Arapiraca PREP…</span></Html>}>
        <Environment onReady={onReady} simulation={simulation}/>
        <DetailedWorld onSelectCar={selectCar} onSelectMoto={selectMoto} personalVehicles={snapshot.personalVehicles}/>
        <NewDeliveryWorld onInspect={({asset,placement})=>{setNotice(asset.description??placement.label);if(["terminal","bus-stop","parked-vehicle"].includes(placement.role)){setTab("routes");setPhoneOpen(true);}}}/>
        <FuturisticClassroom simulation={simulation} runtime={classroomRuntime} onDoorState={()=>audio.play('DOOR')} onInspect={()=>{setNpc({id:'jarvis',name:'Professor JARVIS · Anatomia'});setQuestion('Como estudar ossos e camadas do corpo humano?');setTab('jarvis');setPhoneOpen(true);}}/>
        <BuildingDoors doors={shared.state.doors} simulation={simulation} onToggle={toggleDoor}/>
        <Actor asset={character} snapshot={snapshot} simulation={simulation} tractorRef={tractorRef} held={held} displayName={playerName}/>
        <Vehicle id="bus" simulation={simulation} onAsk={converse} onSelect={selectBus}/><Vehicle id="bus-brt" simulation={simulation} onAsk={converse} onSelect={selectBus}/><Vehicle id="train" simulation={simulation} onAsk={converse}/>
        {Object.keys(DRIVE_VEHICLES).filter(id=>!snapshot.personalVehicles[id]).map(id=><Vehicle key={`base-${id}`} id={id} simulation={simulation} onSelect={id==='mototaxi'?selectMoto:selectCar}/>)}
        {Object.keys(snapshot.personalVehicles).map(id=><Vehicle key={`personal-${id}`} id={id} personal simulation={simulation} onSelect={id==='mototaxi'?selectMoto:selectCar}/>)}
        {benches.filter(bench=>bench.id!=='bench-west').map(bench=><AssetProp key={bench.id} id="bench" height={1} position={[bench.position.x,0,bench.position.z]} onClick={()=>commit({type:'SIT',benchId:bench.id})}/>)}
        {shared.state.objects.filter(object=>object.position).map(object=><SharedProp key={object.id} object={object} template={interactionRooms.cyber.templates.find(t=>t.id===object.templateId)} selected={object.id===selectedObjectId} onSelect={selectObject}/>)}
        {others.map(([id,player])=><RemoteActor key={id} player={player} actorId={id} world={shared.state}/>)}
        {FLOWER_BASES.map(flower=><AssetProp key={flower.id} id="flower" height={.6} position={[flower.position.x,0,flower.position.z]} onClick={event=>{event.stopPropagation();commit({type:'FLOWER',flowerId:flower.id});}}/>)}
        {FARM_PLOTS.map(plot=><GrowthPlot key={plot.id} plot={plot} planted={snapshot.plots[plot.id]} elapsed={snapshot.elapsed} onSelect={id=>{setPlotId(id);setTab('actions');setPhoneOpen(true);}}/>)}
        <AssetProp id="elevator" height={3.2} position={[ELEVATOR_POSITION.x,snapshot.elevator?snapshot.position.y:elevatorNear?snapshot.position.y:0,ELEVATOR_POSITION.z]}/>
        <NPC id="nurse" position={[43,0,-20]} name="Tutora hospitalar PREP" onAsk={converse}/><NPC id="guide" position={[-7,0,2]} name="Guia de Arapiraca PREP" onAsk={converse}/>
        <AssetProp id="fish-blue" height={.4} position={[108,.5,-6]}/><AssetProp id="fish-yellow" height={.35} position={[111,.45,4]}/><AssetProp id="fish-red" height={.35} position={[105,.45,8]}/><AssetProp id="shark" height={.7} position={[115,.45,16]}/>
      </Suspense>
      <SolarSky simulation={simulation} clockConfig={clockConfig} planetarium={spaceView}/>
      <Html position={[0,7,-5]} center distanceFactor={16} zIndexRange={[1,0]}><div className="cyber-billboard"><strong>ARAPIRACA · PREP</strong><span>{clock.text} · {clock.phase}</span><small>CHRONOVITAE · conhecimento em movimento</small></div></Html>
      {snapshot.fishing&&<Line points={[[snapshot.position.x+.4,1.7,snapshot.position.z+.3],[107,.2,0]]} color="#b9dce7" lineWidth={1}/>}
      {placement&&<mesh position={[0,snapshot.position.y+.015,0]} rotation={[-Math.PI/2,0,0]} onClick={event=>{event.stopPropagation();objectAction(placement,placement==='DROP'?held:selectedObject,{x:event.point.x,y:snapshot.position.y,z:event.point.z});}}><planeGeometry args={[236,236]}/><meshBasicMaterial color="#6ce5cc" transparent opacity={.08} depthWrite={false}/></mesh>}
      <RuntimeLoop simulationRef={simulation} input={input} controls={controls} onSnapshot={setSnapshot} onNotice={setNotice} tractorRef={tractorRef} spaceView={spaceView||Boolean(privateUrl)} doors={shared.state.doors} worldObjects={shared.state.objects} classroomRuntime={classroomRuntime}/>
      <GameAudioLoop audioRef={audio.audioRef} simulation={simulation} doors={shared.state.doors} onStatus={audio.syncStatus}/>
      <OrbitControls ref={controls} makeDefault target={[CITY_START.x,1,CITY_START.z]} minDistance={3} maxDistance={spaceView?120:65} maxPolarAngle={Math.PI/2.1}/>
    </Canvas></CityBoundary>
    <div className="cyber-heading"><span>ARAPIRACA · ALAGOAS · VISÃO CONCEITUAL</span><h2>Seu futuro é agora.</h2><p>WASD ou setas · Shift: correr · Espaço: pular · F: entrar/sair · Q/E: itens</p></div>
    <div className="cyber-audio" data-audio-unlocked={audio.status.unlocked}><button onClick={()=>{void audio.unlock();audio.toggleMute();}} aria-pressed={audio.muted}>{audio.muted?'Ativar som':'Silenciar som'}</button><label>Volume<input aria-label="Volume do jogo" type="range" min="0" max="1" step=".05" value={audio.volume} onChange={event=>audio.setVolume(event.target.value)}/></label></div>
    <div className="cyber-time"><strong>{clock.text}</strong><span>{clock.phase}</span><small>{clock.dateText} · horário de Brasília</small></div>
    <button className="cyber-planetarium" aria-pressed={spaceView} onClick={togglePlanetarium}>{spaceView?'Voltar à cidade':'Ver planetário'}</button>
    <div className="cyber-play-control"><button disabled={!ready||Boolean(privateUrl)} onClick={resumeGame}>{ready?'Jogar agora':'Carregando cidade…'}</button><small>{gameActive&&!spaceView&&!privateUrl?'Teclado ativo':'Clique para ativar o teclado'}</small></div>
    <button className="cyber-character-view" onClick={viewCharacter}>Ver personagem</button>
    <button className="cyber-phone-toggle" aria-expanded={phoneOpen} onClick={()=>{if(phoneOpen)closePhone();else{input.current={};setPhoneOpen(true);}}}>{phoneOpen?'Fechar smartphone':'Abrir smartphone'}</button>
    {showBusContext&&!spaceView&&!privateUrl&&<BusControls bus={contextBus} occupied={BUS_IDS.includes(snapshot.mode)} role={snapshot.busControls?.role} nearby={busNearby} onBoard={()=>boardBus(contextBus.id)} onAction={operateBus} onClear={()=>setSelectedBusId(null)}/>}
    {contextCar&&!showBusContext&&!showMotoContext&&snapshot.mode!=='mototaxi'&&!spaceView&&!privateUrl&&<aside className="cyber-car-context" aria-label="Interação com o carro" data-car-id={contextCar.id}>
      <div><strong>{contextCar.label}</strong>{selectedCarId&&snapshot.mode==='foot'&&<button aria-label="Desmarcar carro" onClick={()=>setSelectedCarId(null)}>×</button>}</div>
      {snapshot.mode==='foot'?<><button disabled={!canEnterCar(snapshot,contextCar)||Boolean(snapshot.carEntry)} onClick={()=>enterCar(contextCar.id)}>{snapshot.carEntry?'Abrindo a porta…':'Entrar no carro · F'}</button><small>{canEnterCar(snapshot,contextCar)?'F também abre a porta e inicia a entrada.':'Aproxime-se do carro para entrar.'}</small></>:snapshot.mode==='car'?<><p>Motor {snapshot.carControls?.engineOn?'ligado':'desligado'} · porta {snapshot.carControls?.doorOpen?'aberta':'fechada'}</p><div className="cyber-action-grid"><button disabled={snapshot.carControls?.doorOpen} onClick={()=>commit({type:'CAR_ENGINE'})}>{snapshot.carControls?.engineOn?'Desligar':'Ligar'} motor</button><button disabled={snapshot.carControls?.engineOn} onClick={()=>commit({type:'CAR_DOOR'})}>{snapshot.carControls?.doorOpen?'Fechar':'Abrir'} porta</button><button onClick={()=>commit({type:'CAR_WINDOWS'})}>{snapshot.carControls?.windowsOpen?'Fechar':'Baixar'} vidros laterais</button><button disabled={Boolean(snapshot.carExit)} onClick={()=>commit({type:'CAR_EXIT'})}>{snapshot.carExit?'Abrindo a porta…':'Sair do carro · F'}</button></div></>:<small>Saia do veículo atual para entrar neste carro.</small>}
    </aside>}
    {showMotoContext&&!showBusContext&&!spaceView&&!privateUrl&&snapshot.mode!=='car'&&<aside className="cyber-car-context cyber-moto-context" aria-label="Interação com a moto" data-moto-id={contextMoto.id}>
      <div><strong>{contextMoto.label}</strong><button aria-label="Desmarcar moto" onClick={()=>setSelectedMotoId(null)}>×</button></div>
      {snapshot.mode==='mototaxi'?<><p>Motor {snapshot.motorcycleControls?.engineOn?'ligado':'desligado'}</p><div className="cyber-action-grid"><button onClick={()=>commit({type:'MOTO_ENGINE'})}>{snapshot.motorcycleControls?.engineOn?'Desligar':'Ligar'} motor da moto</button><button onClick={()=>commit({type:'MOTO_EXIT'})}>Descer da moto · F</button></div></>:<><button disabled={snapshot.mode!=='foot'||Math.hypot(snapshot.position.x-contextMoto.position.x,snapshot.position.z-contextMoto.position.z)>7} onClick={()=>enterMoto(contextMoto.id)}>Pilotar moto · F</button><small>Clique na moto ou aproxime-se. F para subir e descer; WASD ou setas para pilotar.</small></>}
    </aside>}
    {phoneOpen&&<aside className="cyber-phone" aria-label="Smartphone CHRONOVITAE">
      <header><div><small>CHRONOVITAE OS · JARVIS</small><strong>{clock.text} <span>{clock.phase}</span></strong></div><button aria-label="Fechar smartphone" onClick={closePhone}>×</button></header>
      <nav aria-label="Aplicativos do smartphone">{tabs.map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{label}</button>)}<button onClick={()=>openAssetCatalog()}>Acervo 3D</button></nav>
      <div className="cyber-phone-body">
        {tab==='actions'&&<>
          <PlayerNameForm value={nameDraft} onChange={setNameDraft} onSubmit={saveUniformName}/>
          <h3>Personagem e ações</h3><label>Personagem<select value={character.id} onChange={event=>changeCharacter(event.target.value)}>{playableCharacters.map(asset=><option key={asset.id} value={asset.id}>{asset.name}{isRealisticHuman(asset)?' · humano':' · acervo anterior'}</option>)}</select></label>{!isRealisticHuman(character)&&<p className="cyber-tip">Prévia do acervo anterior. Este modelo ainda precisa ser adaptado à nova direção realista.</p>}
          <button onClick={()=>openAssetCatalog('Personagens')}>Ver personagens no Acervo 3D</button>
          <div className="cyber-action-grid"><button onClick={()=>commit({type:'DANCE'})} disabled={!character.animations.includes('Dance')||Boolean(held)}>{snapshot.action==='Dance'?'Parar dança':'Dançar'}</button><button onClick={()=>commit({type:snapshot.sitting&&snapshot.mode==='foot'?'STAND':'SIT',benchId:closestBench.id})}>{snapshot.sitting&&snapshot.mode==='foot'?'Levantar':'Sentar no banco'}</button></div>
          <button disabled={snapshot.mode!=='foot'||snapshot.sitting||Boolean(snapshot.jump)||Boolean(snapshot.elevator)} onClick={()=>commit({type:'JUMP'})}>Pular · Espaço</button>
          <p className="cyber-tip">As poses de sentar e pilotar foram ajustadas. O caimento das roupas continua em aprimoramento.</p>
          <h4>Sala de aula futurista</h4><button onClick={visitClassroom}>Visitar sala de aula</button>
          <h4>Jardim da praça</h4><button onClick={()=>commit({type:'FLOWER',flowerId:closestFlower.id})}>Colher cópia de uma flor</button><p>O jardim base permanece. Suas cópias vão para a bolsa.</p>
          <h4>Galeria subterrânea</h4><div className="cyber-action-grid"><button onClick={()=>commit({type:'TELEPORT',zoneId:'elevator-entry'})}>Visitar elevador</button><button disabled={!elevatorNear} onClick={()=>commit({type:'ELEVATOR',floor:-1})}>Descer ao subsolo</button><button disabled={!elevatorNear} onClick={()=>commit({type:'ELEVATOR',floor:0})}>Voltar ao térreo</button></div><h4>Hospital · inspiração no HEA</h4><button onClick={()=>window.dispatchEvent(new Event('prep:open-clinical'))}>Atividade SBAR/SOAP</button>
          <h4>Fazenda · crescimento acelerado</h4><label>Canteiro<select value={plotId} onChange={event=>setPlotId(event.target.value)}>{FARM_PLOTS.map(plot=><option key={plot.id} value={plot.id}>{plot.id.replace('plot-','Canteiro ')}</option>)}</select></label><div className="cyber-action-grid"><button disabled={!farm} onClick={()=>commit({type:'PLANT',plotId})}>Plantar</button><button disabled={!farm||growth<100} onClick={()=>commit({type:'HARVEST',plotId})}>Colher</button><button disabled={!farm} onClick={()=>commit({type:'SEEDS'})}>Receber sementes</button><button disabled={!farm&&snapshot.mode!=='tractor'} onClick={()=>commit({type:snapshot.mode==='tractor'?'EXIT':'TRACTOR'})}>{snapshot.mode==='tractor'?'Sair do trator':'Dirigir trator'}</button></div>{planted&&<p>Crescimento: {growth}% · 20 s neste protótipo</p>}
          <h4>Pesca educativa virtual</h4><div className="cyber-action-grid"><button disabled={!beach||!!snapshot.fishing} onClick={()=>commit({type:'CAST'})}>Lançar linha</button><button disabled={!snapshot.fishing||snapshot.elapsed<snapshot.fishing.readyAt} onClick={()=>commit({type:'REEL'})}>Recolher linha</button></div>{snapshot.fishing&&<p>{snapshot.elapsed<snapshot.fishing.readyAt?`Aguarde ${Math.ceil(snapshot.fishing.readyAt-snapshot.elapsed)} s`:'Pronto para recolher.'}</p>}
        </>}
        {tab==='buildings'&&<><h3>Portas e estabelecimentos</h3><p>Visite a entrada, abra a porta e caminhe para dentro. A abertura é compartilhada pelos jogadores da sala.</p>{buildings.map(b=>{
          const open=shared.state.doors?.[b.id]?.open,p=doorPosition(b),nearby=Math.hypot(snapshot.position.x-p[0],snapshot.position.z-p[2])<=5;
          return <article className="cyber-route" key={b.id}><h4>{b.label}</h4><div className="cyber-action-grid"><button onClick={()=>visitEntrance(b)}>Ir à entrada · {b.label}</button><button disabled={!nearby||shared.status!=='connected'} onClick={()=>toggleDoor(b)}>{open?'Fechar':'Abrir'} porta · {b.label}</button><button disabled={!nearby||!open} onClick={()=>enterBuilding(b)}>Entrar · {b.label}</button></div><p>{open?'Aberta · passagem livre':'Fechada'} · abertura animada</p></article>;
        })}</>}
        {tab==='routes'&&<>
          <h3>Mobilidade da cidade</h3><p>Veículos percorrem rotas automáticas. Embarque e desembarque somente nas paradas.</p>
          <div className="cyber-action-grid"><button onClick={()=>openAssetCatalog('Veículos')}>Veículos no Acervo 3D</button><button onClick={()=>openAssetCatalog('Trens')}>Trens no Acervo 3D</button></div>
          {[[bus,'bus'],[brt,'bus-brt'],[train,'train']].map(([vehicle,id])=><article className="cyber-route" key={id}><h4>{TRANSIT_ROUTES[id].label}</h4><p>{vehicle.stopLabel} · próximo: {vehicle.nextStop}</p><small>{vehicle.control==='player'?'Dirigido por você':vehicle.stopped?`Parado por mais ${vehicle.remaining} s`:`Próxima parada em ${vehicle.remaining} s`}</small><button disabled={snapshot.mode!==id&&(!vehicle.stopped||snapshot.mode!=='foot')} onClick={()=>BUS_IDS.includes(id)?snapshot.mode===id?operateBus('EXIT'):boardBus(id):commit({type:snapshot.mode===id?'EXIT':'BOARD',vehicle:id})}>{snapshot.mode===id?'Desembarcar':'Embarcar'}</button><button disabled={snapshot.mode!=='foot'} onClick={()=>commit({type:'TELEPORT',zoneId:`${id}-boarding`})}>Ir à parada inicial</button></article>)}
          <h4>Sua garagem</h4><p>Apenas um veículo pessoal por vez. Chamar outro recolhe o anterior.</p>
          <label>Veículo<select value={driveId} onChange={event=>setDriveId(event.target.value)}>{Object.values(DRIVE_VEHICLES).map(vehicle=><option value={vehicle.id} key={vehicle.id}>{vehicle.label}</option>)}</select></label>
          {driveId==='car'&&<label>Modelo do carro<select value={garageCarId} onChange={event=>setGarageCarId(event.target.value)}>{listInteractiveCars().filter((car,index,all)=>all.findIndex(c=>c.asset.sourceId===car.asset.sourceId)===index).map(car=><option key={car.id} value={car.id}>{car.label}</option>)}</select></label>}
          <div className="cyber-action-grid"><button onClick={summonVehicle} disabled={snapshot.mode!=='foot'||Boolean(snapshot.carEntry)}>Chamar veículo</button><button onClick={enterPersonalVehicle} disabled={snapshot.mode!=='foot'||!Object.keys(snapshot.personalVehicles).length}>Entrar no veículo · F</button><button onClick={toggleVehicle} disabled={!DRIVE_VEHICLES[snapshot.mode]}>Sair do veículo · F</button><button onClick={()=>{const result=commit({type:'STORE_VEHICLE'});if(result.ok){setSelectedCarId(null);setSelectedMotoId(null);}}} disabled={!Object.keys(snapshot.personalVehicles).length}>Guardar no estacionamento</button></div>
          <p>Veículo pessoal no mapa: {Object.keys(snapshot.personalVehicles).length ? DRIVE_VEHICLES[Object.keys(snapshot.personalVehicles)[0]].label : 'nenhum'}.</p>
          {snapshot.mode==='car'&&<><div className="cyber-action-grid"><button disabled={snapshot.carControls?.engineOn} onClick={()=>commit({type:'CAR_DOOR'})}>{snapshot.carControls?.doorOpen?'Fechar':'Abrir'} porta do carro</button><button disabled={snapshot.carControls?.doorOpen} onClick={()=>commit({type:'CAR_ENGINE'})}>{snapshot.carControls?.engineOn?'Desligar':'Ligar'} motor</button><button onClick={()=>commit({type:'CAR_WINDOWS'})}>{snapshot.carControls?.windowsOpen?'Fechar':'Baixar'} vidros laterais</button></div></>}
          {snapshot.mode==='mototaxi'&&<button onClick={()=>commit({type:'MOTO_ENGINE'})}>{snapshot.motorcycleControls?.engineOn?'Desligar':'Ligar'} motor da moto</button>}
          <label>Estacionamento<select value={parkingDestination} onChange={event=>setParkingDestination(event.target.value)}>{parkingPlaces.map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select></label><button disabled={snapshot.mode!=='foot'} onClick={()=>commit({type:'TELEPORT',zoneId:parkingDestination})}>Ir ao estacionamento</button>
          <label>Carroceria do caminhão<select value={snapshot.trailer} onChange={event=>commit({type:'TRAILER',trailer:event.target.value})}><option value="flatbed">Prancha</option><option value="tanker">Tanque</option><option value="box">Baú</option></select></label>{snapshot.mode==='harvester'&&<button onClick={()=>commit({type:'HARVEST',plotId})}>Colher canteiro selecionado com a colheitadeira</button>}
          <p className="cyber-tip">WASD ou setas para dirigir. Equipamentos agrícolas são chamados na fazenda. Guardar recolhe o veículo; chame novamente quando precisar.</p>
          <h4>Terminal de teletransporte</h4><label>Destino<select value={destination} onChange={event=>setDestination(event.target.value)}>{[...zones,...newDeliveryZones,...classroomZones].map(zone=><option key={zone.id} value={zone.id}>{zone.label}</option>)}</select></label><button onClick={()=>commit({type:'TELEPORT',zoneId:destination})}>Viajar para o destino</button><p className="cyber-tip">Teletransporte local de demonstração. Cenário, distâncias e rotas são conceituais.</p>
        </>}
        {tab==='inventory'&&<>
          <h3>Sua bolsa de demonstração</h3><dl>{[['flowers','Flores pessoais'],['fish','Peixes virtuais'],['seeds','Sementes'],['harvest','Colheitas']].map(([id,label])=><div key={id}><dt>{label}</dt><dd>{snapshot.inventory[id]}</dd></div>)}</dl><p>Colheitas e pesca ficam neste navegador. Personagens e cópias de objetos são compartilhados pela sala local; transportes e crescimento das plantas ainda são simulações individuais.</p><p><strong>{points} CV</strong> · pontos locais de exploração, sem valor financeiro.</p><button onClick={()=>window.dispatchEvent(new Event('prep:open-learning'))}>Abrir aulas e livros</button>
        </>}
        {tab==='objects'&&<>
          <h3>Objetos compartilhados</h3><p>{sharedServiceLabel(shared.status,others.length+1)}</p>
          <label>Selecionar objeto<select value={selectedObjectId??''} onChange={event=>selectObject(event.target.value)}><option value="">Escolha um objeto</option>{shared.state.objects.map(object=><option key={object.id} value={object.id}>{interactionRooms.cyber.templates.find(t=>t.id===object.templateId)?.name}{object.kind==='copy'?object.ownerId===shared.actorId?' · sua cópia':' · outro jogador':' · base'}</option>)}</select></label>
          {selectedTemplate&&<><h4>{selectedTemplate.name}</h4><p>{selectedTemplate.description}</p><div className="cyber-action-grid">
            {selectedTemplate.portable&&!selectedObject.carriedBy&&<button disabled={!objectNear||!objectOwned||Boolean(held)||objectBusy||shared.status!=='connected'} onClick={()=>objectAction('PICKUP')}>{selectedObject.kind==='base'?'Pegar cópia':'Recolher cópia'}</button>}
            <button disabled={!objectNear||!objectOwned||objectBusy||shared.status!=='connected'} onClick={()=>objectAction('USE')}>Interagir</button>
            {selectedTemplate.movable&&<button disabled={!objectNear||!objectOwned||objectBusy||shared.status!=='connected'} onClick={()=>{setPlacement('MOVE');setNotice('Clique em um ponto livre próximo ou coloque a cópia ao lado.');}}>{selectedObject.kind==='base'?'Mover uma cópia':'Mover sua cópia'}</button>}
            {selectedObject.kind==='copy'&&objectOwned&&<button disabled={!objectNear||objectBusy||shared.status!=='connected'} onClick={()=>objectAction('RETURN')}>Devolver cópia</button>}
          </div>{!objectNear&&<p>Aproxime-se do objeto usando os controles de movimento.</p>}</>}
          {held&&<><p>Carregando: {interactionRooms.cyber.templates.find(t=>t.id===held.templateId)?.name}</p><button onClick={()=>{setPlacement('DROP');setNotice('Escolha um ponto livre do chão próximo.');}}>Soltar cópia</button></>}
          {placement&&<div className="cyber-action-grid"><button onClick={()=>objectAction(placement,placement==='DROP'?held:selectedObject,{x:snapshot.position.x+Math.sin(snapshot.heading+Math.PI/2)*2,y:snapshot.position.y,z:snapshot.position.z+Math.cos(snapshot.heading+Math.PI/2)*2})}>Colocar ao lado</button><button onClick={()=>setPlacement(null)}>Cancelar</button></div>}
          <p className="cyber-tip">Cada cópia tem dono e revisão própria; bases permanecem no mundo. A casa privada não é compartilhada.</p>
        </>}
        {tab==='clothes'&&<>
          <PlayerNameForm value={nameDraft} onChange={setNameDraft} onSubmit={saveUniformName}/>
          <p>Nome bordado: <strong>{playerName}</strong>. Cada jogador usa o nome do próprio usuário.</p>
          <h3>Provador de uniformes</h3><p>{uniformCharacters.length?'Experimente um jaleco sobre o pijama hospitalar nos personagens com uniforme preparado.':'Jalecos e pijamas para os novos personagens realistas estão em ajuste. O traje original do personagem foi mantido.'}</p>{uniformCharacters.length>0&&<label>Personagem com uniforme<select value={costumeFor(character)?character.id:''} onChange={event=>changeCharacter(event.target.value)}><option value="" disabled>Escolha um personagem</option>{uniformCharacters.map(asset=><option key={asset.id} value={asset.id}>{asset.name}</option>)}</select></label>}<label>Cor do pijama<select disabled={!costumeFor(character)} value={snapshot.outfit.color} onChange={event=>commit({type:'OUTFIT',coat:snapshot.outfit.coat,color:event.target.value})}><option value="#247fba">Azul</option><option value="#37664b">Verde</option><option value="#783874">Violeta</option><option value="#c85e26">Laranja</option></select></label><label className="cyber-check"><input type="checkbox" disabled={!costumeFor(character)} checked={snapshot.outfit.coat} onChange={event=>commit({type:'OUTFIT',coat:event.target.checked})}/>Jaleco sobre o pijama</label>{!costumeFor(character)&&uniformCharacters.length>0&&<p>Este personagem mantém seu traje original. Escolha um dos personagens acima para experimentar os uniformes.</p>}<p className="cyber-tip">O nome bordado acompanha o seu perfil. As cores disponíveis alteram somente o tecido do pijama.</p><button onClick={()=>commit({type:'TELEPORT',zoneId:'store'})}>Visitar loja</button>
        </>}
        {tab==='jarvis'&&<>
          <h3>{npc.name}</h3><p>{deployment.apiBaseUrl?'Consulta ao índice de aulas e títulos do Drive pelo serviço PREPARATÓRIO. IA online não conectada.':'Consulta de fontes indisponível nesta publicação. Explore o índice de aulas e os links do acervo. IA online não conectada.'}</p><form onSubmit={ask}><label>Pergunta<textarea value={question} maxLength={500} onChange={event=>setQuestion(event.target.value)} placeholder="O que você deseja estudar?"/></label><button type="submit" disabled={!deployment.apiBaseUrl||asking||question.trim().length<3}>{asking?'Consultando fontes…':'Consultar fontes'}</button></form>
          {answer&&<section className="cyber-answer" role="status"><p>{answer.answer??answer.message??'Não foi possível consultar.'}</p>{answer.sources?.length>0&&<><h4>Fontes encontradas</h4><ul>{answer.sources.map((source,index)=><li key={`${source.id}-${index}`}><a href={source.url} target="_blank" rel="noreferrer">{source.title}{source.page?` · p. ${source.page}`:''}</a></li>)}</ul></>}{answer.links?.map(link=><a className="cyber-external" key={link.url} href={link.url} target="_blank" rel="noreferrer">{link.title} ↗</a>)}{answer.scope&&<p className="cyber-tip">Escopo: {answer.scope}</p>}</section>}
        </>}
        {tab==='home'&&<>
          <h3>Acesso do criador</h3><p>{deployment.apiBaseUrl?'O acesso privado depende de autorização pelo serviço PREPARATÓRIO.':'Casa privada indisponível nesta publicação estática. O serviço de autorização não está conectado.'}</p><form onSubmit={openHome}><label>Senha da casa<input type="password" value={password} onChange={event=>setPassword(event.target.value)} autoComplete="off" spellCheck="false"/></label><button disabled={!deployment.apiBaseUrl||homeBusy||!password} type="submit">Entrar na casa privada</button></form>
        </>}
      </div>
      <footer>{sharedServiceLabel(shared.status,others.length+1)} · {snapshot.mode==='foot'?'A PÉ':snapshot.mode.toUpperCase()} · {clock.text}</footer>
    </aside>}
    <div className="cyber-pad" aria-label="Controles de direção">{[['w','↑','Avançar'],['a','←','Esquerda'],['s','↓','Recuar'],['d','→','Direita']].map(([key,icon,label])=><button key={key} aria-label={label} onClick={event=>{if(event.detail===0){focusGame();input.current[key]=true;window.setTimeout(()=>{input.current[key]=false;},250);}}} onPointerDown={event=>{event.preventDefault();event.currentTarget.setPointerCapture(event.pointerId);focusGame();input.current[key]=true;}} onPointerUp={()=>{input.current[key]=false;focusGame();}} onPointerCancel={()=>{input.current[key]=false;}}>{icon}</button>)}</div>
    <p className="cyber-notice" role="status">{notice}</p><div className="cyber-orbit-note">{clock.subtitle} · {clockSourceLabel(serverClock.status)}</div>
    {privateUrl&&<PrivateHome url={privateUrl} onClose={closeHome}/>}
  </section>;
}
