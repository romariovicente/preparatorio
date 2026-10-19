import {Suspense} from 'react';
import {Html,RoundedBox} from '@react-three/drei';
import {Color,Shape,Vector2} from 'three';
import {DetailedModel} from './DetailedWorld.jsx';
import {newDeliveryWorld,getDeliveryAsset,newDeliveryRoadConnections,buildDeliveryRoadSurfaces} from './newDeliveryWorld.js';

const roadMaterials=Object.fromEntries(Object.entries(newDeliveryRoadConnections.materials).map(([id,material])=>[id,
  {...material,color:new Color(...material.linearColor)}]));
const roadBatches=Array.from(buildDeliveryRoadSurfaces().reduce((batches,record)=>{
  const key=`${record.material}-${record.surfaceY}`;
  if(!batches.has(key))batches.set(key,{id:key,material:record.material,surfaceY:record.surfaceY,shapes:[],surfaceIds:[]});
  const batch=batches.get(key);batch.shapes.push(new Shape(record.points.map(([x,z])=>new Vector2(x,-z))));batch.surfaceIds.push(record.id);
  return batches;
},new Map()).values());
function DeliveryRoadConnections(){return <group name="DELIVERY_LIGACOES_VIARIAS" userData={{walkable:true}}>
  {roadBatches.map(surface=><mesh key={surface.id} name={`DELIVERY_VIA_${surface.id}`} position={[0,surface.surfaceY,0]}
    rotation={[-Math.PI/2,0,0]} receiveShadow userData={{walkable:true,roadSurfaceIds:surface.surfaceIds}}>
    <shapeGeometry args={[surface.shapes]}/><meshStandardMaterial color={roadMaterials[surface.material].color}
      roughness={roadMaterials[surface.material].roughness} polygonOffset polygonOffsetFactor={-1} polygonOffsetUnits={-1}/>
  </mesh>)}
  {[...newDeliveryRoadConnections.streets.map(street=>({id:street.id,label:street.label,position:street.labelPosition})),
    ...newDeliveryRoadConnections.notices].map(label=><Html key={label.id} position={label.position} center distanceFactor={10} zIndexRange={[2,0]}
      style={{pointerEvents:'none'}}><span className="cyber-world-label">{label.label}</span></Html>)}
</group>;}

function DeliveryPlacement({record,onInspect}){
  const asset=getDeliveryAsset(record.assetId);if(!asset)return null;
  const pedestal=record.pedestal;
  return <group name={'DELIVERY_'+record.id} userData={{worldPlacementId:record.id,assetId:asset.id,nonPlayable:true}}>
    {pedestal&&<RoundedBox position={[record.position[0],(pedestal.baseY??0)+pedestal.height/2,record.position[2]]}
      args={[pedestal.width,pedestal.height,pedestal.depth]} radius={.035} smoothness={3} castShadow receiveShadow>
      <meshStandardMaterial color="#78868c" metalness={.55} roughness={.4}/>
    </RoundedBox>}
    <DetailedModel asset={asset} height={record.height??asset.height} position={record.position} rotation={record.rotation}
      onClick={onInspect?event=>{event.stopPropagation();onInspect({asset,placement:record});}:undefined}/>
    <Html position={[record.position[0],record.position[1]+record.labelOffset,record.position[2]]} center distanceFactor={10} zIndexRange={[2,0]}>
      {onInspect?<button className="cyber-world-label" onClick={()=>onInspect({asset,placement:record})}>{record.label}</button>
        :<span className="cyber-world-label">{record.label}</span>}
    </Html>
  </group>;
}
function DeliveryParking(){return <group name="DELIVERY_TERMINAL_PARKING">{newDeliveryWorld.parkingOverrides.map(bay=><group key={bay.id} position={bay.position}>
  <mesh position={[0,-.04,0]} receiveShadow userData={{walkable:true}}><boxGeometry args={[bay.size[0]+.4,.075,bay.size[1]+.25]}/><meshStandardMaterial color="#454b4d" roughness={.92}/></mesh>
  {[-1,1].map(side=><mesh key={side} position={[0,.006,side*bay.size[1]/2]} userData={{walkable:true}}><boxGeometry args={[bay.size[0],.012,.065]}/><meshStandardMaterial color="#e2e4d7" roughness={.8}/></mesh>)}
  <mesh position={[-bay.size[0]/2,.006,0]} userData={{walkable:true}}><boxGeometry args={[.065,.012,bay.size[1]]}/><meshStandardMaterial color="#e2e4d7" roughness={.8}/></mesh>
 </group>)}</group>;}
export default function NewDeliveryWorld({onInspect}){
  return <group name="PREP_NEW_DELIVERY_20261006"><DeliveryRoadConnections/><Suspense fallback={null}>
    {newDeliveryWorld.compositions.filter(record=>record.role!=='transit-vehicle').map(record=><DeliveryPlacement key={record.id} record={record} onInspect={onInspect}/>)}
    <DeliveryParking/>
  </Suspense></group>;
}
