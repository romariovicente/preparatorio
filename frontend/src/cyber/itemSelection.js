// Selection changes focus only. Taking or returning an item remains an explicit action.
export function cycleItem(objects,selectedId,direction,actorId){
  const available=objects.filter(object=>object.kind==='base'||object.ownerId===actorId);
  if(!available.length)return null;
  const current=available.findIndex(object=>object.id===selectedId);
  const index=current<0?(direction<0?available.length-1:0):(current+(direction<0?-1:1)+available.length)%available.length;
  return available[index];
}
