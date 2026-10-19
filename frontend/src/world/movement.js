export const campusObstacles=[{x:0,z:-4.5,w:3.4,d:1.6},{x:-7,z:-4,w:1.4,d:1.4},{x:7,z:-4,w:1.4,d:1.4}];
export function advancePosition(position,direction,delta,speed=2.2,obstacles=campusObstacles){
  const length=Math.hypot(direction.x,direction.z);if(!length)return {...position};
  const distance=Math.min(Math.max(delta,0),.05)*speed;const radius=.3;
  const blocked=(x,z)=>obstacles.some(o=>Math.abs(x-o.x)<o.w/2+radius&&Math.abs(z-o.z)<o.d/2+radius);
  const x=Math.max(-10,Math.min(10,position.x+direction.x/length*distance));
  const px=blocked(x,position.z)?position.x:x;
  const z=Math.max(-9,Math.min(10,position.z+direction.z/length*distance));
  return {x:px,z:blocked(px,z)?position.z:z};
}
