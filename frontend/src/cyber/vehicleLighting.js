import profiles from '../config/vehicleLights.json' with {type:'json'};

export const HEADLIGHT_MODES={
  auto:'Automático · DRL de dia',
  off:'Desligado',
  position:'Posição',
  drl:'Luz diurna (DRL)',
  low:'Farol baixo',
  high:'Farol alto',
};
export const AUXILIARY_LIGHTS={
  fog:'Neblina',
  driving:'Milha',
  bar:'Luzes superiores',
  work:'Luz de trabalho',
};
const BEAMS={
  low:{reach:31,aim:20,angle:.28,power:225,color:'#fff1da'},
  high:{reach:64,aim:50,angle:.19,power:460,color:'#fff5e5'},
  fog:{reach:17,aim:10,angle:.53,power:110,color:'#ffdfa2'},
  driving:{reach:51,aim:41,angle:.14,power:260,color:'#fff3de'},
  bar:{reach:44,aim:26,angle:.32,power:235,color:'#fff3de'},
  work:{reach:12,angle:.55,power:110,color:'#fff1da'},
};

export function vehicleLightingProfile(sourceId) {
  return Object.hasOwn(profiles,sourceId)?profiles[sourceId]:null;
}

export function readVehicleLights(profile,value) {
  const mode=Object.hasOwn(HEADLIGHT_MODES,value?.mode)?value.mode:'auto';
  const auxiliaries=Object.fromEntries(Object.keys(AUXILIARY_LIGHTS)
    .filter(id=>profile.lamps[id]?.length)
    .map(id=>[id,value?.auxiliaries?.[id]===true]));
  return {mode,auxiliaries};
}

export function changeVehicleLights(profile,value,change) {
  const next=readVehicleLights(profile,value);
  if(Object.hasOwn(HEADLIGHT_MODES,change.mode))return {...next,mode:change.mode};
  if(Object.hasOwn(next.auxiliaries,change.auxiliary)&&typeof change.enabled==='boolean'){
    return {...next,auxiliaries:{...next.auxiliaries,[change.auxiliary]:change.enabled}};
  }
  return null;
}

export function lowBeamMaskLevel(pitch,angle,u,v) {
  // With the projector facing +Z, increasing texture U points to vehicle right.
  const rise=Math.min(1,Math.max(0,(u-.48)/.16));
  const ceiling=.5+.5*Math.tan(pitch-.012+.009*rise)/Math.tan(angle);
  return Math.min(1,Math.max(0,(ceiling-v)/.014));
}

export function vehicleLightOutputs(profile,value,powered,illuminate,daylight=false) {
  const {mode,auxiliaries}=readVehicleLights(profile,value);
  const main=mode==='low'||mode==='high';
  const marker=main||mode==='position'||powered&&(mode==='drl'||mode==='auto'&&daylight);
  const enabledAuxiliaries=Object.keys(auxiliaries).filter(id=>auxiliaries[id]);
  const lamps=[...(main?['main']:[]),...(marker?['marker']:[]),...enabledAuxiliaries];
  const beams=illuminate?[...(main?[mode]:[]),...enabledAuxiliaries].map(id=>{
    const optic=BEAMS[id],lamp=profile.lamps[id]?.[0];
    const origin=lamp?[0,lamp.position[1],id==='work'?lamp.position[2]:profile.beamOrigin[2]]:profile.beamOrigin;
    const target=id==='work'?profile.workTarget:[origin[0],.07,origin[2]+optic.aim];
    return {id,...optic,origin,target};
  }):[];
  return {lamps,beams};
}
