import {useEffect,useMemo,useRef,useState} from 'react';
import {useFrame} from '@react-three/fiber';
import {Html,useGLTF} from '@react-three/drei';
import {HOSPITAL_ASSET_URL,createDoorController,hasNamedAncestor,inspectHospitalModel,PUBLIC_DOOR_PREFIX} from '../hospital/hospitalModel.js';
import {hospitalReception,HOSPITAL_PLATFORM_URL,markHospitalFloors,markHospitalPlatformFloors,readHospitalDoorColliders,roomDoorwayOccupied} from './hospitalReception.js';
import {insideBuilding} from './doorGeometry.js';
import CityAssetBoundary from './CityAssetBoundary.js';
import hospitalChairPlan from '../config/hospitalChairs.json';
import HospitalChairs from './HospitalChairs.jsx';
import HospitalEquipment from './HospitalEquipment.jsx';
import {hideHospitalChairRoots,restoreHospitalChairRoots,hospitalChairAssetUrl} from './hospitalChairs.js';

function HospitalPlatform(){
  const {scene}=useGLTF(HOSPITAL_PLATFORM_URL);
  const model=useMemo(()=>{
    const copy=scene.clone(true);
    markHospitalPlatformFloors(copy);
    return copy;
  },[scene]);
  return <primitive object={model} dispose={null}/>;
}

export default function HospitalReception({building,door,simulation,runtime,onToggle,onNotice,players={}}){
  const gltf=useGLTF(HOSPITAL_ASSET_URL);
  const prepared=useMemo(()=>{
    const scene=gltf.scene.clone(true);markHospitalFloors(scene);
    return {scene,info:inspectHospitalModel(scene,gltf.animations)};
  },[gltf.scene,gltf.animations]);
  const controllers=useRef({public:null,rooms:{}});
  const [rooms,setRooms]=useState({});
  const [chairsReady,setChairsReady]=useState(false);
  useEffect(()=>{
    const names=hospitalChairPlan.placements.map(placement=>placement.originalRoot);
    if(chairsReady)hideHospitalChairRoots(prepared.scene,names);
    else restoreHospitalChairRoots(prepared.scene,names);
  },[prepared.scene,chairsReady]);
  useEffect(()=>{
    controllers.current={public:createDoorController(prepared.scene,prepared.info.doorClips),rooms:Object.fromEntries(hospitalReception.roomDoors.map(room=>[room.id,createDoorController(prepared.scene,prepared.info.roomClips.filter(clip=>clip.name===`Room_Open_${room.id}`))]))};
    return()=>{controllers.current.public?.dispose();Object.values(controllers.current.rooms).forEach(controller=>controller?.dispose());controllers.current={public:null,rooms:{}};};
  },[prepared]);
  // These are owned Three.js scene objects and a simulation ref, not React
  // render data. The frame loop updates their animation, roof and physics data.
  /* eslint-disable react-hooks/immutability */
  useFrame((_,delta)=>{
    controllers.current.public?.update(Boolean(door?.open),delta);
    for(const [id,controller] of Object.entries(controllers.current.rooms))controller?.update(Boolean(rooms[id]),delta);
    const p=simulation.current.position,near=Math.hypot(p.x-building.center[0],p.z-building.center[2]-building.depth/2)<10;
    for(const roof of prepared.info.roofNodes)roof.visible=!insideBuilding(p,building)&&!(door?.open&&near);
    runtime.current.dynamicColliders=readHospitalDoorColliders(prepared.scene);
  });
  /* eslint-enable react-hooks/immutability */
  function toggleRoom(room){
    const p=simulation.current.position,target=room.closedCollider;
    if(simulation.current.mode!=='foot'||Math.abs((p.y??0)-hospitalReception.position[1])>1.6||Math.hypot(p.x-hospitalReception.position[0]-target.x,p.z-hospitalReception.position[2]-target.z)>4){onNotice?.('Aproxime-se da porta interna a pé.');return;}
    const occupied=[p,...Object.values(players).filter(player=>player.online).map(player=>player.position)];
    if(rooms[room.id]&&roomDoorwayOccupied(room,occupied)){onNotice?.('Afaste-se da passagem para fechar a porta.');return;}
    setRooms(previous=>({...previous,[room.id]:!previous[room.id]}));
    onNotice?.(rooms[room.id]?'Porta interna fechada.':'Porta interna aberta.');
  }
  return <group name="PREP_HOSPITAL_RECEPTION_PLAYABLE" position={hospitalReception.position} userData={{dynamicCollider:true,hospitalModule:true}}>
    <CityAssetBoundary label="entrada do hospital"><HospitalPlatform/></CityAssetBoundary>
    {hospitalChairPlan.ready&&<CityAssetBoundary label="cadeiras do hospital" assetUrls={[hospitalChairAssetUrl(hospitalChairPlan)]}><HospitalChairs plan={hospitalChairPlan} onReady={setChairsReady}/></CityAssetBoundary>}
    <primitive object={prepared.scene} dispose={null} onClick={event=>{
      if(hasNamedAncestor(event.object,PUBLIC_DOOR_PREFIX)){event.stopPropagation();onToggle(building);return;}
      const room=hospitalReception.roomDoors.find(record=>hasNamedAncestor(event.object,record.hingeName));
      if(room){event.stopPropagation();toggleRoom(room);}
    }}/>
    <Html position={[0,3.45,hospitalReception.publicDoor.z+.3]} center distanceFactor={10} zIndexRange={[2,0]}><button className="cyber-world-label" onClick={()=>onToggle(building)}>{door?.open?'Fechar porta':'Abrir porta'}<br/>{building.label}</button></Html>
    {hospitalReception.roomDoors.map(room=><Html key={room.id} position={[room.hingePosition[0],2.65,room.closedCollider.z]} center distanceFactor={8} zIndexRange={[2,0]}><button className="cyber-world-label" onClick={()=>toggleRoom(room)}>{rooms[room.id]?'Fechar':'Abrir'} · {room.label}</button></Html>)}
    <HospitalEquipment simulation={simulation} onInspect={onNotice}/>
    <pointLight position={[0,3.3,3]} color="#fff5e5" intensity={32} distance={24} decay={2}/>
  </group>;
}
