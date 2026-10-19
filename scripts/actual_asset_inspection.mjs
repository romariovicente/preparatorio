import {readFileSync} from 'node:fs';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {Box3,Vector3} from '../frontend/node_modules/three/build/three.module.js';

// CPU-only loading keeps all vertex, joint and skin data while avoiding browser
// image APIs. The source buffer and files are never changed.
export async function loadTexturelessGLB(path) {
  const raw=readFileSync(path),jsonLength=raw.readUInt32LE(12);
  const doc=JSON.parse(raw.subarray(20,20+jsonLength));
  delete doc.images;delete doc.textures;delete doc.samplers;
  if(doc.materials)doc.materials=doc.materials.map(material=>({
    name:material.name,
    doubleSided:material.doubleSided,
    pbrMetallicRoughness:{baseColorFactor:material.pbrMetallicRoughness?.baseColorFactor??[1,1,1,1]},
  }));
  const json=Buffer.from(JSON.stringify(doc)),padding=Buffer.alloc((4-json.length%4)%4,32);
  const chunk=Buffer.concat([json,padding]),tail=raw.subarray(20+jsonLength);
  const buffer=Buffer.alloc(20+chunk.length+tail.length);
  raw.copy(buffer,0,0,12);buffer.writeUInt32LE(buffer.length,8);
  buffer.writeUInt32LE(chunk.length,12);buffer.writeUInt32LE(0x4e4f534a,16);
  chunk.copy(buffer,20);tail.copy(buffer,20+chunk.length);
  const gltf=await new GLTFLoader().parseAsync(buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength),'');
  synchronizeSkinnedBounds(gltf.scene);
  return gltf;
}

export function synchronizeSkinnedBounds(scene) {
  scene.updateMatrixWorld(true);
  scene.traverse(object=>{
    if(object.isSkinnedMesh){object.skeleton.update();object.computeBoundingBox();object.computeBoundingSphere();}
  });
  return new Box3().setFromObject(scene,true);
}

export function joint(scene,suffix) {
  let bone;
  scene.traverse(object=>{if(object.isBone&&object.name.replace(/[^a-z0-9]/gi,'').toLowerCase().endsWith(suffix.toLowerCase()))bone=object;});
  if(!bone)throw new Error(`Missing real rig joint: ${suffix}`);
  return bone.getWorldPosition(new Vector3());
}

export function localTransformSnapshot(scene) {
  const transforms=[];
  scene.traverse(object=>transforms.push({uuid:object.uuid,name:object.name,position:object.position.toArray(),quaternion:object.quaternion.toArray(),scale:object.scale.toArray()}));
  return transforms;
}

export function finiteDeformedVertices(scene) {
  const point=new Vector3();let count=0;
  scene.traverse(object=>{
    if(!object.isMesh)return;
    const position=object.geometry.attributes.position;
    for(let index=0;index<position.count;index++){
      object.getVertexPosition(index,point).applyMatrix4(object.matrixWorld);
      if(!point.toArray().every(Number.isFinite))throw new Error(`Nonfinite vertex in ${object.name}:${index}`);
      count++;
    }
  });
  return count;
}
