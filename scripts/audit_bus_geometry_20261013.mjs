import {readFileSync,writeFileSync} from 'node:fs';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {Box3,Vector3} from '../frontend/node_modules/three/build/three.module.js';
import {createBusRig} from '../frontend/src/cyber/busArticulation.js';
if(!globalThis.ProgressEvent)globalThis.ProgressEvent=class{constructor(type,options){this.type=type;Object.assign(this,options);}};
const records=[];
for(const filename of ['VEH_Bus_City_20261006','VEH_Bus_BRT_Interactive_20261009']){
  const bytes=readFileSync(new URL(`../frontend/public/assets/new-delivery/${filename}.glb`,import.meta.url));
  const length=bytes.readUInt32LE(12),document=JSON.parse(bytes.subarray(20,20+length).toString());
  const binary=bytes.subarray(28+length);
  // Inspect actual geometry only. No source asset or image is altered; embedded
  // binary is resolved locally, without requesting browser or network access.
  document.buffers[0].uri='data:application/octet-stream;base64,'+binary.toString('base64');
  document.images=[];document.textures=[];document.materials=[];
  for(const mesh of document.meshes)for(const primitive of mesh.primitives)delete primitive.material;
  const model=await new GLTFLoader().parseAsync(JSON.stringify(document),'');
  const rig=createBusRig(model.scene);rig.outer.updateMatrixWorld(true);
  const box=new Box3().setFromObject(rig.outer),positions={};
  rig.outer.traverse(node=>{if(/^(Door_|SteeringWheel|RearSection)/.test(node.name))positions[node.name]=node.getWorldPosition(new Vector3()).toArray();});
  records.push({filename,dimensions:box.getSize(new Vector3()).toArray(),bounds:{min:box.min.toArray(),max:box.max.toArray()},positions,wheels:rig.wheels.length});
}
writeFileSync(new URL('../reports/bus_geometry_20261013.json',import.meta.url),JSON.stringify(records,null,2));
console.log(JSON.stringify(records));
