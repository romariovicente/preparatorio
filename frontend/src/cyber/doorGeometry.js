export function doorPosition(building){return [building.center[0],building.center[1],building.center[2]+building.depth/2];}
export function doorApproach(building){const p=doorPosition(building);return {x:p[0],y:p[1],z:p[2]+3.4};}
export function insideBuilding(position,building,margin=0){return Math.abs(position.x-building.center[0])<building.width/2-margin&&Math.abs(position.z-building.center[2])<building.depth/2-margin&&Math.abs((position.y??0)-building.center[1])<2;}
export function buildingColliders(building,door){
  const [x,,z]=building.center,w=building.width,d=building.depth,t=.26,gap=building.opening;
  const result=[{x:x-w/2,z,w:t,d},{x:x+w/2,z,w:t,d},{x,z:z-d/2,w,d:t},
    {x:x-(w+gap)/4,z:z+d/2,w:(w-gap)/2,d:t},{x:x+(w+gap)/4,z:z+d/2,w:(w-gap)/2,d:t}];
  if(!door?.open)result.push({x,z:z+d/2,w:gap,d:.18});
  return result;
}
export function cityColliders(base,buildings,doors={},nowMs=Date.now()){
  const replaced=base.filter(c=>!buildings.some(b=>Math.abs(c.x-b.center[0])<.01&&Math.abs(c.z-b.center[2])<.01));
  return [...replaced,...buildings.flatMap(b=>{const door=doors[b.id];return buildingColliders(b,{open:door?.open&&(!door.changedAtMs||nowMs-door.changedAtMs>=1100)});})];
}
export function doorwayOccupied(players,building){
  const [x,y,z]=doorPosition(building);
  return Object.values(players).some(p=>p.online&&p.position&&Math.abs(p.position.x-x)<building.opening/2+.4&&Math.abs(p.position.z-z)<.75&&Math.abs((p.position.y??0)-y)<1.5);
}
export function doorLeafTransform(building,side,progress){
  const clamped=Math.max(0,Math.min(1,progress));
  return building.style==='slide'?{x:side*building.opening/4+side*clamped*(building.opening/2+.12),angle:0}
    :{x:side*building.opening/2,angle:-side*clamped*Math.PI/2};
}
