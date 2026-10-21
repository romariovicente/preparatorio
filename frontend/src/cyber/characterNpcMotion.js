const TAU=Math.PI*2;

function phaseFor(id){
  let hash=0;for(const character of String(id??''))hash=(hash*31+character.codePointAt(0))>>>0;
  return hash/0xffffffff*TAU;
}

export function characterNpcMotionSample(entry,elapsed,{radius=.32,speed=.46}={}){
  const base=Array.isArray(entry?.position)?entry.position:[0,0,0];
  if(!entry?.walkingAnimationAvailable||!Number.isFinite(elapsed)||radius<=0||speed<=0)
    return {position:[...base],heading:Number(entry?.heading)||0,moving:false};
  const angle=phaseFor(entry.id)+elapsed*speed/radius;
  const x=base[0]+Math.cos(angle)*radius,z=base[2]+Math.sin(angle)*radius;
  const heading=Math.atan2(-Math.sin(angle),Math.cos(angle));
  return {position:[x,base[1],z],heading,moving:true};
}
