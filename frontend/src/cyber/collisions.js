import {Raycaster,Vector3} from 'three';
function visibleSolid(mesh){
  for(let p=mesh;p;p=p.parent){if(!p.visible||p.userData.dynamicCollider||p.userData.actor||p.userData.walkable||p.name.startsWith('DOOR_'))return false;}
  return !mesh.isSkinnedMesh&&!/^(ROAD_|MARK_|CLOCK_|SOLAR_|ENV_ARAP_Base|PLAZA_.*Ring)/.test(mesh.name);
}
export function createSolidIndex(scene){
  scene.updateMatrixWorld(true);const rows=[];
  scene.traverse(mesh=>{
    if(!mesh.isMesh||!visibleSolid(mesh))return;
    if(!mesh.geometry.boundingBox)mesh.geometry.computeBoundingBox();
    const box=mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld);
    if(box.max.y<=.45||box.min.y>2||box.max.x-box.min.x<.025||box.max.z-box.min.z<.025)return;
    rows.push({mesh,box});
  });return rows;
}
export function solidMovement(index,from,to,radius=.4){
  const direction=new Vector3(to.x-from.x,0,to.z-from.z),distance=direction.length();
  if(distance<1e-8)return to;direction.normalize();
  const meshes=index.filter(({box})=>box.min.x<=Math.max(from.x,to.x)+radius&&box.max.x>=Math.min(from.x,to.x)-radius&&box.min.z<=Math.max(from.z,to.z)+radius&&box.max.z>=Math.min(from.z,to.z)-radius).map(row=>row.mesh);
  if(!meshes.length)return to;
  const ray=new Raycaster(),perp=new Vector3(-direction.z,0,direction.x),origin=new Vector3();
  ray.far=distance+radius;
  for(const h of [.55,1,1.6])for(const side of [-.7,0,.7]){
    origin.set(from.x,(from.y??0)+h,from.z).addScaledVector(perp,side*radius);ray.set(origin,direction);
    if(ray.intersectObjects(meshes,false).length)return {...from};
  }
  return to;
}
export function footprintCollider(record,catalog){
  const source=catalog.find(a=>a.id===record.sourceId);if(!source)return null;
  const scale=record.height/source.dimensions[2],w=source.dimensions[0]*scale,d=source.dimensions[1]*scale,heading=record.rotation?.[1]??0;
  return {x:record.position[0],z:record.position[2],w:Math.abs(Math.cos(heading))*w+Math.abs(Math.sin(heading))*d,d:Math.abs(Math.sin(heading))*w+Math.abs(Math.cos(heading))*d};
}
