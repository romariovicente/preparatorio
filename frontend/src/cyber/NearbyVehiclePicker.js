import {createElement} from 'react';

export default function NearbyVehiclePicker({choices,selectedKey,onSelect}){
  if(!choices.length)return null;
  return createElement('div',{className:'cyber-nearby-vehicles',role:'group','aria-label':'Veículos próximos'},
    createElement('strong',null,'Escolha um veículo próximo'),
    createElement('div',{className:'cyber-action-grid'},choices.map(choice=>createElement('button',{
      key:choice.key,'aria-pressed':selectedKey===choice.key,onClick:()=>onSelect(choice),
    },`${choice.label} · ${choice.distance.toFixed(1)} m${choice.kind==='bus'&&!choice.canEnter?' · aguarde a parada':''}`))));
}
