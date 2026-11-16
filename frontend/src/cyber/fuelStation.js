export const fuelStationZone = {
  id: 'fuel-station',
  label: 'Posto de Gasolina · Via Sul',
  position: [-51.5, 0, 102],
  approach: [-55, 0, 95.5],
};

export const fuelStationPavement = {position:[0,-.036,0], size:[29,.12,17.5]};
export const fuelStationCanopy = {position:[-3,5.15,-.7], size:[19,.52,9.4]};
export const fuelStationShop = {position:[10,1.87,3.35], size:[8,3.7,7.1]};
export const fuelStationPumpX = [-9,2];

// Movement uses fixed obstacles for the islands, shop and sign, leaving both
// the canopy and the open lane free. Ground queries use the exported pavement.
const localObstacles = [
  ...fuelStationPumpX.map((x,index)=>[`pump-island-${index+1}`,x,0,1.65,6.51]),
  ['shop',10,3.35,8,7.1],
  ['sign',12.1,-6.25,.42,.38],
];

export const fuelStationColliders = localObstacles.map(([id,x,z,w,d])=>({
  id:`fuel-station-${id}`, x:x+fuelStationZone.position[0], z:z+fuelStationZone.position[2], w, d,
}));

export function fuelStationArrivalCamera(action, position) {
  if(action.type!=='TELEPORT'||action.zoneId!==fuelStationZone.id)return null;
  const {x,y,z}=position;
  return {position:[x+7.5,y+8.8,z-26],target:[x+1.5,y+1.55,z+1]};
}
