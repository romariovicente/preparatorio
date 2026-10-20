import {createElement} from 'react';
import {publicDoorCapabilities} from './localDoors.js';

export default function PublicBuildingActions({building,position,mode,connected,open,onVisit,onToggle,onEnter}){
  const capabilities=publicDoorCapabilities(building,{position,mode,connected,open});
  return createElement('div',{className:'cyber-action-grid'},
    createElement('button',{onClick:()=>onVisit(building)},`Ir à entrada · ${building.label}`),
    createElement('button',{disabled:!capabilities.canToggle,onClick:()=>onToggle(building)},`${open?'Fechar':'Abrir'} porta · ${building.label}`),
    createElement('button',{disabled:!capabilities.canEnter,onClick:()=>onEnter(building)},`Entrar · ${building.label}`));
}
