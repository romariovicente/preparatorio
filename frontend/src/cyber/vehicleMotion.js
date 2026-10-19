export const STEERING_LIMIT=.52;
export function carMotion(heading,keys,delta,speed=14,wheelbase=2.7){
  const dt=Math.max(0,Math.min(.05,Number.isFinite(delta)?delta:0));
  // With Three.js +Z as the nose, a negative Y rotation turns to the driver's right.
  const throttle=(keys.w?1:0)-(keys.s?1:0),turn=(keys.a?1:0)-(keys.d?1:0);
  const steeringAngle=turn*STEERING_LIMIT;
  const travelSpeed=throttle*(throttle<0?speed*.45:speed);
  const yaw=heading+travelSpeed/wheelbase*Math.tan(steeringAngle)*dt;
  return {heading:yaw,steeringAngle,direction:{x:Math.sin(yaw)*throttle,y:0,z:Math.cos(yaw)*throttle},speed:Math.abs(travelSpeed)};
}
export function wheelRotation(previous,from,to,heading,radius=.32){
  const distance=Math.hypot(to.x-from.x,to.z-from.z),projection=(to.x-from.x)*Math.sin(heading)+(to.z-from.z)*Math.cos(heading);
  return (Number.isFinite(previous)?previous:0)+Math.sign(projection)*distance/Math.max(.1,radius);
}
