import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3,BufferGeometry,Float32BufferAttribute,Matrix4,Vector3} from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import {MeshBVH} from 'three-mesh-bvh';
import {applyCyberAction,createCyberState,DRIVE_VEHICLES} from './simulation.js';
import {listTruckProfiles,resolveTruckProfile,resolveTruckTrailer,TRAILER_DEFINITIONS,TRUCK_ARTICULATION_LIMIT,truckLocalToWorld,truckTrailerPose,
  truckColliders,truckPositionBlocked,truckSweepBlocked,moveTruck,safeTruckCopy,truckExitPosition} from './truckInteraction.js';
import {createTruckRig,animateTruckRig} from './truckArticulation.js';

await MeshoptDecoder.ready;
const wideBounds={minX:-1000,maxX:1000,minZ:-1000,maxZ:1000};
const freshTruck=(profile=resolveTruckProfile(),extra={})=>({x:0,y:0,z:0,heading:0,sourceId:profile.id,trailer:profile.compatibleTrailers.includes('flatbed')?'flatbed':'none',articulationAngle:0,wheelAngle:0,trailerWheelAngle:0,...extra});
async function loadGeometry(url){
  const bytes=readFileSync(new URL(`../../public${url}`,import.meta.url)),length=bytes.readUInt32LE(12);
  const document=JSON.parse(bytes.subarray(20,20+length).toString());
  document.buffers[0].uri='data:application/octet-stream;base64,'+bytes.subarray(28+length).toString('base64');
  document.images=[];document.textures=[];document.materials=[];
  for(const mesh of document.meshes)for(const primitive of mesh.primitives)delete primitive.material;
  if(!globalThis.ProgressEvent)globalThis.ProgressEvent=class{constructor(type,options){this.type=type;Object.assign(this,options);}};
  return (await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(JSON.stringify(document),'')).scene;
}
// Compare exported donor content rather than accepting a copied wheel label.
// Face UVs are sorted so vertex/index ordering and uniform placement/scale do
// not affect identity; tyre/rim topology and material appearance still must match.
function wheelAssemblyIdentities(url){
  const bytes=readFileSync(new URL(`../../public${url}`,import.meta.url)),length=bytes.readUInt32LE(12);
  const document=JSON.parse(bytes.subarray(20,20+length).toString()),binary=bytes.subarray(28+length);
  const views=new Map();
  const bufferData=index=>{
    if(views.has(index))return views.get(index);
    const bufferView=document.bufferViews[index],compression=bufferView.extensions?.EXT_meshopt_compression;
    let data;
    if(compression){
      const {buffer,byteOffset=0,byteLength,byteStride,count,mode,filter}=compression;
      assert.equal(buffer,0);
      const decoded=new Uint8Array(count*byteStride);
      MeshoptDecoder.decodeGltfBuffer(decoded,count,byteStride,binary.subarray(byteOffset,byteOffset+byteLength),mode,filter);
      data=new DataView(decoded.buffer);
    }else{
      assert.equal(bufferView.buffer,0);
      data=new DataView(binary.buffer,binary.byteOffset+(bufferView.byteOffset??0),bufferView.byteLength);
    }
    views.set(index,data);
    return data;
  };
  const componentTypes={5121:['getUint8',1],5123:['getUint16',2],5125:['getUint32',4],5126:['getFloat32',4]};
  const read=(accessorId,index,component=0)=>{
    const accessor=document.accessors[accessorId],bufferView=document.bufferViews[accessor.bufferView],[method,width]=componentTypes[accessor.componentType];
    const components=accessor.type==='VEC2'?2:1,stride=bufferView.byteStride??components*width;
    return bufferData(accessor.bufferView)[method]((accessor.byteOffset??0)+index*stride+component*width,true);
  };
  const primitives=index=>{
    const node=document.nodes[index],own=(node.mesh===undefined?[]:document.meshes[node.mesh].primitives).map(primitive=>{
      const count=document.accessors[primitive.indices??primitive.attributes.POSITION].count,faces=[];
      if(primitive.attributes.TEXCOORD_0!==undefined)for(let offset=0;offset<count;offset+=3){
        const uv=[];
        for(let vertex=0;vertex<3;vertex++){
          const index=primitive.indices===undefined?offset+vertex:read(primitive.indices,offset+vertex);
          uv.push([read(primitive.attributes.TEXCOORD_0,index,0),read(primitive.attributes.TEXCOORD_0,index,1)]);
        }
        faces.push(JSON.stringify(uv.sort((a,b)=>a[0]-b[0]||a[1]-b[1])));
      }
      const material=document.materials?.[primitive.material],pbr=material?.pbrMetallicRoughness??{};
      return {mode:primitive.mode??4,triangles:count/3,
        uvFaces:faces.length?createHash('sha256').update(JSON.stringify(faces.sort())).digest('hex'):null,
        material:material?{name:material.name,baseColor:pbr.baseColorFactor??[1,1,1,1],roughness:pbr.roughnessFactor??1,
          metalness:pbr.metallicFactor??1,alpha:material.alphaMode??'OPAQUE',baseMap:Boolean(pbr.baseColorTexture),normalMap:Boolean(material.normalTexture)}:null};
    });
    return [...own,...(node.children??[]).flatMap(primitives)].sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
  };
  return document.nodes.flatMap((node,index)=>{
    const name=node.extras?.runtime_node_name??node.name?.replace(/\.\d+$/,'');
    return /^Wheel_\d+_[LR]$/.test(name)?[{name,donorPivot:node.extras?.wheel_donor_pivot??null,parts:primitives(index)}]:[];
  }).sort((a,b)=>a.name.localeCompare(b.name));
}
const action=(state,action,context={})=>{const result=applyCyberAction(state,action,context);assert.equal(result.ok,true,result.message);return result.state;};
// The integrator accepted this explicit Scania cab region after native
// measurement: its upper rear envelope starts at Z=.60233593 m. Cutting at
// .55 m retains a 52 mm rear margin and every material, including glass and
// mixed chassis panels. It does not certify the rear chassis/fifth-wheel area.
function clearanceGeometry(root,cabRearZ){
  root.updateMatrixWorld(true);const values=[],points=[new Vector3(),new Vector3(),new Vector3()];
  const append=polygon=>{
    for(let i=1;i<polygon.length-1;i++)for(const point of [polygon[0],polygon[i],polygon[i+1]])values.push(point.x,point.y,point.z);
  };
  root.traverse(mesh=>{
    if(!mesh.isMesh)return;
    for(let ancestor=mesh;ancestor;ancestor=ancestor.parent){
      if(!ancestor.visible)return;
      if(cabRearZ!==undefined&&(ancestor.userData.role==='wheel_pivot'||/^Wheel_\d+_[LR]$/.test(ancestor.userData.runtime_node_name??ancestor.name)))return;
    }
    const position=mesh.geometry.attributes.position,index=mesh.geometry.index,count=index?.count??position.count;
    for(let offset=0;offset<count;offset+=3){
      points.forEach((point,i)=>point.fromBufferAttribute(position,index?index.getX(offset+i):offset+i).applyMatrix4(mesh.matrixWorld));
      if(cabRearZ===undefined){append(points);continue;}
      const inside=points.map(point=>point.z>=cabRearZ);if(inside.every(Boolean)){append(points);continue;}if(inside.every(value=>!value))continue;
      const clipped=[];
      for(let i=0;i<3;i++){
        const previous=points[(i+2)%3],current=points[i],wasInside=previous.z>=cabRearZ,isInside=current.z>=cabRearZ;
        if(isInside!==wasInside)clipped.push(previous.clone().lerp(current,(cabRearZ-previous.z)/(current.z-previous.z)));
        if(isInside)clipped.push(current);
      }
      append(clipped);
    }
  });
  const geometry=new BufferGeometry();geometry.setAttribute('position',new Float32BufferAttribute(values,3));
  assert.ok(values.length>0,'the declared clearance region must contain real geometry');
  geometry.boundsTree=new MeshBVH(geometry);return geometry;
}

test('truck profiles keep forward, reverse, steering and wheel travel independent of camera direction',()=>{
  assert.ok(listTruckProfiles().length>=2,'both audited truck models must be available');
  for(const profile of listTruckProfiles()){
    const start=freshTruck(profile),forward=moveTruck(start,{w:true},.05),reverse=moveTruck(start,{s:true},.05);
    assert.ok(forward.z>0&&reverse.z<0,profile.id);assert.equal(forward.heading,0);assert.equal(reverse.heading,0);
    assert.ok(forward.wheelAngle>0&&reverse.wheelAngle<0);
    if(resolveTruckTrailer(start))assert.ok(forward.trailerWheelAngle>0&&reverse.trailerWheelAngle<0);
    const left=moveTruck(start,{w:true,a:true},.05),backLeft=moveTruck(start,{s:true,a:true},.05);
    assert.ok(left.heading>0&&backLeft.heading<0);assert.ok(left.steeringAngle>0&&backLeft.steeringAngle>0);
    const stationary=moveTruck(start,{a:true},.05);assert.equal(stationary.heading,0);assert.equal(stationary.wheelAngle,0);
    assert.deepEqual(moveTruck(start,{w:true,s:true},.05).x,start.x);
  }
});

test('the trailer follows the hitch in forward and reverse, straightens forward and stops before jackknifing',()=>{
  for(const profile of listTruckProfiles())for(const trailer of Object.values(TRAILER_DEFINITIONS).filter(trailer=>profile.compatibleTrailers.includes(trailer.id))){
    let truck=freshTruck(profile,{trailer:trailer.id,articulationAngle:.3});
    for(let frame=0;frame<240;frame++)truck=moveTruck(truck,{w:true},.05,[],wideBounds);
    assert.ok(Math.abs(truck.articulationAngle)<.06,`${profile.id}/${trailer.id}: forward straightening`);
    truck=freshTruck(profile,{trailer:trailer.id,articulationAngle:.3});let stopped=false;
    for(let frame=0;frame<1200;frame++){
      const previous=truck;truck=moveTruck(truck,{s:true},.05,[],wideBounds);
      assert.ok(Math.abs(truck.articulationAngle)<=TRUCK_ARTICULATION_LIMIT+1e-9);
      assert.ok(Math.abs(truck.articulationAngle)<=resolveTruckTrailer(truck).articulationLimit+1e-9);
      const tractorHitch=truckLocalToWorld(truck,profile.hitch),trailerHitch=truckLocalToWorld(truckTrailerPose(truck),resolveTruckTrailer(truck).hitch);
      assert.ok(Math.hypot(tractorHitch.x-trailerHitch.x,tractorHitch.y-trailerHitch.y,tractorHitch.z-trailerHitch.z)<1e-10,'the coupling must remain joined');
      if(truck.blocked==='articulation'){assert.equal(truck.x,previous.x);assert.equal(truck.z,previous.z);assert.equal(truck.speed,0);stopped=true;break;}
    }
    assert.equal(stopped,true,`${profile.id}/${trailer.id}: unsafe reverse must stop`);
  }
});

test('collision protects the trailer body, swept movement and full city boundary instead of only the cab',()=>{
  for(const profile of listTruckProfiles())for(const trailer of Object.values(TRAILER_DEFINITIONS).filter(trailer=>profile.compatibleTrailers.includes(trailer.id))){
    const truck=freshTruck(profile,{trailer:trailer.id}),pose=truckTrailerPose(truck),obstacle={x:pose.x,z:pose.z-trailer.length*.3,w:.4,d:.4};
    assert.equal(truckPositionBlocked(truck,[obstacle]),true);
    assert.equal(truckPositionBlocked({...truck,trailer:'none'},[obstacle]),false,'the fixture must only obstruct the trailer');
    const blocked=moveTruck(truck,{s:true},.05,[obstacle]);assert.equal(blocked.z,truck.z);assert.equal(blocked.speed,0);assert.equal(blocked.wheelAngle,truck.wheelAngle);
    assert.equal(truckPositionBlocked({...truck,z:-188}),true,'the rear, not just the cab center, must stay inside the city');
    const next={...truck,x:25};assert.equal(truckPositionBlocked(next,[{x:12,z:0,w:.1,d:100}],wideBounds),false);
    assert.equal(truckSweepBlocked(truck,next,[{x:12,z:0,w:.1,d:100}],wideBounds),true,'a thin obstacle between clear endpoints must stop movement');
  }
});

test('summoning checks the entire coupled vehicle at city edges and refuses enclosed space',()=>{
  for(const profile of listTruckProfiles())for(const trailer of [...profile.compatibleTrailers,'none']){
    for(const position of [{x:-115,y:0,z:-187},{x:115,y:0,z:115}]){
      const truck=safeTruckCopy(position,Math.PI/4,profile.id,trailer);assert.ok(truck,`${profile.id}/${trailer}`);
      assert.equal(truckPositionBlocked(truck),false);
    }
    for(const heading of [0,Math.PI/4,Math.PI/2,Math.PI]){
      const truck=safeTruckCopy({x:0,y:0,z:0},heading,profile.id,trailer);assert.ok(truck);
      assert.equal(truckPositionBlocked(truck,[{x:0,z:0,w:.8,d:.8}]),false,'the summoned trailer must not cover the player');
    }
    assert.equal(safeTruckCopy({x:0,y:0,z:0},0,profile.id,trailer,[{x:0,z:0,w:200,d:200}]),null);
  }
});

test('game actions keep the selected truck model and trailer, require a stop for coupling, and leave a clear exit',()=>{
  for(const profile of listTruckProfiles()){
    let state=action(createCyberState(),{type:'SUMMON_VEHICLE',vehicle:'truck',sourceId:profile.id});
    const truck=state.personalVehicles.truck;assert.equal(truck.sourceId,profile.id);assert.equal(truck.trailer,profile.compatibleTrailers.includes('flatbed')?'flatbed':'none');
    state={...state,position:{x:truck.x,y:0,z:truck.z}};
    assert.equal(applyCyberAction({...state,jump:{}},{type:'DRIVE',vehicle:'truck'}).ok,false);
    state=action(state,{type:'DRIVE',vehicle:'truck'});
    assert.equal(applyCyberAction(state,{type:'MOVE',position:{x:0,y:0,z:100}}).ok,false,'generic walking must not bypass coupled collisions');
    state=action(state,{type:'TRUCK_DRIVE',keys:{w:true},delta:.05});
    assert.equal(applyCyberAction(state,{type:'TRAILER',trailer:'box'}).ok,false);
    state=action(state,{type:'TRUCK_DRIVE',keys:{},delta:.05});
    const pose=truckTrailerPose(state.personalVehicles.truck);
    if(pose){const blocker={x:pose.x,z:pose.z,w:1,d:1};assert.equal(applyCyberAction(state,{type:'TRAILER',trailer:'box'},{obstacles:[blocker]}).ok,false);}
    for(const trailer of [...profile.compatibleTrailers,'none']){
      state=action(state,{type:'TRAILER',trailer});assert.equal(state.personalVehicles.truck.trailer,trailer);
    }
    for(const trailer of Object.keys(TRAILER_DEFINITIONS).filter(id=>!profile.compatibleTrailers.includes(id)))assert.equal(applyCyberAction(state,{type:'TRAILER',trailer}).ok,false,'incompatible semitrailers must be rejected');
    if(profile.compatibleTrailers.includes('flatbed'))state=action(state,{type:'TRAILER',trailer:'flatbed'});
    const exit=truckExitPosition(state.personalVehicles.truck);assert.ok(exit);
    for(const box of truckColliders(state.personalVehicles.truck))assert.ok(Math.abs(exit.x-box.x)>=box.w/2+.4||Math.abs(exit.z-box.z)>=box.d/2+.4);
    const blockedExit={obstacles:[{x:state.position.x,z:state.position.z,w:100,d:100}],parking:[{id:'test',position:[state.position.x,0,state.position.z]}]};
    assert.equal(applyCyberAction(state,{type:'EXIT'},blockedExit).ok,false);
    assert.equal(applyCyberAction(state,{type:'STORE_VEHICLE'},blockedExit).ok,false,'parking must not place the player inside a blocker');
    state=action(state,{type:'EXIT'});assert.equal(state.mode,'foot');assert.equal(state.personalVehicles.truck.sourceId,profile.id);assert.equal(state.personalVehicles.truck.speed,0);
    state={...state,position:{...DRIVE_VEHICLES.truck.position,y:10},personalVehicles:{}};
    assert.equal(applyCyberAction(state,{type:'DRIVE',vehicle:'truck'}).ok,false,'a player upstairs cannot board a truck below');
  }
});

test('actual truck and trailer GLBs fit the collision profiles and their wheel centers survive steering and rolling',async()=>{
  const donorAssemblies=wheelAssemblyIdentities(resolveTruckProfile('scania').url);
  for(const profile of [...listTruckProfiles(),...Object.values(TRAILER_DEFINITIONS)]){
    const source=await loadGeometry(profile.url),original=new Box3().setFromObject(source,true),rig=createTruckRig(source,profile.height,profile.sourceYaw??0,profile.normalized,!profile.wheelbase);
    assert.ok(rig.wheels.length>=4,`${profile.id}: real separate wheels are required`);
    const isTruck=Boolean(profile.wheelbase);
    assert.equal(rig.wheels.filter(wheel=>wheel.front).length,isTruck?2:0,`${profile.id}: only the front truck axle should steer`);
    if(!isTruck){
      const expectedAssemblies=['Wheel_00_L','Wheel_00_R','Wheel_01_L','Wheel_01_R'].map(name=>{
        const donorPivot=`Wheel_01_${name.at(-1)}`;
        return {name,donorPivot,parts:donorAssemblies.find(wheel=>wheel.name===donorPivot)?.parts};
      });
      assert.deepEqual(wheelAssemblyIdentities(profile.url),expectedAssemblies,
        `${profile.id}: all four wheel pivots must preserve actual Scania rear tyre/rim topology, UVs and materials`);
      const legs=[];rig.outer.traverse(node=>{if(node.userData.hide_when_coupled)legs.push(node);});
      assert.ok(legs.length>=2,`${profile.id}: both landing legs must declare their coupled state`);
      assert.ok(legs.every(node=>node.visible===false),`${profile.id}: coupled landing legs must be hidden in the runtime`);
    }
    rig.outer.updateMatrixWorld(true);const initial=rig.wheels.map(wheel=>wheel.node.getWorldPosition(new Vector3()));
    const geometricCenters=rig.wheels.map(wheel=>new Box3().setFromObject(wheel.node,true).getCenter(new Vector3()));
    animateTruckRig(rig,{steeringAngle:.35,wheelAngle:Math.PI/2},profile);rig.outer.updateMatrixWorld(true);
    rig.wheels.forEach((wheel,index)=>{
      assert.ok(wheel.node.getWorldPosition(new Vector3()).distanceTo(initial[index])<1e-6,`${profile.id}: spinning cannot move a wheel off its axle`);
      assert.ok(new Box3().setFromObject(wheel.node,true).getCenter(new Vector3()).distanceTo(geometricCenters[index])<.03,`${profile.id}: actual wheel geometry must rotate around its axle`);
    });
    animateTruckRig(rig,{steeringAngle:0,wheelAngle:0});rig.outer.updateMatrixWorld(true);
    const actual=new Box3().setFromObject(rig.outer,true),size=actual.getSize(new Vector3());
    assert.ok(size.x<=profile.width+1e-4,`${profile.id}: profile width ${profile.width} must enclose ${size.x}`);
    assert.ok(size.z<=profile.length+1e-4,`${profile.id}: profile length ${profile.length} must enclose ${size.z}`);
    assert.ok(Math.abs(actual.min.y)<1e-5,`${profile.id}: tires must meet the floor`);
    for(const wheel of rig.wheels)assert.ok(Math.abs(new Box3().setFromObject(wheel.node,true).min.y)<.04,`${profile.id}/${wheel.node.name}: every wheel must meet the floor`);
    assert.ok(new Box3().setFromObject(source,true).equals(original),'rig creation must preserve the shared source');
    if(isTruck){
      animateTruckRig(rig,{steeringAngle:.48,wheelAngle:.3},profile);rig.outer.updateMatrixWorld(true);
      const steered=new Box3().setFromObject(rig.outer,true),collision=truckColliders(freshTruck(profile,{trailer:'none',steeringAngle:.48}))[0];
      assert.ok(steered.min.x>=collision.x-collision.w/2-1e-4&&steered.max.x<=collision.x+collision.w/2+1e-4,`${profile.id}: collision must include steered tires`);
      const front=rig.wheels.filter(wheel=>wheel.front).sort((a,b)=>a.lateralPosition-b.lateralPosition);
      assert.ok(front[1].steering.rotation.y>front[0].steering.rotation.y,'the inner wheel needs a tighter steering angle');
    }
  }
});

test('actual coupled GLBs remain inside their separate collision bounds throughout turns without lifting trailer tires',async()=>{
  const encloses=(box,collision,label)=>{
    assert.ok(box.min.x>=collision.x-collision.w/2-1e-4&&box.max.x<=collision.x+collision.w/2+1e-4,`${label}: X bounds`);
    assert.ok(box.min.z>=collision.z-collision.d/2-1e-4&&box.max.z<=collision.z+collision.d/2+1e-4,`${label}: Z bounds`);
  };
  for(const profile of listTruckProfiles()){
    const truckRig=createTruckRig(await loadGeometry(profile.url),profile.height,profile.sourceYaw??0,profile.normalized);
    for(const trailerId of profile.compatibleTrailers){
      const definition=TRAILER_DEFINITIONS[trailerId],trailerRig=createTruckRig(await loadGeometry(definition.url),definition.height,0,definition.normalized,true);
      const limit=Math.min(.5,resolveTruckTrailer(freshTruck(profile,{trailer:trailerId})).articulationLimit);
      for(const heading of [0,Math.PI/4,Math.PI/2])for(const articulationAngle of [-limit,0,limit]){
        const truck=freshTruck(profile,{x:12,z:25,heading,trailer:trailerId,articulationAngle}),pose=truckTrailerPose(truck),collisions=truckColliders(truck);
        truckRig.outer.position.set(truck.x,0,truck.z);truckRig.outer.rotation.y=heading;truckRig.outer.updateMatrixWorld(true);
        trailerRig.outer.position.set(pose.x,pose.y,pose.z);trailerRig.outer.rotation.y=pose.heading;trailerRig.outer.updateMatrixWorld(true);
        encloses(new Box3().setFromObject(truckRig.outer,true),collisions[0],profile.id);
        const actual=new Box3().setFromObject(trailerRig.outer,true);encloses(actual,collisions[1],trailerId);
        assert.ok(Math.abs(actual.min.y)<.01,`${profile.id}/${trailerId}: matched coupling height must preserve tire contact`);
      }
    }
  }
});

test('real Scania cab triangles clear each complete coupled trailer throughout its configured articulation range',async context=>{
  const profile=listTruckProfiles().find(profile=>profile.compatibleTrailers.length);assert.ok(profile,'a tractor profile is required');
  assert.equal(profile.sourceId,'SUP_scania_truck','the measured cab ROI is specific to the audited Scania');
  const rig=createTruckRig(await loadGeometry(profile.url),profile.height,0,profile.normalized),cabRearZ=.55,cab=clearanceGeometry(rig.outer,cabRearZ);
  for(const trailerId of profile.compatibleTrailers){
    const definition=TRAILER_DEFINITIONS[trailerId],trailerRig=createTruckRig(await loadGeometry(definition.url),definition.height,0,definition.normalized,true);
    const trailer=clearanceGeometry(trailerRig.outer),limit=resolveTruckTrailer(freshTruck(profile,{trailer:trailerId})).articulationLimit;
    const samples=Math.ceil(limit*180/Math.PI),angles=Array.from({length:samples*2+1},(_,i)=>-limit+2*limit*i/(samples*2));
    let minimum=Infinity,closestAngle=0;
    for(const angle of angles){
      const pose=truckTrailerPose(freshTruck(profile,{trailer:trailerId,articulationAngle:angle})),transform=new Matrix4().makeRotationY(pose.heading).setPosition(pose.x,pose.y,pose.z);
      assert.equal(cab.boundsTree.intersectsGeometry(trailer,transform),false,`${trailerId}: cab intersection at ${angle*180/Math.PI} degrees`);
      const nearest=cab.boundsTree.closestPointToGeometry(trailer,transform);
      assert.ok(nearest&&nearest.distance>.02,`${trailerId}: less than 2 cm cab clearance at ${angle*180/Math.PI} degrees`);
      if(nearest.distance<minimum){minimum=nearest.distance;closestAngle=angle;}
    }
    context.diagnostic(JSON.stringify({truck:profile.id,trailer:trailerId,cabRearZ,samples:angles.length,limitDegrees:limit*180/Math.PI,
      minimumCabClearanceM:minimum,closestAngleDegrees:closestAngle*180/Math.PI,scope:'all visible trailer geometry versus non-wheel truck triangles clipped to cab Z>=.55 m'}));
  }
});
