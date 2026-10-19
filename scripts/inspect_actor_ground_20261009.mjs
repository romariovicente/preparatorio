import {writeFileSync} from 'node:fs';
import {Raycaster,Vector3} from '../frontend/node_modules/three/build/three.module.js';
import {loadTexturelessGLB} from './actual_asset_inspection.mjs';

const {scene}=await loadTexturelessGLB(new URL('../frontend/public/assets/cyber/ENV_Arapiraca_RealMaterials_v3_20261005.glb',import.meta.url));
scene.updateMatrixWorld(true);
const meshes=[],currentSurfaces=[];
scene.traverse(o=>{
  if(!o.isMesh)return;
  meshes.push(o);
  if(o.userData.walkable||o.name.startsWith('ENV_ARAP_Base')||o.name.startsWith('ROAD_')&&!/white|Centre|MARK/i.test(o.name)||o.name.startsWith('UNDERGROUND_Floor'))currentSurfaces.push(o);
});
const ray=new Raycaster(),results=[];
for(const [x,z] of [[0,25],[-.68,23.93],[84.3,-23.24],[21.53,60.01]]){
  ray.set(new Vector3(x,2,z),new Vector3(0,-1,0));
  const describe=hit=>({name:hit.object.name,point:hit.point.toArray(),visible:hit.object.visible,walkable:hit.object.userData.walkable??false});
  results.push({x,z,current:ray.intersectObjects(currentSurfaces,false).slice(0,8).map(describe),all:ray.intersectObjects(meshes,false).slice(0,8).map(describe)});
}
writeFileSync(new URL('../reports/actor_ground_diagnostic_20261009.json',import.meta.url),JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results,null,2));
