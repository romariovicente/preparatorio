import CityAssetBoundary from './CityAssetBoundary.js';
import {resolveAssetReferences} from '../config/deploymentConfig.js';
import {useEffect,useRef} from 'react';
import SuppliedModel from '../world/SuppliedModel.jsx';
import manifestRaw from '../config/realisticWorldManifest.json';
const manifest=resolveAssetReferences(manifestRaw);
import {setWorldShadows} from './modelLighting.js';
import {resolveCarSource} from './carInteraction.js';
import monumentsRaw from '../config/monumentAssets.json';
const monuments=resolveAssetReferences(monumentsRaw);
import {resolveMotorcycle} from './motorcycleInteraction.js';
import CarModel from './CarModel.jsx';
import MotorcycleModel from './MotorcycleModel.jsx';
import {activeWorldPlacements} from './vehiclePlacements.js';
import {worldVehicleClickHandler} from './vehicleSelection.js';
function LoadedDetailedModel({asset,height,...props}){
  const group=useRef(null);
  useEffect(()=>{if(group.current)setWorldShadows(group.current);},[asset.url,height]);
  return <group ref={group} {...props}><SuppliedModel asset={asset} height={height}/></group>;
}
export function DetailedModel(props){return <CityAssetBoundary label={props.asset.name??props.asset.id}><LoadedDetailedModel {...props}/></CityAssetBoundary>;}
export default function DetailedWorld({onSelectCar,onSelectMoto,personalVehicles={}}){return <group>{activeWorldPlacements(manifest.environmentReplacements,personalVehicles).map(record=>{
  const car=resolveCarSource(record.id),moto=resolveMotorcycle(record.id);
  const onClick=worldVehicleClickHandler(record.id,{onSelectCar,onSelectMoto});
  return car||moto?<group key={record.id} position={record.position} rotation={record.rotation} userData={{dynamicCollider:true}} onClick={onClick}><CityAssetBoundary label={record.id}>
    {car?<CarModel asset={record}/>:<MotorcycleModel asset={record}/>}
  </CityAssetBoundary></group>:<DetailedModel key={record.id} asset={record} height={record.height} position={record.position} rotation={record.rotation}/>;
})}{monuments.flatMap(asset=>asset.positions.map((position,i)=><DetailedModel key={`${asset.id}-${i}`} asset={asset} height={asset.height} position={position}/>))}</group>;}
