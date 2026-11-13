export const mechanicWorkshopAsset = '/assets/buildings/BLD_Oficina_Publica_PREP_20261111.glb';

export const mechanicWorkshopZone = {
  id: 'mechanic-workshop',
  label: 'Oficina Mecânica · Pátio',
  position: [-47, 0, 3],
  approach: [-60, 0, 0],
};

export const mechanicWorkshopCollider = {
  id: 'mechanic-workshop-building',
  x: -44.575,
  z: 2.8,
  w: 12.85,
  d: 17.3,
};

export function workshopArrivalCamera(action, position) {
  if (action.type !== 'TELEPORT' || action.zoneId !== mechanicWorkshopZone.id) return null;
  const {x,y,z} = position;
  return {position:[x-12,y+4,z-2.8],target:[x,y+1,z]};
}
