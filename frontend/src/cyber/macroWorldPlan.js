import {resolveAssetReferences} from '../config/deploymentConfig.js';
import planRaw from '../config/macroWorldPlan.json' with {type:'json'};
const plan=resolveAssetReferences(planRaw);

// Planning helpers only. The active game never imports this module.
export const macroWorldPlan = plan;
const epsilon = 1e-7;
const finitePoint = point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite);

export function footprint(record) {
  if (!finitePoint(record?.center) || !finitePoint(record?.size) || record.size.some(value => value <= 0)) {
    throw new TypeError('A footprint needs a finite XZ center and positive width/depth in meters.');
  }
  return {minX:record.center[0]-record.size[0]/2,maxX:record.center[0]+record.size[0]/2,
    minZ:record.center[1]-record.size[1]/2,maxZ:record.center[1]+record.size[1]/2};
}

export function containedBy(inner, outer, clearance=0) {
  return inner.minX >= outer.minX+clearance-epsilon && inner.maxX <= outer.maxX-clearance+epsilon
    && inner.minZ >= outer.minZ+clearance-epsilon && inner.maxZ <= outer.maxZ-clearance+epsilon;
}

export function footprintsOverlap(a, b, clearance=0) {
  return a.minX < b.maxX+clearance-epsilon && a.maxX > b.minX-clearance+epsilon
    && a.minZ < b.maxZ+clearance-epsilon && a.maxZ > b.minZ-clearance+epsilon;
}

export function polylineLengthMeters(points) {
  if (!Array.isArray(points) || points.length < 2 || !points.every(finitePoint)) {
    throw new TypeError('A route needs at least two finite XZ points.');
  }
  return points.slice(1).reduce((length, point, index) => length+Math.hypot(point[0]-points[index][0],point[1]-points[index][1]),0);
}

export function plannedJourney(route, mode=route.mode, config=plan) {
  const profile=config.movementProfiles[mode],speed=profile?.speedMetersPerSecond;
  if (!Number.isFinite(speed) || speed <= 0) throw new RangeError('A movement profile needs a positive speed in meters per second.');
  const dwell=route.plannedDwellSeconds??0;
  if (!Number.isFinite(dwell) || dwell < 0) throw new RangeError('Dwell must be a nonnegative number of seconds.');
  const meters=polylineLengthMeters(route.path),travelSeconds=meters/speed;
  return {meters,travelSeconds,dwellSeconds:dwell,totalSeconds:travelSeconds+dwell,
    minutes:(travelSeconds+dwell)/60,speedMetersPerSecond:speed,speedKmh:speed*3.6};
}

export function roadSegments(config=plan) {
  return config.roads.flatMap(road=>road.points.slice(1).map((to,index)=>({roadId:road.id,
    from:road.points[index],to,width:config.roadProfiles[road.profile].rightOfWayWidth})));
}

export function pointOnSegment(point, from, to, tolerance=epsilon) {
  if (![point,from,to].every(finitePoint)) return false;
  const dx=to[0]-from[0],dz=to[1]-from[1],length=Math.hypot(dx,dz);
  if (length <= tolerance) return Math.hypot(point[0]-from[0],point[1]-from[1]) <= tolerance;
  const projection=((point[0]-from[0])*dx+(point[1]-from[1])*dz)/(length*length);
  return projection >= -tolerance && projection <= 1+tolerance
    && Math.abs((point[0]-from[0])*dz-(point[1]-from[1])*dx)/length <= tolerance;
}

// Clip a centerline against an expanded rectangle. Expanding by half the
// right-of-way protects sidewalks and cycle lanes, not only asphalt centers.
export function roadIntersectsFootprint(segment, box, clearance=0) {
  const radius=segment.width/2+clearance;
  const bounds={minX:box.minX-radius,maxX:box.maxX+radius,minZ:box.minZ-radius,maxZ:box.maxZ+radius};
  let start=0,end=1;
  for (const [index,min,max] of [[0,bounds.minX,bounds.maxX],[1,bounds.minZ,bounds.maxZ]]) {
    const delta=segment.to[index]-segment.from[index];
    if (Math.abs(delta)<epsilon) {
      if (segment.from[index]<min || segment.from[index]>max) return false;
    } else {
      const one=(min-segment.from[index])/delta,two=(max-segment.from[index])/delta;
      start=Math.max(start,Math.min(one,two));end=Math.min(end,Math.max(one,two));
      if (start>end+epsilon) return false;
    }
  }
  return true;
}

// Include all authored junction points on each centerline so T-junctions and
// district approaches can be checked for real network connectivity.
export function roadNetwork(config=plan) {
  const segments=roadSegments(config),points=config.roads.flatMap(road=>road.points);
  const key=point=>point.map(value=>Math.round(value*1e6)/1e6).join(',');
  const nodes=new Map();
  const add=point=>{const id=key(point);if(!nodes.has(id))nodes.set(id,{point,neighbors:new Set()});return id;};
  for (const segment of segments) {
    const onLine=points.filter(point=>pointOnSegment(point,segment.from,segment.to));
    const unique=[...new Map(onLine.map(point=>[key(point),point])).values()]
      .sort((a,b)=>Math.hypot(a[0]-segment.from[0],a[1]-segment.from[1])-Math.hypot(b[0]-segment.from[0],b[1]-segment.from[1]));
    for(let index=1;index<unique.length;index++) {
      const a=add(unique[index-1]),b=add(unique[index]);
      nodes.get(a).neighbors.add(b);nodes.get(b).neighbors.add(a);
    }
  }
  return nodes;
}

export function routeUsesRoadNetwork(route, config=plan) {
  const segments=roadSegments(config);
  return route.path.slice(1).every((point,index)=>{
    const from=route.path[index];
    const matching=segments.filter(segment=>pointOnSegment(from,segment.from,segment.to)
      && pointOnSegment(point,segment.from,segment.to));
    if(matching.length)return true;
    // A route leg can span consecutive collinear road segments. Collect their
    // projected intervals and require coverage of the whole leg without gaps.
    const dx=point[0]-from[0],dz=point[1]-from[1],length2=dx*dx+dz*dz;
    if(length2<epsilon)return false;
    const projection=p=>((p[0]-from[0])*dx+(p[1]-from[1])*dz)/length2;
    const intervals=segments.filter(segment=>Math.abs((segment.from[0]-from[0])*dz-(segment.from[1]-from[1])*dx)<epsilon
      && Math.abs((segment.to[0]-from[0])*dz-(segment.to[1]-from[1])*dx)<epsilon)
      .map(segment=>[projection(segment.from),projection(segment.to)].sort((a,b)=>a-b))
      .sort((a,b)=>a[0]-b[0]);
    let covered=0;
    for(const [start,end]of intervals){if(start>covered+epsilon)break;if(end>=0)covered=Math.max(covered,end);if(covered>=1-epsilon)return true;}
    return false;
  });
}
