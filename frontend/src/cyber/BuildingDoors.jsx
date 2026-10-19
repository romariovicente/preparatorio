import {resolveAssetReferences} from '../config/deploymentConfig.js';
import {useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {Html,RoundedBox} from '@react-three/drei';
import catalogRaw from '../config/suppliedAssets.json';
const catalog=resolveAssetReferences(catalogRaw);
import buildings from '../config/buildingDoors.json';
import {DetailedModel} from './DetailedWorld.jsx';
import {doorPosition,insideBuilding,doorLeafTransform} from './doorGeometry.js';
function Solid({position,size,color='#c2c9cc',metalness=0,roughness=.65,...props}){
  return <RoundedBox position={position} args={size} radius={Math.min(.06,...size.map(s=>s/4))} smoothness={3} castShadow receiveShadow {...props}><meshStandardMaterial color={color} metalness={metalness} roughness={roughness}/></RoundedBox>;
}
function Source({id,height,position,rotation}){const asset=catalog.find(a=>a.id===id);return asset?<DetailedModel asset={asset} height={height} position={position} rotation={rotation}/>:null;}
function DoorLeaf({building,side,animation}){
  const ref=useRef(null),half=building.opening/2,h=2.9;
  useFrame(()=>{const pose=doorLeafTransform(building,side,animation.current);ref.current.position.x=pose.x;ref.current.rotation.y=pose.angle;});
  const center=building.style==='swing'?-side*half/2:0;
  return <group ref={ref}><group position={[center,h/2,0]}>
    <mesh castShadow><boxGeometry args={[half-.06,h-.12,.045]}/><meshPhysicalMaterial color="#a9c5ce" roughness={.12} metalness={.05} transparent opacity={.24} side={2} depthWrite={false}/></mesh>
    {[-1,1].map(s=><Solid key={'v'+s} position={[s*(half/2-.035),0,0]} size={[.055,h,.1]} color="#596c76" metalness={.8} roughness={.2}/>)}
    {[-1,1].map(s=><Solid key={'h'+s} position={[0,s*(h/2-.035),0]} size={[half,.055,.1]} color="#596c76" metalness={.8} roughness={.2}/>)}
    <Solid position={[-side*(half/2-.15),-.08,.12]} size={[.055,.46,.06]} color="#d6dfe1" metalness={.9} roughness={.15}/>
    <Solid position={[0,.05,.032]} size={[half-.11,.1,.012]} color="#dcebf0" roughness={.3}/>
  </group></group>;
}
function Interior({building,simulation}){
  const w=building.width,d=building.depth;
  const light=useRef(null);
  useFrame(()=>{if(light.current){const p=simulation.current.position;light.current.visible=Math.hypot(p.x-building.center[0],p.z-building.center[2])<Math.max(w,d)+8;}});
  return <group>
    <Solid position={[-w/3,.58,d/2-4.4]} size={[w/5,1.16,1.25]} color="#ddd8ce"/>
    <Solid position={[-w/3,1.2,d/2-4.4]} size={[w/5+.14,.07,1.4]} color="#353f44" roughness={.25}/>
    <Solid position={[-w/3,1.48,d/2-4.4]} size={[.6,.38,.06]} color="#1e3444" metalness={.2}/>
    {building.interior==='hospital'&&<><Source id="SUP_charite_university_hospital___operating_room" height={2.78} position={[-8,.025,-4]}/><Source id="SUP_kit_hospital" height={2} position={[8,.025,-5]}/><Source id="SUP_gm_hospitals_stand_design" height={2} position={[8,.025,5]}/></>}
    {building.interior==='laboratory'&&<Source id="SUP_Clone_Human_Sleep_Module_Lab" height={3.1} position={[4,.025,-1]}/>}
    {building.interior==='moto'&&<><Source id="SUP_cyberpunk_kawasaki_ninja" height={1.3} position={[-4,.025,-3]}/><Source id="SUP_moto_in_cyberpunk_style" height={1.17} position={[4,.025,-3]} rotation={[0,Math.PI/2,0]}/></>}
    {building.interior==='store'&&[-w/2+2,w/2-2].map(x=><group key={x}>{[.6,1.25,1.9].map(y=><group key={y}><Solid position={[x,y,-2]} size={[2,.08,5]} color="#6c7375" metalness={.55}/>{[-3.5,-2,-.5].map(z=><Solid key={z} position={[x,y+.2,z]} size={[.6,.35,.55]} color={y>1?'#d0d9d5':'#527780'}/>)}</group>)}<Solid position={[x,1.1,-2]} size={[.08,2.2,5.2]} color="#707a7c" metalness={.6}/></group>)}
    {building.interior==='house'&&<><Solid position={[-3,.4,-2]} size={[2,.7,3.1]} color="#777b79"/><Solid position={[-3,.81,-2]} size={[1.9,.2,3]} color="#e7ded0"/><Solid position={[3,.65,-2]} size={[2,1.3,.7]} color="#997758"/></>}
    {building.interior==='station'&&[-5,0,5].map(x=><Solid key={x} position={[x,.48,-2]} size={[3,.95,1]} color="#73838a"/>)}
    <pointLight ref={light} position={[0,building.height-.65,0]} color="#fff1df" intensity={60} distance={Math.max(w,d)} decay={2}/>
    {[-w/4,w/4].map(x=><mesh key={x} position={[x,building.height-.2,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[2.5,.45]}/><meshStandardMaterial color="#f1f2e6" emissive="#f3f0da" emissiveIntensity={2.5}/></mesh>)}
  </group>;
}
function Building({building,door,simulation,onToggle}){
  const roof=useRef(null),animation=useRef(door?.open?1:0),doorRoot=useRef(null);
  const w=building.width,d=building.depth,h=building.height,gap=building.opening,span=(w-gap)/2;
  useFrame((_,delta)=>{
    const target=door?.open?1:0;animation.current+=Math.sign(target-animation.current)*Math.min(Math.abs(target-animation.current),delta/1.25);
    const p=simulation.current.position,entry=doorPosition(building),near=Math.hypot(p.x-entry[0],p.z-entry[2])<10;
    roof.current.visible=!insideBuilding(p,building)&&!(door?.open&&near);
    if(doorRoot.current)doorRoot.current.userData.openProgress=animation.current;
  });
  return <group position={building.center}>
    <Solid position={[0,-.055,0]} size={[w,.16,d]} color="#c8c7be" roughness={.28} userData={{walkable:true}}/>
    <Solid position={[-w/2,h/2,0]} size={[.26,h,d]} color={building.color}/><Solid position={[w/2,h/2,0]} size={[.26,h,d]} color={building.color}/><Solid position={[0,h/2,-d/2]} size={[w,h,.26]} color={building.color}/>
    {[-1,1].map(s=><group key={s} position={[s*(w+gap)/4,0,d/2]}><Solid position={[0,.43,0]} size={[span,.86,.26]} color={building.color}/><mesh position={[0,1.92,0]}><boxGeometry args={[span- .08,2.12,.06]}/><meshPhysicalMaterial color="#a7bcc3" transparent opacity={.3} roughness={.18} depthWrite={false}/></mesh><Solid position={[0,3.1,0]} size={[span,.18,.3]} color="#525f64" metalness={.6}/></group>)}
    <Solid position={[0,(h+3.05)/2,d/2]} size={[w,h-3.05,.28]} color={building.color}/>
    <group ref={roof}><Solid position={[0,h+.12,0]} size={[w+.4,.24,d+.4]} color="#697579" roughness={.8}/></group>
    <Solid position={[0,3.13,d/2+.5]} size={[gap+2,.13,1.6]} color="#66737a" metalness={.6}/>
    <Interior building={building} simulation={simulation}/>
    <group ref={doorRoot} name={'DOOR_'+building.id} position={[0,.025,d/2+.04]} onClick={event=>{event.stopPropagation();onToggle(building);}}>
      <DoorLeaf building={building} side={-1} animation={animation}/><DoorLeaf building={building} side={1} animation={animation}/>
      <Html position={[0,3.55,.3]} center distanceFactor={10} zIndexRange={[2,0]}><button className="cyber-world-label" onClick={()=>onToggle(building)} aria-label={`${door?.open?'Fechar':'Abrir'} porta · ${building.label}`}>{door?.open?'Fechar porta':'Abrir porta'}<br/>{building.label}</button></Html>
    </group>
  </group>;
}
export default function BuildingDoors({doors,simulation,onToggle}){return <group>{buildings.map(b=><Building key={b.id} building={b} door={doors?.[b.id]} simulation={simulation} onToggle={onToggle}/>)}</group>;}
