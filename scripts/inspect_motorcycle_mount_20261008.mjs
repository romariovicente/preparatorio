import {writeFileSync} from 'node:fs';
import {Box3,Raycaster,Vector3} from '../frontend/node_modules/three/build/three.module.js';
import {createMotorcycleRig} from '../frontend/src/cyber/motorcycleArticulation.js';
import {loadTexturelessGLB} from './actual_asset_inspection.mjs';

const path=new URL('../frontend/public/assets/vehicles/VEH_Kawasaki_Interactive_20261007.glb',import.meta.url);
const {scene}=await loadTexturelessGLB(path),rig=createMotorcycleRig(scene,1.3);
rig.outer.updateMatrixWorld(true);
const meshes=[],points=[],vertex=new Vector3();
rig.outer.traverse(object=>{
  if(!object.isMesh)return;
  const position=object.geometry.attributes.position;
  const box=new Box3();
  for(let index=0;index<position.count;index++){
    vertex.fromBufferAttribute(position,index).applyMatrix4(object.matrixWorld);
    box.expandByPoint(vertex);
    points.push({part:object.parent.name,material:object.material?.name,point:vertex.toArray()});
  }
  meshes.push({name:object.name,material:object.material?.name,vertices:position.count,bounds:[box.min.toArray(),box.max.toArray()]});
});
const bounds=new Box3().setFromObject(rig.outer,true);
const ray=new Raycaster(),seatSamples=[];
for(const z of [-.5,-.45,-.4,-.35,-.3]){
  ray.set(new Vector3(0,2,z),new Vector3(0,-1,0));
  const hit=ray.intersectObject(rig.outer,true)[0];
  seatSamples.push({z,point:hit?.point.toArray(),material:hit?.object.material?.name});
}
const steeringPoints=points.filter(row=>row.part==='Steering_F');
const nearest=target=>steeringPoints.reduce((best,row)=>{
  const distance=new Vector3(...row.point).distanceToSquared(new Vector3(...target));
  return distance<best.distance?{point:row.point,distance}:best;
},{distance:Infinity}).point;
const summary={date:'2026-10-08',normalization:'createMotorcycleRig with exact CPU vertex bounds, height=1.3m, +Z front',bounds:[bounds.min.toArray(),bounds.max.toArray()],seatSamples,recommendedActorMount:[0,.94,-.4],gripApproximations:{positiveX:nearest([.33,1.1,.4]),negativeX:nearest([-.35,1.1,.51]),method:'Nearest real Steering_F vertices to handles identified in geometry side view; approximate palm locations, not rigged grip sockets'},meshes};
writeFileSync(new URL('../reports/motorcycle_mount_validation_20261008.json',import.meta.url),JSON.stringify(summary,null,2)+'\n');
if(process.argv.includes('--vertices'))writeFileSync(new URL('../reports/motorcycle_mount_vertices_20261008.json',import.meta.url),JSON.stringify({summary,points}));
console.log(JSON.stringify(summary,null,2));
