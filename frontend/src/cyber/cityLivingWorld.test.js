import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {Group,Mesh,BoxGeometry,MeshBasicMaterial,Bone,AnimationClip,VectorKeyframeTrack,Vector3} from 'three';
import {cityLivingWorldPlan as plan,livingWorldColliders,livingWorldZones,campusBenchLocations,habitatAsset,habitatPath,campusIsNear,selectLivingWorldResidents,livingWorldBlenderPoint,prepareCityCampusScene,prepareCityCampusShadows} from './cityLivingWorld.js';
import {createLivingAnimal} from './livingAnimalModel.js';
import {setWorldShadows} from './modelLighting.js';
const rectangle=item=>({x:item.position[0],z:item.position[2],w:item.size[0],d:item.size.at(-1)});
const overlap=(a,b)=>Math.abs(a.x-b.x)<(a.w+b.w)/2&&Math.abs(a.z-b.z)<(a.d+b.d)/2;

test('campus remains full scale in a connected northern district with disjoint habitats',()=>{
  assert.deepEqual(plan.campus.position,[-49,.04,-148]);assert.equal(plan.campus.scale,1);
  assert.deepEqual(plan.district.access.from,[-49,.23,-111]);assert.equal(plan.district.access.width,5);
  assert.deepEqual(plan.district.ground.size,[90,75]);
  const rectangles=[rectangle({...plan.campus,size:[25,28]}),...plan.habitats.map(rectangle)];
  for(let i=0;i<rectangles.length;i++)for(let j=i+1;j<rectangles.length;j++)assert.equal(overlap(rectangles[i],rectangles[j]),false,`${i}/${j}`);
  for(const r of rectangles){assert.ok(r.x-r.w/2>=-93&&r.x+r.w/2<=-3);assert.ok(r.z-r.d/2>=-187.5&&r.z+r.d/2<=-112.5);}
  assert.equal(plan.campus.hideNodes.includes('Patio'),false);assert.ok(plan.campus.hideNodes.includes('Terreno'));
});
test('the audited oak grove uses one compact real GLB and keeps all eight trunks outside campus and habitat footprints',()=>{
  const asset=plan.vegetation.asset,bytes=readFileSync(new URL('../../public'+asset.url,import.meta.url));
  assert.equal(bytes.length,asset.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256);
  assert.equal(asset.triangles,1217);assert.equal(plan.vegetation.placements.length,8);
  const rectangles=[rectangle({...plan.campus,size:[25,28]}),...plan.habitats.map(rectangle)];
  for(const tree of plan.vegetation.placements){
    const box={x:tree.position[0],z:tree.position[2],w:4.1,d:4.1};
    assert.ok(box.x-box.w/2>=-93&&box.x+box.w/2<=-3&&box.z-box.d/2>=-187.5&&box.z+box.d/2<=-112.5,tree.id);
    for(const occupied of rectangles)assert.equal(overlap(box,occupied),false,`${tree.id} overlaps an occupied lot`);
  }
});
test('each resident uses an existing animated source, unique ID and original animation',()=>{
  assert.equal(new Set(plan.habitats.map(h=>h.id)).size,6);
  assert.equal(new Set(plan.habitats.map(h=>h.assetId)).size,6);
  for(const h of plan.habitats){
    const asset=habitatAsset(h);assert.ok(asset?.rigged&&asset.originalRig&&asset.animated);
    assert.ok(asset.animations.includes(h.clip));assert.equal(h.position[1],.23);
    assert.ok(h.unloadRadius>h.loadRadius);
  }
  assert.equal(campusBenchLocations.length,2);assert.equal(livingWorldZones.length,7);
});
test('resident loading is automatic, nearest first, bounded, hysteretic and absent far away',()=>{
  assert.deepEqual(selectLivingWorldResidents({x:0,z:25}),[]);
  assert.equal(selectLivingWorldResidents({x:-49,z:-148}).length,2);
  for(let x=-90;x<-5;x+=4)for(let z=-185;z<-110;z+=4)assert.ok(selectLivingWorldResidents({x,z}).length<=3);
  const center={x:-78,z:-122};assert.equal(selectLivingWorldResidents(center)[0],'habitat-rabbit');
  assert.deepEqual(selectLivingWorldResidents({x:NaN,z:0}),[]);
  const outside={x:-108,z:-122};assert.ok(selectLivingWorldResidents(outside,['habitat-rabbit']).includes('habitat-rabbit'));
  assert.equal(campusIsNear({x:-49,z:-90}),false);assert.equal(campusIsNear({x:-49,z:-90},true),true);
});
test('all solid boundaries and campus fixtures have finite footprints and no path obstruction',()=>{
  assert.equal(new Set(livingWorldColliders.map(c=>c.id)).size,livingWorldColliders.length);
  for(const c of livingWorldColliders){assert.ok([c.x,c.z,c.w,c.d].every(Number.isFinite));assert.ok(c.w>0&&c.d>0);}
  assert.ok(livingWorldColliders.some(c=>c.id==='habitat-megalodon-tank'&&c.w===24&&c.d===16));
  const access={x:-49,z:-122.5,w:5,d:23};
  for(const collider of livingWorldColliders)assert.equal(overlap(access,collider),false,collider.id);
});
test('loop paths stay within clear habitat boundaries and shark remains in water',()=>{
  for(const h of plan.habitats){
    for(let t=0;t<=h.periodSeconds;t+=.13){
      const p=habitatPath(h,t);assert.ok(Object.values(p).every(Number.isFinite));
      // A conservative radius includes body and tail in any turn.
      const body=h.kind==='aquarium'?4:h.assetId.includes('HORSE')?2:1.6;
      assert.ok(Math.abs(p.x)+body<h.size[0]/2-.15,h.id);
      assert.ok(Math.abs(p.z)+body<h.size[1]/2-.15,h.id);
      if(h.kind==='aquarium'){assert.ok(p.y>.4);assert.ok(p.y+h.height<h.waterSurfaceY);assert.ok(h.targetLengthMeters<=h.maxLengthMeters);}
    }
  }
  assert.deepEqual(livingWorldBlenderPoint([-49,.04,-148]),[-49,148,.04]);
});
test('exact Blender node names survive GLTFLoader name sanitization when hiding redundant campus buildings',()=>{
  const scene=new Group();
  for(const name of plan.campus.hideNodes){const node=new Group();node.name=name.replaceAll('.','');node.userData.name=name;scene.add(node);}
  const patio=new Group();patio.name='Patio';scene.add(patio);prepareCityCampusScene(scene);
  for(const node of scene.children)assert.equal(node.visible,node.name==='Patio');
  assert.equal(patio.userData.walkable,true);
});
test('campus floor receives character and bench shadows without casting a shadow onto itself',()=>{
  const scene=new Group();
  const patio=new Mesh(new BoxGeometry(25,.12,28),new MeshBasicMaterial());patio.name='Patio';
  const bench=new Mesh(new BoxGeometry(2.6,.5,.64),new MeshBasicMaterial());bench.name='Banco';
  scene.add(patio,bench);setWorldShadows(scene);
  assert.equal(patio.castShadow,true);assert.equal(bench.castShadow,true);
  const positions=Array.from(patio.geometry.attributes.position.array),material=patio.material;
  prepareCityCampusShadows(scene);
  assert.equal(patio.castShadow,false);assert.equal(patio.receiveShadow,true);
  assert.equal(bench.castShadow,true);assert.equal(bench.receiveShadow,true);
  assert.deepEqual(Array.from(patio.geometry.attributes.position.array),positions);assert.equal(patio.material,material);
});
test('original horizontal pelvis movement is compensated by wrappers while the animation and geometry survive',()=>{
  const scene=new Group(),pelvis=new Bone();pelvis.name='Pelvis_00';scene.add(pelvis);
  const mesh=new Mesh(new BoxGeometry(.5,1,.6),new MeshBasicMaterial());mesh.position.y=.5;pelvis.add(mesh);
  const helper=new Mesh(new BoxGeometry(20,20,20),new MeshBasicMaterial());helper.name='Icosphere';scene.add(helper);
  const track=new VectorKeyframeTrack('Pelvis_00.position',[0,1],[0,0,0,6,.1,5]);
  const clip=new AnimationClip('walk',1,[track]),originalValues=Array.from(track.values);
  const runtime=createLivingAnimal({scene,animations:[clip]},{id:'test-resident',assetId:'test',clip:'walk',height:1,anchorBone:'Pelvis_00'});
  assert.equal(runtime.scaleFactor,1);assert.equal(helper.visible,false);
  for(const heading of [0,.6,Math.PI,-.7]){
    runtime.update(.1,{x:2,y:.23,z:4,heading});
    const body=mesh.getWorldPosition(new Vector3());assert.ok(Math.abs(body.x-2)<1e-6);assert.ok(Math.abs(body.z-4)<1e-6);
  }
  assert.deepEqual(Array.from(track.values),originalValues);assert.equal(mesh.geometry.parameters.height,1);
  assert.throws(()=>createLivingAnimal({scene:new Group(),animations:[]},{id:'missing',assetId:'missing',clip:'walk'}),/Animação original ausente/);
  runtime.stop();
});
