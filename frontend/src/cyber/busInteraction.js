import {resolveAssetReferences} from '../config/deploymentConfig.js';
import deliveryConfigRaw from '../config/newDeliveryWorld.json' with {type:'json'};
const deliveryConfig=resolveAssetReferences(deliveryConfigRaw);
import buildingConfig from '../config/buildingDoors.json' with {type:'json'};

export const BUS_IDS=['bus','bus-brt'];
export const BUS_BRT_ROUTE={id:'bus-brt',label:'Ônibus articulado · Terminal PREPARATÓRIO',speed:8,dwell:12,cornerRadius:9,
  points:[{x:-106,z:-49},{x:-106,z:-5},{x:-102,z:15},{x:-102,z:35},{x:-55,z:35},{x:0,z:35},
    {x:10,z:35},{x:25,z:36.5},{x:75,z:36.5},{x:90,z:35},{x:105,z:35},
    {x:111.2,z:20},{x:111.2,z:-18},{x:105,z:-35},{x:105,z:-45},{x:105,z:-99},{x:-106,z:-99},{x:-106,z:-89}],
  stops:[{id:'terminal',label:'Terminal · acesso pela Via Oeste',position:{x:-106,y:0,z:-49}},
    {id:'hospital',label:'Hospital',position:{x:105,y:0,z:-45}},
    {id:'station',label:'Estação Arapiraca',position:{x:-106,y:0,z:-89}},
    {id:'store',label:'Loja',position:{x:-55,y:0,z:35}},
    {id:'plaza',label:'Praça PREP',position:{x:0,y:0,z:35}}]};
export const BUS_ROUTES={bus:deliveryConfig.routeOverrides.bus,'bus-brt':BUS_BRT_ROUTE};
export const BUS_DEFINITIONS={
  bus:{id:'bus',assetId:'VEH_Bus_City_20261006',label:'Ônibus circular PREPARATÓRIO',width:2.9,length:12.41,wheelbase:6.25,wheelRadius:.49,speed:10,
    driverSeat:[.65,1.05,4.8],passengerSeat:[.7,1.1,1.1],door:[-1.8,0,4.3]},
  'bus-brt':{id:'bus-brt',assetId:'VEH_Bus_BRT_20261006',label:'Ônibus articulado PREPARATÓRIO',width:3.56,length:23.22,wheelbase:5.27,wheelRadius:.524,speed:8,
    driverSeat:[.65,1.05,9.75],passengerSeat:[-.65,1.1,6],door:[1.95,0,6.325],articulationPivot:[.03696382,0,.35870849],rearWheelbase:7.5,articulationLimit:25*Math.PI/180},
};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const distance=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const angleDifference=(from,to)=>Math.atan2(Math.sin(to-from),Math.cos(to-from));
const routeCache=new WeakMap();
const stopAt=(route,p)=>route.stops.find(stop=>distance(stop.position,p)<.01);
const defaultObstacles=[...buildingConfig.map(b=>({id:b.id,x:b.center[0],z:b.center[2],w:b.width,d:b.depth})),...deliveryConfig.colliders];
const defaultBounds={minX:-118,maxX:118,minZ:-118,maxZ:118};

// Round only road junctions. Authored stop positions remain exact so boarding
// and the timetable share the same physical location.
export function buildBusPath(route){
  if(routeCache.has(route))return routeCache.get(route);
  const points=[];
  for(let index=0;index<route.points.length;index++){
    const p=route.points[index],a=route.points[(index+route.points.length-1)%route.points.length],b=route.points[(index+1)%route.points.length];
    const incoming=distance(a,p),outgoing=distance(p,b),ux=(p.x-a.x)/incoming,uz=(p.z-a.z)/incoming,vx=(b.x-p.x)/outgoing,vz=(b.z-p.z)/outgoing;
    const turn=ux*vx+uz*vz;
    if(stopAt(route,p)||turn>.999||turn<-.95||!incoming||!outgoing){points.push({...p,stop:stopAt(route,p)});continue;}
    const radius=Math.min(route.cornerRadius??9,incoming*.35,outgoing*.35),start={x:p.x-ux*radius,z:p.z-uz*radius},end={x:p.x+vx*radius,z:p.z+vz*radius};
    for(let step=0;step<=12;step++){
      const t=step/12,q=1-t;
      points.push({x:q*q*start.x+2*q*t*p.x+t*t*end.x,z:q*q*start.z+2*q*t*p.z+t*t*end.z,
        tangent:Math.atan2(q*(p.x-start.x)+t*(end.x-p.x),q*(p.z-start.z)+t*(end.z-p.z))});
    }
  }
  let cursor=0;
  const legs=points.map((point,index)=>{
    const next=points[(index+1)%points.length],length=distance(point,next),heading=Math.atan2(next.x-point.x,next.z-point.z),dwell=point.stop?route.dwell:0;
    const leg={point,next,length,heading,dwell,travel:length/route.speed,start:cursor,index};cursor+=dwell+leg.travel;return leg;
  });
  const result={points,legs,cycle:cursor};routeCache.set(route,result);return result;
}

export function sampleBusRoute(route,elapsed=0){
  const path=buildBusPath(route),time=((elapsed%path.cycle)+path.cycle)%path.cycle;
  const leg=path.legs.find(item=>time<item.start+item.dwell+item.travel)??path.legs.at(-1);
  const nextStop=Array.from({length:path.legs.length},(_,offset)=>path.legs[(leg.index+offset+1)%path.legs.length]).find(item=>item.point.stop)?.point.stop;
  const local=time-leg.start;
  if(local<leg.dwell)return {x:leg.point.x,y:0,z:leg.point.z,heading:leg.heading,stopped:true,speed:0,doorOpen:true,
    stopId:leg.point.stop.id,stopLabel:leg.point.stop.label,nextStop:nextStop?.label??'',remaining:Math.ceil(leg.dwell-local),routeTime:time};
  const fraction=leg.travel?clamp((local-leg.dwell)/leg.travel,0,1):0;
  const headingStart=leg.point.tangent??leg.heading,headingEnd=leg.next.tangent??leg.heading;
  let untilStop=leg.travel-(local-leg.dwell);
  for(let count=1;count<path.legs.length;count++){
    const following=path.legs[(leg.index+count)%path.legs.length];if(following.point.stop)break;untilStop+=following.travel;
  }
  return {x:leg.point.x+(leg.next.x-leg.point.x)*fraction,y:0,z:leg.point.z+(leg.next.z-leg.point.z)*fraction,
    heading:headingStart+angleDifference(headingStart,headingEnd)*fraction,stopped:false,speed:route.speed,doorOpen:false,
    stopId:null,stopLabel:'Em movimento',nextStop:nextStop?.label??'',remaining:Math.ceil(untilStop),routeTime:time};
}
export function createLiveBuses(elapsed=0){
  return Object.fromEntries(BUS_IDS.map(id=>[id,{id,label:BUS_DEFINITIONS[id].label,...sampleBusRoute(BUS_ROUTES[id],elapsed),control:'npc',engineOn:true,routeOffset:0,wheelAngle:0,steeringAngle:0,articulationAngle:0}]));
}
export function sampleLiveBus(state,id='bus'){
  if(!BUS_DEFINITIONS[id])return null;
  const bus=state.liveBuses?.[id]??createLiveBuses(state.elapsed??0)[id];
  return bus.control==='npc'&&!bus.trafficWaiting?{...bus,...sampleBusRoute(BUS_ROUTES[id],(state.elapsed??0)+(bus.routeOffset??0))}:{...bus};
}
export function busLocalToWorld(bus,local){
  const c=Math.cos(bus.heading),s=Math.sin(bus.heading);
  return {x:bus.x+local[0]*c+local[2]*s,y:(bus.y??0)+local[1],z:bus.z-local[0]*s+local[2]*c};
}
export function busSeatPosition(bus,role='passenger'){
  return busLocalToWorld(bus,BUS_DEFINITIONS[bus.id][role==='driver'?'driverSeat':'passengerSeat']);
}
export function busDoorPosition(bus){return busLocalToWorld(bus,BUS_DEFINITIONS[bus.id].door);}
export function nearestBus(state,maxDistance=7){
  return BUS_IDS.map(id=>sampleLiveBus(state,id)).map(bus=>({...bus,distance:distance(state.position,busDoorPosition(bus))}))
    .filter(bus=>bus.distance<=maxDistance).sort((a,b)=>a.distance-b.distance)[0]??null;
}
export function canBoardBus(state,bus,maxDistance=7){
  return Boolean(bus&&state.mode==='foot'&&!state.sitting&&!state.elevator&&!state.jump&&!state.carEntry&&bus.stopped&&bus.doorOpen&&Math.abs((state.position.y??0)-(bus.y??0))<2&&distance(state.position,busDoorPosition(bus))<=maxDistance);
}
export function busFootprintPolygons(bus){
  const definition=BUS_DEFINITIONS[bus.id],{width,length}=definition;
  const joint=clamp(bus.articulationAngle??0,-(definition.articulationLimit??0),definition.articulationLimit??0);
  const pivot=definition.articulationPivot??[0,0,0],c=Math.cos(joint),s=Math.sin(joint);
  return [false,true].map(rear=>{
    const low=rear?-length/2:pivot[2],high=rear?pivot[2]:length/2;
    return [[-width/2,low],[width/2,low],[width/2,high],[-width/2,high]].map(([x,z])=>{
      const point=rear?[pivot[0]+(x-pivot[0])*c+(z-pivot[2])*s,0,pivot[2]-(x-pivot[0])*s+(z-pivot[2])*c]:[x,0,z];
      const world=busLocalToWorld(bus,point);return [world.x,world.z];
    });
  });
}
export function busFootprint(bus){
  const corners=busFootprintPolygons(bus).flat().map(([x,z])=>({x,z}));
  const minX=Math.min(...corners.map(p=>p.x)),maxX=Math.max(...corners.map(p=>p.x)),minZ=Math.min(...corners.map(p=>p.z)),maxZ=Math.max(...corners.map(p=>p.z));
  return {id:bus.id,x:(minX+maxX)/2,z:(minZ+maxZ)/2,w:maxX-minX,d:maxZ-minZ};
}
export function busPositionBlocked(bus,obstacles=defaultObstacles,bounds=defaultBounds){
  const box=busFootprint(bus);
  return box.x-box.w/2<bounds.minX||box.x+box.w/2>bounds.maxX||box.z-box.d/2<bounds.minZ||box.z+box.d/2>bounds.maxZ||
    obstacles.some(o=>o.id!==bus.id&&Math.abs(box.x-o.x)<(box.w+o.w)/2&&Math.abs(box.z-o.z)<(box.d+o.d)/2);
}
// Walking collisions use an axis-aligned bus box. Clear that same box, including
// the actor radius, even when the bus is parked at an angle to the road.
export function busExitPosition(bus,obstacles=defaultObstacles,radius=.4,bounds=defaultBounds){
  const definition=BUS_DEFINITIONS[bus.id],box=busFootprint(bus),side=Math.sign(definition.door[0])||1;
  const nx=side*Math.cos(bus.heading),nz=-side*Math.sin(bus.heading),margin=radius+.2;
  for(const shift of [0,-1.25,1.25,-2.5,2.5]){
    const door=busLocalToWorld(bus,[definition.door[0],0,definition.door[2]+shift]);
    const tx=Math.abs(nx)>.00001?(box.w/2+margin-Math.sign(nx)*(door.x-box.x))/Math.abs(nx):Infinity;
    const tz=Math.abs(nz)>.00001?(box.d/2+margin-Math.sign(nz)*(door.z-box.z))/Math.abs(nz):Infinity;
    for(const extra of [0,.75,1.5,3]){
      const step=Math.max(.65,Math.min(tx,tz))+extra,point={x:door.x+nx*step,y:0,z:door.z+nz*step};
      if(point.x-radius<bounds.minX||point.x+radius>bounds.maxX||point.z-radius<bounds.minZ||point.z+radius>bounds.maxZ)continue;
      if([box,...obstacles.filter(o=>o.id!==bus.id)].some(o=>Math.abs(point.x-o.x)<o.w/2+radius+.05&&Math.abs(point.z-o.z)<o.d/2+radius+.05))continue;
      return point;
    }
  }
  return null;
}
export function busMotion(heading,keys,delta,id='bus'){
  const definition=BUS_DEFINITIONS[id],dt=clamp(Number.isFinite(delta)?delta:0,0,.05);
  const throttle=(keys.w?1:0)-(keys.s?1:0),steeringAngle=((keys.a?1:0)-(keys.d?1:0))*.48;
  const speed=throttle*(throttle<0?definition.speed*.35:definition.speed),yaw=heading+speed/definition.wheelbase*Math.tan(steeringAngle)*dt;
  return {heading:yaw,steeringAngle,speed,dx:Math.sin(yaw)*speed*dt,dz:Math.cos(yaw)*speed*dt};
}
function animateMotion(previous,next,delta){
  const definition=BUS_DEFINITIONS[next.id],travel=distance(previous,next),yaw=angleDifference(previous.heading,next.heading),dt=Math.max(.0001,Number.isFinite(delta)?delta:.05);
  const signedTravel=(next.x-previous.x)*Math.sin(next.heading)+(next.z-previous.z)*Math.cos(next.heading);
  const steering=next.control==='player'?next.steeringAngle:travel>.00001?clamp(Math.atan(yaw*definition.wheelbase/travel),-.48,.48):0;
  const articulation=next.id==='bus-brt'?clamp((previous.articulationAngle??0)-yaw+(signedTravel/definition.rearWheelbase)*Math.sin(-(previous.articulationAngle??0)),-definition.articulationLimit,definition.articulationLimit):0;
  return {...next,wheelAngle:(previous.wheelAngle??0)+Math.sign(signedTravel)*travel/definition.wheelRadius,steeringAngle:steering,articulationAngle:articulation,
    speed:next.stopped?0:Math.sign(signedTravel)*travel/dt};
}
export function moveLiveBus(state,id,position,heading,steeringAngle=0,delta=.05){
  const previous=sampleLiveBus(state,id),travel=distance(previous,position);
  const bus=animateMotion(previous,{...previous,x:position.x,y:0,z:position.z,heading,steeringAngle,stopped:travel<.00001,doorOpen:false,stopId:null,stopLabel:travel<.00001?'Parado pelo motorista':'Condução manual'},delta);
  return {...state,liveBuses:{...state.liveBuses,[id]:bus},position:busSeatPosition(bus,state.busControls?.role),heading:bus.heading};
}
function closestRoutePoint(route,position){
  const path=buildBusPath(route);let best=null;
  for(const leg of path.legs){
    const dx=leg.next.x-leg.point.x,dz=leg.next.z-leg.point.z,lengthSq=dx*dx+dz*dz;
    const fraction=lengthSq?clamp(((position.x-leg.point.x)*dx+(position.z-leg.point.z)*dz)/lengthSq,0,1):0;
    const point={x:leg.point.x+dx*fraction,z:leg.point.z+dz*fraction},gap=distance(position,point);
    if(!best||gap<best.distance){
      const routeTime=leg.start+leg.dwell+leg.travel*fraction;
      best={...point,heading:sampleBusRoute(route,routeTime).heading,routeTime,distance:gap};
    }
  }
  return best;
}
export function returnBusToRoute(state,id){
  const bus=sampleLiveBus(state,id),target=closestRoutePoint(BUS_ROUTES[id],bus);
  return {...state,liveBuses:{...state.liveBuses,[id]:{...bus,control:'rejoin',engineOn:true,doorOpen:false,rejoinTarget:target,stopLabel:'Retornando à linha',remaining:Math.ceil(target.distance/BUS_ROUTES[id].speed)}}};
}
function busPolygonsTooClose(a,b,clearance=.6){
  return busFootprintPolygons(a).some(first=>busFootprintPolygons(b).some(second=>{
    for(const polygon of [first,second])for(let index=0;index<polygon.length;index++){
      const point=polygon[index],next=polygon[(index+1)%polygon.length],nx=point[1]-next[1],nz=next[0]-point[0],margin=clearance*Math.hypot(nx,nz);
      const one=first.map(p=>p[0]*nx+p[1]*nz),two=second.map(p=>p[0]*nx+p[1]*nz);
      if(Math.max(...one)+margin<=Math.min(...two)||Math.max(...two)+margin<=Math.min(...one))return false;
    }
    return true;
  }));
}
function busSweepBlocked(previous,next,blocked){
  // Check the swept turn as well as the final articulated pose. A long frame
  // or a bus rotating back onto its line must not pass through a parked bus.
  const yaw=angleDifference(previous.heading,next.heading),joint=(next.articulationAngle??0)-(previous.articulationAngle??0);
  const steps=Math.max(1,Math.ceil(distance(previous,next)/.25),Math.ceil(Math.abs(yaw)/.03),Math.ceil(Math.abs(joint)/.03));
  for(let step=1;step<=steps;step++){
    const t=step/steps,bus={...next,x:previous.x+(next.x-previous.x)*t,z:previous.z+(next.z-previous.z)*t,
      heading:previous.heading+yaw*t,articulationAngle:(previous.articulationAngle??0)+joint*t};
    if(blocked(bus))return true;
  }
  return false;
}
function busTrafficBlocked(previous,next,others){
  // A player may park inside the preferred gap without touching the body.
  // Preserve physical separation while allowing that tight pair to clear.
  const checks=others.map(other=>({other,clearance:busPolygonsTooClose(previous,other)?0:.6}));
  return busSweepBlocked(previous,next,bus=>checks.some(({other,clearance})=>busPolygonsTooClose(bus,other,clearance)));
}
export function tickLiveBuses(state,delta,elapsed,obstacles=defaultObstacles){
  const liveBuses={};
  for(const id of BUS_IDS){
    const previous=sampleLiveBus(state,id);let next=previous;
    if(previous.control==='npc')next={...previous,...sampleBusRoute(BUS_ROUTES[id],elapsed+(previous.routeOffset??0)),trafficWaiting:false};
    else if(previous.control==='rejoin'&&!previous.returnBlocked){
      const target=previous.rejoinTarget,gap=distance(previous,target),desired=gap>.02?Math.atan2(target.x-previous.x,target.z-previous.z):target.heading;
      const yaw=angleDifference(previous.heading,desired),heading=previous.heading+clamp(yaw,-delta*.8,delta*.8);
      const step=Math.abs(yaw)<.5?Math.min(gap,BUS_ROUTES[id].speed*delta):0;
      next={...previous,x:previous.x+(target.x-previous.x)/(gap||1)*step,z:previous.z+(target.z-previous.z)/(gap||1)*step,heading,stopped:step===0,returnBlocked:false,trafficWaiting:false,doorOpen:false,engineOn:true,stopLabel:'Retornando à linha'};
      if(gap<.02&&Math.abs(angleDifference(heading,target.heading))<.03){
        next={...next,...sampleBusRoute(BUS_ROUTES[id],target.routeTime),control:'npc',routeOffset:target.routeTime-elapsed,rejoinTarget:null};
      }
    }
    if(previous.control==='player'){liveBuses[id]=next;continue;}
    next=animateMotion(previous,next,delta);
    if(previous.control==='rejoin'&&!previous.returnBlocked&&busSweepBlocked(previous,next,bus=>busPositionBlocked(bus,obstacles))){
      liveBuses[id]={...previous,stopped:true,speed:0,engineOn:false,doorOpen:true,trafficWaiting:false,returnBlocked:true,stopLabel:'Retorno bloqueado · reposicione o ônibus'};
      continue;
    }
    const others=BUS_IDS.filter(other=>other!==id).map(other=>liveBuses[other]??sampleLiveBus(state,other));
    if(busTrafficBlocked(previous,next,others)){
      // Pause this vehicle's route clock instead of letting it catch up by
      // teleporting after the lead vehicle clears the stop.
      next={...previous,stopped:true,speed:0,trafficWaiting:true,
        routeOffset:previous.control==='npc'?(previous.routeOffset??0)-delta:previous.routeOffset,
        stopLabel:previous.stopId?previous.stopLabel:'Aguardando o ônibus à frente'};
    }
    liveBuses[id]=next;
  }
  return liveBuses;
}
