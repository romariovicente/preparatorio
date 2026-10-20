import {nearbyInteractiveCars,resolveCarSource} from './carInteraction.js';
import {nearbyMotorcycles,resolveMotorcycle} from './motorcycleInteraction.js';
import {BUS_IDS,sampleLiveBus,busDoorPosition,canBoardBus} from './busInteraction.js';

export function worldVehicleClickHandler(id,{onSelectCar,onSelectMoto}={}){
  const select=resolveCarSource(id)?onSelectCar:resolveMotorcycle(id)?onSelectMoto:null;
  return typeof select==='function'?event=>{event.stopPropagation();select(id);}:undefined;
}

export function nearbyVehicleChoices(state,maxRange=7,driveDefinitions={}){
  const p=state?.position;
  if(!p||![p.x,p.y??0,p.z,maxRange].every(Number.isFinite)||maxRange<0||state.mode!=='foot')return [];
  const free=!state.sitting&&!state.elevator&&!state.jump&&!state.carEntry;
  const cars=nearbyInteractiveCars(p,state.personalVehicles?.car,maxRange).map(car=>({...car,kind:'car',key:`car:${car.id}`,canEnter:free}));
  const motos=nearbyMotorcycles(p,state.personalVehicles?.mototaxi,maxRange).map(moto=>({...moto,kind:'moto',key:`moto:${moto.id}`,canEnter:free}));
  const buses=BUS_IDS.map(id=>sampleLiveBus(state,id)).filter(Boolean).map(bus=>{
    const position=busDoorPosition(bus);
    return {...bus,position,distance:Math.hypot(p.x-position.x,p.z-position.z),kind:'bus',key:`bus:${bus.id}`,canEnter:free&&canBoardBus(state,bus,maxRange)};
  }).filter(bus=>bus.distance<=maxRange&&Math.abs((p.y??0)-(bus.y??0))<=1.6);
  const equipment=Object.values(driveDefinitions).filter(definition=>!['car','mototaxi'].includes(definition.id)).map(definition=>{
    const position=state.personalVehicles?.[definition.id]??definition.position;
    if(!position||![position.x,position.y??0,position.z].every(Number.isFinite))return null;
    return {id:definition.id,label:definition.label,position,distance:Math.hypot(p.x-position.x,p.z-position.z),kind:'drive',key:`drive:${definition.id}`,canEnter:free};
  }).filter(vehicle=>vehicle&&vehicle.distance<=maxRange&&Math.abs((p.y??0)-(vehicle.position.y??0))<=1.6);
  return [...cars,...motos,...buses,...equipment].sort((a,b)=>a.distance-b.distance||a.key.localeCompare(b.key));
}

// A clicked selection wins over proximity. If it is no longer reachable, do
// not silently board a different vehicle when the player presses F.
export function chooseNearbyVehicle(state,selected,maxRange=7,driveDefinitions={}){
  const candidates=nearbyVehicleChoices(state,maxRange,driveDefinitions);
  return selected?candidates.find(candidate=>candidate.kind===selected.kind&&candidate.id===selected.id)??null:candidates[0]??null;
}
