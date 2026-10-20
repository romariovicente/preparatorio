import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3,Group,Matrix3,Matrix4,Quaternion,Vector3} from '../frontend/node_modules/three/build/three.module.js';
import {loadTexturelessGLB,finiteDeformedVertices,localTransformSnapshot} from './actual_asset_inspection.mjs';
import {animateCarRig,createCarRig} from '../frontend/src/cyber/carArticulation.js';
import {resolveCarSource} from '../frontend/src/cyber/carInteraction.js';
import {activeWorldPlacements} from '../frontend/src/cyber/vehiclePlacements.js';
import {createSolidIndex} from '../frontend/src/cyber/collisions.js';
import catalog from '../frontend/src/config/suppliedAssets.json' with {type:'json'};
import world from '../frontend/src/config/realisticWorldManifest.json' with {type:'json'};

const root=new URL('../',import.meta.url);
const derivative=new URL('frontend/public/assets/additions20261019/VEH_Mercedes_AMG_One_Interactive_20261019.glb',root);
const sourcePath='C:/Users/Senac/Downloads/NÃO APAGUE ESSA PASTA Sou Aluno Programador no GitHub, pois utilizo pra programar no GitHub e no VScode/Tudo pra colocar no jogo/Veiculos/Transparency Mercedes AMG One/transparency_mercedes_amg_one.glb';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const document=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
const raw=readFileSync(derivative),doc=document(raw),original=readFileSync(sourcePath),sourceDoc=document(original);
const source=catalog.find(asset=>asset.id==='SUP_transparency_mercedes_amg_one');
assert.equal(hash(original),source.sourceSha256,'original Downloads file must remain intact');
assert.equal(doc.scenes.length,1,'only the independent AMG scene may be exported');
assert.ok(raw.length<25_000_000,'the derivative must not contain the full master world');
function inventory(json){
  const result={triangles:0,positions:0,normals:0,uv:0,meshInstances:0};
  for(const node of json.nodes){
    if(!Number.isInteger(node.mesh))continue;
    result.meshInstances++;
    for(const primitive of json.meshes[node.mesh].primitives){
      assert.equal(primitive.mode??4,4);
      result.triangles+=json.accessors[primitive.indices].count/3;
      result.positions+=json.accessors[primitive.attributes.POSITION].count;
      if(primitive.attributes.NORMAL!==undefined)result.normals+=json.accessors[primitive.attributes.NORMAL].count;
      if(primitive.attributes.TEXCOORD_0!==undefined)result.uv+=json.accessors[primitive.attributes.TEXCOORD_0].count;
    }
  }
  return result;
}
const exportedInventory=inventory(doc),sourceInventory=inventory(sourceDoc);
assert.equal(exportedInventory.triangles,sourceInventory.triangles);
assert.equal(exportedInventory.meshInstances,sourceInventory.meshInstances);
assert.equal(exportedInventory.normals,exportedInventory.positions,'every exported position retains its normal');
assert.ok(exportedInventory.uv>=sourceInventory.uv,'UV seam splitting may add vertices but cannot remove UV coverage');
const opaque=doc.materials.filter(material=>/^AMGO19_amgprojone_(paint|carbon)_opaque$/.test(material.name));
assert.equal(opaque.length,2);
assert.ok(opaque.every(material=>(material.pbrMetallicRoughness?.baseColorFactor?.[3]??1)===1&&material.alphaMode!=='BLEND'));
assert.ok(doc.materials.some(material=>/clearglass/.test(material.name)&&material.alphaMode==='BLEND'),'actual windows retain source transparency');
const {scene}=await loadTexturelessGLB(derivative);
const {scene:originalScene}=await loadTexturelessGLB(sourcePath);
const originalBox=new Box3().setFromObject(originalScene),originalSize=originalBox.getSize(new Vector3()),originalCenter=originalBox.getCenter(new Vector3());
const normalize=new Matrix4().makeScale(1.26/originalSize.y,1.26/originalSize.y,1.26/originalSize.y).multiply(new Matrix4().makeTranslation(-originalCenter.x,-originalBox.min.y,-originalCenter.z));
const sourceMeshes=new Map();originalScene.traverse(mesh=>{if(mesh.isMesh)sourceMeshes.set(mesh.name,mesh);});
const permutations=[[0,1,2],[1,2,0],[2,0,1],[0,2,1],[2,1,0],[1,0,2]],tolerance=1e-4;
let matchedTriangles=0,maxPositionError=0,maxUvError=0,maxNormalError=0,uvCorners=0;
const point=new Vector3(),normal=new Vector3();
function positions(mesh,matrix){
  const geometry=mesh.geometry,index=geometry.index,count=index?.count??geometry.attributes.position.count;
  const values=new Float64Array(count*3);
  for(let corner=0;corner<count;corner++){
    point.fromBufferAttribute(geometry.attributes.position,index?index.getX(corner):corner).applyMatrix4(matrix);
    point.toArray(values,corner*3);
  }
  return values;
}
function permutationFor(a,ai,b,bi){
  return permutations.find(order=>order.every((corner,index)=>Math.hypot(a[ai+index*3]-b[bi+corner*3],a[ai+index*3+1]-b[bi+corner*3+1],a[ai+index*3+2]-b[bi+corner*3+2])<=tolerance));
}
function bucket(values,face){const at=face*9;return [0,1,2].map(axis=>Math.floor((values[at+axis]+values[at+axis+3]+values[at+axis+6])/3/.001));}
scene.traverse(mesh=>{
  if(!mesh.isMesh)return;
  const sourceName=mesh.userData.source_object_name?.replace(/\.\d+$/,'');
  const sourceMesh=sourceMeshes.get(sourceName);
  assert.ok(sourceMesh,`exported component must identify its original: ${sourceName}`);
  const a=positions(mesh,mesh.matrixWorld),b=positions(sourceMesh,normalize.clone().multiply(sourceMesh.matrixWorld));
  assert.equal(a.length,b.length,`${sourceName}: triangle corners unchanged`);
  const count=a.length/9,assignments=new Map(),used=new Set(),unmatched=[];
  for(let face=0;face<count;face++){
    const order=permutationFor(a,face*9,b,face*9);
    if(order){assignments.set(face,[face,order]);used.add(face);}else unmatched.push(face);
  }
  if(unmatched.length){
    const buckets=new Map();
    for(let face=0;face<count;face++)if(!used.has(face)){
      const key=bucket(b,face).join(',');if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(face);
    }
    for(const face of unmatched){
      const cell=bucket(a,face);let found=false;
      for(let x=-1;x<=1&&!found;x++)for(let y=-1;y<=1&&!found;y++)for(let z=-1;z<=1&&!found;z++){
        for(const other of buckets.get([cell[0]+x,cell[1]+y,cell[2]+z].join(','))??[]){
          if(used.has(other))continue;
          const order=permutationFor(a,face*9,b,other*9);
          if(order){assignments.set(face,[other,order]);used.add(other);found=true;break;}
        }
      }
      assert.ok(found,`${sourceName}: transformed triangle ${face} must match original within ${tolerance}m`);
    }
  }
  const ag=mesh.geometry,bg=sourceMesh.geometry,an=new Matrix3().getNormalMatrix(mesh.matrixWorld),bn=new Matrix3().getNormalMatrix(normalize.clone().multiply(sourceMesh.matrixWorld));
  assert.equal(Boolean(ag.attributes.uv),Boolean(bg.attributes.uv),`${sourceName}: actual UV coverage preserved`);
  assert.ok(ag.attributes.normal&&bg.attributes.normal);
  for(const [face,[other,order]]of assignments){
    matchedTriangles++;
    for(let corner=0;corner<3;corner++){
      const ai=face*3+corner,bi=other*3+order[corner],av=ag.index?ag.index.getX(ai):ai,bv=bg.index?bg.index.getX(bi):bi;
      maxPositionError=Math.max(maxPositionError,Math.hypot(a[ai*3]-b[bi*3],a[ai*3+1]-b[bi*3+1],a[ai*3+2]-b[bi*3+2]));
      if(ag.attributes.uv){uvCorners++;maxUvError=Math.max(maxUvError,Math.abs(ag.attributes.uv.getX(av)-bg.attributes.uv.getX(bv)),Math.abs(ag.attributes.uv.getY(av)-bg.attributes.uv.getY(bv)));}
      point.fromBufferAttribute(ag.attributes.normal,av).applyNormalMatrix(an);
      normal.fromBufferAttribute(bg.attributes.normal,bv).applyNormalMatrix(bn);
      maxNormalError=Math.max(maxNormalError,point.distanceTo(normal));
    }
  }
});
assert.equal(matchedTriangles,sourceInventory.triangles);
assert.ok(maxPositionError<=tolerance);
assert.ok(maxUvError<=1e-4,'actual face-corner UV values must remain intact');
assert.ok(maxNormalError<=.001,'normal directions remain within export precision');
const originalTransforms=localTransformSnapshot(scene),vertices=finiteDeformedVertices(scene);
const car=resolveCarSource('plaza-amg-one');
const rig=createCarRig(scene,car.asset.height,car.asset);
rig.outer.updateMatrixWorld(true);
assert.equal(rig.wheels.length,4);assert.equal(rig.doors.length,2);assert.equal(rig.windows.length,2);
const box=new Box3().setFromObject(rig.outer),size=box.getSize(new Vector3());
assert.ok(Math.abs(box.min.y)<1e-5);assert.ok(Math.abs(size.y-1.26)<1e-5);
assert.ok(Math.abs(car.w-size.x)<.01&&Math.abs(car.d-size.z)<.01,'static and moving footprint agree with the derivative within one centimetre');
const dynamic=new Group();dynamic.userData.dynamicCollider=true;dynamic.add(rig.outer);
assert.equal(createSolidIndex(dynamic).length,0,'interactive geometry relies on explicit footprints and cannot leave a stale second collision');
const centers=rig.wheels.map(wheel=>wheel.node.getWorldPosition(new Vector3()));
const doorCenters=rig.doors.map(door=>new Box3().setFromObject(door.node).getCenter(new Vector3()));
const fixed=[];
rig.outer.traverse(node=>{if(node.isMesh&&/windshield/i.test(node.userData.source_component_lineage??''))fixed.push([node,node.matrixWorld.clone()]);});
assert.ok(fixed.length,'the actual windshield must remain fixed');
animateCarRig(rig,{wheelAngle:Math.PI/2,steeringAngle:.4,doorOpen:true,windowsOpen:true},1);
rig.outer.updateMatrixWorld(true);
for(let index=0;index<rig.wheels.length;index++){
  const wheel=rig.wheels[index];
  assert.ok(wheel.node.getWorldPosition(new Vector3()).distanceTo(centers[index])<1e-5,'rotating wheel remains on its axle');
  assert.ok(wheel.node.quaternion.angleTo(wheel.baseQuaternion)>.1,'wheel really spins');
  const expected=new Quaternion().setFromAxisAngle(new Vector3(0,1,0),wheel.front?.4:0);
  assert.ok(wheel.steering.quaternion.angleTo(expected)<1e-6,'only front wheels steer');
}
for(let index=0;index<rig.doors.length;index++){
  assert.ok(Math.abs(rig.doors[index].angle)>1);
  assert.ok(new Box3().setFromObject(rig.doors[index].node).getCenter(new Vector3()).y>doorCenters[index].y+.1,'butterfly door geometry visibly raises');
}
assert.ok(rig.windows.every(glass=>Math.abs(glass.offset-.22)<1e-6));
for(const [node,matrix]of fixed)assert.deepEqual(node.matrixWorld.elements,matrix.elements,'windshield remains fixed while lateral glass lowers');
animateCarRig(rig,{wheelAngle:0,steeringAngle:0,doorOpen:false,windowsOpen:false},1);
assert.ok(rig.doors.every(door=>Math.abs(door.angle)<1e-6));
assert.ok(rig.windows.every(glass=>Math.abs(glass.offset)<1e-6));
assert.deepEqual(localTransformSnapshot(scene),originalTransforms,'runtime animation must not deform the shared original scene');
assert.ok(!activeWorldPlacements(world.environmentReplacements,{car:{sourceId:car.id}}).some(record=>record.id===car.id));
const report={passed:true,derivative:new URL(derivative).pathname,bytes:raw.length,sha256:hash(raw),sourceSha256:hash(original),sourcePreserved:true,inventory:exportedInventory,sourceInventory,splitVertices:exportedInventory.positions-sourceInventory.positions,splitVertexPercent:(exportedInventory.positions/sourceInventory.positions-1)*100,geometry:{matchedTriangles,toleranceM:tolerance,maxPositionError,maxUvError,maxNormalError,uvCorners},finiteVertices:vertices,normalizedSize:size.toArray(),placement:car.position,footprint:{w:car.w,d:car.d},wheels:4,doors:2,lateralGlass:2,frontDirection:'+Z',wheelCentersStable:true,frontSteeringOnly:true,doorsRaise:true,glassReversible:true,fixedWindshield:true,sharedScenePreserved:true,doorHingeApproximate:true,browserVisualValidation:false};
writeFileSync(new URL('reports/AMG_ONE_RUNTIME_VALIDATION_20261019.json',root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
