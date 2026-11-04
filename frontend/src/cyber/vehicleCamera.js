// Apply only on entry: ordinary frames keep the player's chosen orbit intact.
export function entryVehicleCamera(previousMode,state){
  if(previousMode===state?.mode||!['truck','car','mototaxi'].includes(state?.mode))return null;
  const {x,y,z}=state.position??{},heading=state.heading;
  if(![x,y,z,heading].every(Number.isFinite))return null;
  const truck=state.mode==='truck',distance=truck?17:9,lateral=truck?7:4;
  return {
    position:[x-Math.sin(heading)*distance+Math.cos(heading)*lateral,truck?6.5:3.6,z-Math.cos(heading)*distance-Math.sin(heading)*lateral],
    target:[x,y+1,z],
  };
}
