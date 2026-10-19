import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Group,Matrix4,Mesh,MeshBasicMaterial,Quaternion,Raycaster,Shape,ShapeGeometry,Vector2,Vector3} from 'three';
import buildings from '../config/buildingDoors.json' with {type:'json'};
import {buildDeliveryRoadSurfaces,deliveryRoadRectangle,deliveryPolygonArea,subtractDeliveryPolygon,deliveryPointInPolygon,
  newDeliveryRoadConnections as roads,newDeliveryRoutes,newDeliveryColliders,newDeliveryZones} from './newDeliveryWorld.js';
import {createSolidIndex} from './collisions.js';

const surfaces=buildDeliveryRoadSurfaces();
const originals=roads.existingRoads.map(r=>deliveryRoadRectangle(r.from,r.to,r.width));
const intersectionArea=(a,b)=>deliveryPolygonArea(a)-subtractDeliveryPolygon(a,b).reduce((sum,p)=>sum+deliveryPolygonArea(p),0);
const rectangle=(x,z,w,d)=>deliveryRoadRectangle([x-w/2,z],[x+w/2,z],d);
const inAny=(point,polygons)=>polygons.some(p=>deliveryPointInPolygon(point,p));

test('road clipping preserves area for overlap, containment, disjoint edges and diagonal crossings',()=>{
  const square=rectangle(0,0,10,10);
  assert.equal(intersectionArea(square,rectangle(5,0,10,10)),50);
  assert.equal(intersectionArea(square,rectangle(0,0,20,20)),100);
  assert.equal(intersectionArea(square,rectangle(0,0,4,4)),16);
  assert.equal(intersectionArea(square,rectangle(10,0,10,10)),0);
  const diagonal=deliveryRoadRectangle([-20,-20],[20,20],2);
  const remainder=subtractDeliveryPolygon(square,diagonal);
  assert.ok(remainder.length>=2);
  assert.ok(intersectionArea(square,diagonal)>20&&intersectionArea(square,diagonal)<30);
  assert.ok(remainder.every(p=>intersectionArea(p,diagonal)<1e-6));
});

test('existing road dimensions and palette match the actual untouched scene asset',()=>{
  const buffer=readFileSync(new URL(`../../public${roads.sourceScene}`,import.meta.url));
  const gltf=JSON.parse(buffer.subarray(20,20+buffer.readUInt32LE(12)).toString());
  for(const road of roads.existingRoads){
    const node=gltf.nodes.find(n=>n.name===road.id);assert.ok(node,road.id);
    const positions=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
    const matrix=new Matrix4().compose(new Vector3().fromArray(node.translation),new Quaternion().fromArray(node.rotation??[0,0,0,1]),new Vector3().fromArray(node.scale??[1,1,1]));
    const vertices=Array.from({length:8},(_,i)=>new Vector3(i&1?positions.max[0]:positions.min[0],i&2?positions.max[1]:positions.min[1],i&4?positions.max[2]:positions.min[2]).applyMatrix4(matrix));
    const low=vertices.reduce((a,p)=>a.min(p),new Vector3(Infinity,Infinity,Infinity));
    const high=vertices.reduce((a,p)=>a.max(p),new Vector3(-Infinity,-Infinity,-Infinity));
    const polygon=deliveryRoadRectangle(road.from,road.to,road.width);
    assert.ok(Math.abs(low.x-Math.min(...polygon.map(p=>p[0])))<.001,road.id);
    assert.ok(Math.abs(high.z-Math.max(...polygon.map(p=>p[1])))<.001,road.id);
    assert.ok(Math.abs(high.y-.15)<.001,road.id);
  }
  for(const material of Object.values(roads.materials)){
    const source=gltf.materials.find(m=>m.name===material.source);assert.ok(source,material.source);
    material.linearColor.forEach((value,i)=>assert.ok(Math.abs(value-source.pbrMetallicRoughness.baseColorFactor[i])<1e-6));
    assert.ok(Math.abs(material.roughness-source.pbrMetallicRoughness.roughnessFactor)<1e-6);
  }
});

test('only missing asphalt is added and the new streets do not duplicate each other',()=>{
  const added=surfaces.filter(s=>s.material==='asfalto');assert.ok(added.length>=4);
  for(const [i,surface] of added.entries()){
    assert.ok(deliveryPolygonArea(surface.points)>1e-6,surface.id);
    for(const original of originals)assert.ok(intersectionArea(surface.points,original)<1e-5,surface.id);
    for(const other of added.slice(i+1))assert.ok(intersectionArea(surface.points,other.points)<1e-5,`${surface.id} / ${other.id}`);
  }
  assert.ok(added.reduce((area,s)=>area+deliveryPolygonArea(s.points),0)>900);
});

test('the complete bus route has visible asphalt across its width including all junctions',()=>{
  const asphalt=[...originals,...surfaces.filter(s=>s.material==='asfalto').map(s=>s.points)];
  const route=newDeliveryRoutes.bus;
  for(let i=0;i<route.points.length;i++){
    const a=route.points[i],b=route.points[(i+1)%route.points.length],dx=b.x-a.x,dz=b.z-a.z,length=Math.hypot(dx,dz),steps=Math.ceil(length*2);
    for(let j=0;j<=steps;j++)for(const offset of [-1.65,0,1.65]){
      const point=[a.x+dx*j/steps-dz/length*offset,a.z+dz*j/steps+dx/length*offset];
      assert.ok(inAny(point,asphalt),`Trecho ${i}, passo ${j}, margem ${offset}`);
    }
  }
});

test('new floors keep buildings, station frontage and the city limits clear',()=>{
  for(const surface of surfaces.filter(s=>['asfalto','ciclofaixa','calcada'].includes(s.material))){
    assert.equal(surface.walkable,true,surface.id);
    assert.ok(surface.surfaceY<=.25,surface.id);
    assert.ok(surface.points.every(([x,z])=>Math.abs(x)<=118&&Math.abs(z)<=118),surface.id);
    for(const building of buildings){
      const footprint=rectangle(building.center[0],building.center[2],building.width+.26,building.depth+.26);
      assert.ok(intersectionArea(surface.points,footprint)<1e-5,`${surface.id}: ${building.id}`);
    }
  }
  const cycle=surfaces.filter(s=>s.material==='ciclofaixa');
  assert.equal(inAny([-70,-94.6],cycle.map(s=>s.points)),false,'Fachada da estação preservada');
  assert.ok(inAny([-110.1,42.3],cycle.map(s=>s.points)),'Ligação à ciclofaixa existente na praça');
  const existingPaths=roads.existingRoads.flatMap(r=>[-1,1].flatMap(side=>[
    deliveryRoadRectangle(r.from,r.to,2,side*7.3),deliveryRoadRectangle(r.from,r.to,2.3,side*9.75)]));
  const pedestrianFloors=[...originals,...existingPaths,...surfaces.filter(s=>['asfalto','ciclofaixa','calcada'].includes(s.material)).map(s=>s.points)];
  for(const link of roads.pedestrianLinks)for(let i=1;i<link.points.length;i++){
    const a=link.points[i-1],b=link.points[i],length=Math.hypot(b[0]-a[0],b[1]-a[1]),steps=Math.ceil(length*2);
    for(let j=0;j<=steps;j++)for(const offset of [-link.width/2,0,link.width/2]){
      const point=[a[0]+(b[0]-a[0])*j/steps-(b[1]-a[1])/length*offset,a[1]+(b[1]-a[1])*j/steps+(b[0]-a[0])/length*offset];
      assert.ok(inAny(point,pedestrianFloors),`${link.id} possui piso contínuo em toda a largura`);
      if(offset===0)for(const building of buildings)assert.ok(intersectionArea(rectangle(point[0],point[1],.8,.8),rectangle(building.center[0],building.center[2],building.width+.26,building.depth+.26))<1e-5,`${link.id}: ${building.id}`);
    }
  }
});

test('flat pedestrian crossing and the open station stop edge introduce no solid barriers',()=>{
  const crossing=surfaces.filter(s=>s.kind==='travessia');assert.equal(crossing.length,5);
  for(const surface of crossing)for(const collider of newDeliveryColliders){
    assert.ok(intersectionArea(surface.points,rectangle(collider.x,collider.z,collider.w,collider.d))<1e-5,surface.id);
  }
  const edge=surfaces.filter(s=>s.id.startsWith('via-oeste-borda--1'));
  assert.equal(inAny([-103.32,-89],edge.map(s=>s.points)),false,'Nenhuma linha fecha a frente da parada');
  for(const zone of newDeliveryZones.filter(z=>z.stopId)){
    for(const collider of newDeliveryColliders){
      assert.ok(intersectionArea(rectangle(zone.approach[0],zone.approach[2],.8,.8),rectangle(collider.x,collider.z,collider.w,collider.d))<1e-5,`${zone.id}: ${collider.id}`);
    }
  }
  assert.match(roads.status,/conceitual/);assert.equal(roads.railCrossings.length,1);
});

test('rendered polygon floors face up, support ground rays and are excluded from solid collisions',()=>{
  const group=new Group();group.userData.walkable=true;
  const material=new MeshBasicMaterial();
  for(const surface of surfaces){
    const geometry=new ShapeGeometry(new Shape(surface.points.map(([x,z])=>new Vector2(x,-z))));
    const mesh=new Mesh(geometry,material);mesh.rotation.x=-Math.PI/2;mesh.position.y=surface.surfaceY;group.add(mesh);
  }
  group.updateMatrixWorld(true);
  const ray=new Raycaster();
  for(const [x,z] of [[12,-99],[-106,-48],[-110.1,-30],[-60,-96.7]]){
    ray.set(new Vector3(x,2,z),new Vector3(0,-1,0));
    const hit=ray.intersectObjects(group.children,false)[0];assert.ok(hit,`Piso visível em ${x}, ${z}`);
    assert.ok(hit.point.y>=.15&&hit.point.y<.251);
  }
  assert.deepEqual(createSolidIndex(group),[]);
  group.children.forEach(mesh=>mesh.geometry.dispose());material.dispose();
});
