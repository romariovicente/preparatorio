import {doorPosition,doorwayOccupied} from './doorGeometry.js';

// Single-device fallback only. Shared sessions continue to use the server's
// validated door operation rather than being overwritten by this state.
export function changeLocalDoor(doors,building,{position,mode='foot',players={}}={},nowMs=Date.now()){
  const entry=doorPosition(building);
  if(mode!=='foot'||!position||Math.hypot(position.x-entry[0],position.z-entry[2])>5||Math.abs((position.y??0)-entry[1])>1.6)return {ok:false,message:'Aproxime-se da porta a pé para abrir ou fechar.'};
  const current=doors?.[building.id],open=!current?.open;
  if(!open&&doorwayOccupied({...players,current:{online:true,position}},building))return {ok:false,message:'Afaste-se da passagem para fechar a porta.'};
  return {ok:true,doors:{...doors,[building.id]:{open,revision:(current?.revision??0)+1,changedAtMs:nowMs}},message:open?'Porta aberta.':'Porta fechada.'};
}
