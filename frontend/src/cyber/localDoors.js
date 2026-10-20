import {doorPosition,doorwayOccupied} from './doorGeometry.js';
import publicBuildings from '../config/buildingDoors.json' with {type:'json'};

const finitePosition=position=>position&&[position.x,position.y??0,position.z].every(Number.isFinite);

export function publicDoorCapabilities(building,{position,mode='foot',connected=false,open=false}={}){
  const known=publicBuildings.find(candidate=>candidate.id===building?.id);
  const entry=known&&doorPosition(known);
  const nearby=Boolean(entry&&finitePosition(position)&&Math.hypot(position.x-entry[0],position.z-entry[2])<=5&&Math.abs((position.y??0)-entry[1])<=1.6);
  const canToggle=Boolean(known&&mode==='foot'&&nearby);
  return {canToggle,canEnter:canToggle&&Boolean(open),nearby,scope:connected?'shared':'local'};
}

export function publicDoorScopeLabel(connected){
  return connected?'A abertura é compartilhada pelos jogadores conectados à sala.':'As portas funcionam nesta sessão de jogo.';
}

// Single-device fallback only. Shared sessions continue to use the server's
// validated door operation rather than being overwritten by this state.
export function changeLocalDoor(doors,building,{position,mode='foot',players={}}={},nowMs=Date.now()){
  const entry=doorPosition(building);
  if(mode!=='foot'||!finitePosition(position)||Math.hypot(position.x-entry[0],position.z-entry[2])>5||Math.abs((position.y??0)-entry[1])>1.6)return {ok:false,message:'Aproxime-se da porta a pé para abrir ou fechar.'};
  const current=doors?.[building.id],open=!current?.open;
  if(!open&&doorwayOccupied({...players,current:{online:true,position}},building))return {ok:false,message:'Afaste-se da passagem para fechar a porta.'};
  return {ok:true,doors:{...doors,[building.id]:{open,revision:(current?.revision??0)+1,changedAtMs:nowMs}},message:open?'Porta aberta.':'Porta fechada.'};
}
