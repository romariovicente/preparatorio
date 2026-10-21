export const hospitalPatientRoute=[
  [55,0.02,-8],
  [55,0.02,-18],
  [52,0.02,-23],
  [49.2,0.28,-25.15],
  [48,0.28,-25.45],
];

const finitePoint=point=>Array.isArray(point)&&point.length===3&&point.every(Number.isFinite);

export function validateHospitalPatientRoute(route=hospitalPatientRoute){
  return Array.isArray(route)&&route.length>=2&&route.every(finitePoint)&&route.every((point,index)=>index===0||Math.hypot(point[0]-route[index-1][0],point[2]-route[index-1][2])>.01);
}

function routeLengths(route){
  const segments=[];let total=0;
  for(let index=1;index<route.length;index++){
    const length=Math.hypot(route[index][0]-route[index-1][0],route[index][2]-route[index-1][2]);
    segments.push({from:route[index-1],to:route[index],start:total,length});total+=length;
  }
  return {segments,total};
}

export function sampleHospitalPatientRoute(elapsed,{route=hospitalPatientRoute,speed=1.05,arrivalWait=9,startWait=2,phaseOffset=0}={}){
  if(!validateHospitalPatientRoute(route)||!Number.isFinite(elapsed)||!Number.isFinite(speed)||speed<=0)throw new Error('Rota de paciente inválida.');
  const {segments,total}=routeLengths(route),travel=total/speed,cycle=startWait+travel+arrivalWait+travel;
  let time=((elapsed+phaseOffset)%cycle+cycle)%cycle,forward=true,distance=0,phase='walking';
  if(time<startWait){phase='waiting';distance=0;}
  else if((time-=startWait)<travel)distance=time*speed;
  else if((time-=travel)<arrivalWait){phase='waiting';distance=total;}
  else{time-=arrivalWait;forward=false;distance=total-time*speed;}
  distance=Math.max(0,Math.min(total,distance));
  const segment=segments.find(item=>distance<=item.start+item.length+1e-8)??segments.at(-1);
  const amount=segment.length?Math.max(0,Math.min(1,(distance-segment.start)/segment.length)):0;
  const position=segment.from.map((value,index)=>value+(segment.to[index]-value)*amount);
  const dx=(segment.to[0]-segment.from[0])*(forward?1:-1),dz=(segment.to[2]-segment.from[2])*(forward?1:-1);
  return {position,heading:Math.atan2(dx,dz),phase,forward,progress:total?distance/total:0};
}
