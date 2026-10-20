// The same active source is suppressed in rendering and static collision lists.
// Its personal copy supplies the moving footprint, so no invisible source box
// can remain behind while that copy is in use.
export function activeWorldPlacements(records,personalVehicles={}){
  const suppressed=new Set([personalVehicles.car?.sourceId,personalVehicles.mototaxi?.sourceId].filter(Boolean));
  return records.filter(record=>!suppressed.has(record.id));
}

export function baseVehicleIsVisible(id,personalVehicles={}){
  const personal=personalVehicles[id];
  if(!personal)return true;
  // Cars and motorcycles can originate at a different authored placement.
  // Keep the unrelated default vehicle present and selectable in that case.
  return ['car','mototaxi'].includes(id)&&(personal.sourceId??id)!==id;
}
