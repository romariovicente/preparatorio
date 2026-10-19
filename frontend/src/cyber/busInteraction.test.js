import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Box3,Matrix4,Quaternion,Vector3} from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {advanceCityPosition,applyCyberAction,createCyberState,tickCyberState} from './simulation.js';
import {BUS_IDS,BUS_BRT_ROUTE,BUS_ROUTES,BUS_DEFINITIONS,busDoorPosition,busSeatPosition,busFootprint,busFootprintPolygons,busPositionBlocked,buildBusPath,canBoardBus,nearestBus,returnBusToRoute,sampleLiveBus} from './busInteraction.js';
import delivery from '../config/newDeliveryWorld.json' with {type:'json'};
import buildings from '../config/buildingDoors.json' with {type:'json'};
import monuments from '../config/monumentAssets.json' with {type:'json'};
import {animateBusRig,createBusRig,BRT_INTERACTIVE_URL} from './busArticulation.js';
import {buildDeliveryRoadSurfaces,deliveryRoadRectangle,deliveryPolygonArea,subtractDeliveryPolygon,deliveryPointInPolygon,newDeliveryColliders} from './newDeliveryWorld.js';
const distance=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const boardingState=id=>{const state=createCyberState();return {...state,position:busDoorPosition(sampleLiveBus(state,id))};};
const action=(state,type,extra={})=>{const result=applyCyberAction(state,{type,...extra});assert.equal(result.ok,true,result.message);return result.state;};
function busOverlapArea(first,second){
  return busFootprintPolygons(first).reduce((total,one)=>total+busFootprintPolygons(second).reduce((area,two)=>
    area+deliveryPolygonArea(one)-subtractDeliveryPolygon(one,two).reduce((rest,polygon)=>rest+deliveryPolygonArea(polygon),0),0),0);
}
async function loadGeometry(url){
  const bytes=readFileSync(new URL(`../../public${url}`,import.meta.url)),length=bytes.readUInt32LE(12);
  const document=JSON.parse(bytes.subarray(20,20+length).toString());
  document.buffers[0].uri='data:application/octet-stream;base64,'+bytes.subarray(28+length).toString('base64');
  document.images=[];document.textures=[];document.materials=[];
  for(const mesh of document.meshes)for(const primitive of mesh.primitives)delete primitive.material;
  if(!globalThis.ProgressEvent)globalThis.ProgressEvent=class{constructor(type,options){this.type=type;Object.assign(this,options);}};
  return (await new GLTFLoader().parseAsync(JSON.stringify(document),'')).scene;
}
function originalCenterFootprints(){
  const bytes=readFileSync(new URL(`../../public${delivery.roadConnections.sourceScene}`,import.meta.url));
  const document=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const parents=new Map();document.nodes.forEach((n,i)=>(n.children??[]).forEach(child=>parents.set(child,i)));
  const matrices=new Map(),worldMatrix=index=>{
    if(matrices.has(index))return matrices.get(index);
    const node=document.nodes[index],matrix=node.matrix?new Matrix4().fromArray(node.matrix):new Matrix4().compose(
      new Vector3().fromArray(node.translation??[0,0,0]),new Quaternion().fromArray(node.rotation??[0,0,0,1]),new Vector3().fromArray(node.scale??[1,1,1]));
    if(parents.has(index))matrix.premultiply(worldMatrix(parents.get(index)));matrices.set(index,matrix);return matrix;
  };
  return document.nodes.flatMap((node,index)=>{
    if(node.mesh===undefined||!(/^(PLAZA_|STAT_Language|TELEPORT_)/.test(node.name))||monuments.some(a=>a.hidePrefixes.some(p=>node.name.startsWith(p))))return [];
    const box=new Box3();
    for(const primitive of document.meshes[node.mesh].primitives){
      const position=document.accessors[primitive.attributes.POSITION];
      for(let i=0;i<8;i++)box.expandByPoint(new Vector3(i&1?position.max[0]:position.min[0],i&2?position.max[1]:position.min[1],i&4?position.max[2]:position.min[2]).applyMatrix4(worldMatrix(index)));
    }
    const center=box.getCenter(new Vector3()),size=box.getSize(new Vector3());return [{id:node.name,x:center.x,z:center.z,w:size.x,d:size.z}];
  });
}
async function monumentFootprints(){
  const rows=[];
  for(const asset of monuments){
    const model=await loadGeometry(asset.url),size=new Box3().setFromObject(model,true).getSize(new Vector3()),scale=asset.height/size.y;
    rows.push(...asset.positions.map((p,i)=>({id:`${asset.id}-${i}`,x:p[0],z:p[2],w:size.x*scale,d:size.z*scale})));
  }
  return rows;
}

test('the bus collision bounds enclose the actual eight-wheel GLB through its complete articulation range',async()=>{
  const rig=createBusRig(await loadGeometry(BRT_INTERACTIVE_URL));assert.equal(rig.wheels.length,8);
  const definition=BUS_DEFINITIONS['bus-brt'];
  for(const heading of [0,Math.PI/4,Math.PI/2,-Math.PI/4])for(const joint of [-definition.articulationLimit,0,definition.articulationLimit]){
    const bus={id:'bus-brt',x:0,y:0,z:0,heading,articulationAngle:joint};
    animateBusRig(rig,{articulationAngle:joint,doorOpen:false},1);rig.outer.rotation.y=heading;rig.outer.updateMatrixWorld(true);
    const actual=new Box3().setFromObject(rig.outer,true),footprint=busFootprint(bus);
    assert.ok(actual.min.x>=footprint.x-footprint.w/2-1e-5,`left bound: ${heading}, ${joint}`);
    assert.ok(actual.max.x<=footprint.x+footprint.w/2+1e-5,`right bound: ${heading}, ${joint}`);
    assert.ok(actual.min.z>=footprint.z-footprint.d/2-1e-5,`rear bound: ${heading}, ${joint}`);
    assert.ok(actual.max.z<=footprint.z+footprint.d/2+1e-5,`front bound: ${heading}, ${joint}`);
  }
});

test('both authored bus instances circulate and require the stopped entrance on foot',()=>{
  for(const id of BUS_IDS){
    let state=boardingState(id),bus=sampleLiveBus(state,id);
    assert.equal(nearestBus(state).id,id);
    assert.equal(applyCyberAction({...state,jump:{startedAt:0}},{type:'BOARD',vehicle:id}).ok,false);
    assert.equal(applyCyberAction({...state,position:{x:70,y:0,z:70}},{type:'BOARD',vehicle:id}).ok,false);
    state=action(state,'BOARD',{vehicle:id});
    assert.deepEqual(state.position,busSeatPosition(bus));
    assert.deepEqual(state.personalVehicles,{});
    for(let step=0;step<30;step++)state=tickCyberState(state,.5);
    bus=sampleLiveBus(state,id);
    assert.equal(bus.stopped,false);assert.ok(Math.abs(bus.wheelAngle)>1);assert.deepEqual(state.position,busSeatPosition(bus));
    assert.equal(applyCyberAction(state,{type:'EXIT'}).ok,false);
    assert.equal(applyCyberAction(state,{type:'BUS_TAKE_WHEEL'}).ok,false);
  }
});
test('taking the wheel pauses the shared bus, engine gates motion and passengers stay in the real driver seat',()=>{
  let state=action(action(boardingState('bus-brt'),'BOARD',{vehicle:'bus-brt'}),'BUS_TAKE_WHEEL');
  const start=sampleLiveBus(state,'bus-brt');
  assert.equal(start.control,'player');assert.equal(start.engineOn,false);
  assert.equal(applyCyberAction(state,{type:'BUS_DRIVE',keys:{w:true},delta:.05}).ok,false);
  state=tickCyberState(state,.5);assert.equal(distance(start,sampleLiveBus(state,'bus-brt')),0);
  state=action(state,'BUS_ENGINE');
  assert.equal(applyCyberAction(state,{type:'EXIT'}).ok,false,'a stopped bus still requires open doors');
  for(let step=0;step<20;step++)state=action(state,'BUS_DRIVE',{keys:{w:true,a:true},delta:.05});
  const driven=sampleLiveBus(state,'bus-brt');assert.ok(distance(start,driven)>4);assert.ok(driven.heading>start.heading);
  assert.ok(driven.wheelAngle>5);assert.ok(driven.articulationAngle<0);
  assert.deepEqual(state.position,busSeatPosition(driven,'driver'));
  assert.equal(applyCyberAction(state,{type:'EXIT'}).ok,false);
  state=action(state,'BUS_STOP');assert.equal(sampleLiveBus(state,'bus-brt').doorOpen,true);
  const exit=action(state,'EXIT');assert.equal(exit.mode,'foot');assert.equal(exit.busControls.role,null);
  assert.equal(exit.liveBuses['bus-brt'].control,'rejoin');
  assert.deepEqual(exit.personalVehicles,{});assert.equal(Object.keys(exit.liveBuses).length,2);
});
test('releasing a displaced bus preserves its position and rejoins its original route continuously',()=>{
  let state=action(action(boardingState('bus'),'BOARD',{vehicle:'bus'}),'BUS_TAKE_WHEEL');
  state=action(state,'BUS_ENGINE');
  for(let i=0;i<60;i++)state=action(state,'BUS_DRIVE',{keys:{w:true,a:true},delta:.05});
  state=action(state,'BUS_STOP');const parked=sampleLiveBus(state,'bus');
  state=action(state,'BUS_RELEASE_WHEEL');assert.equal(distance(parked,sampleLiveBus(state,'bus')),0);
  let rejoined=false;
  for(let i=0;i<1200;i++){
    const before=sampleLiveBus(state,'bus');state=tickCyberState(state,.05);const after=sampleLiveBus(state,'bus');
    assert.ok(distance(before,after)<=BUS_ROUTES.bus.speed*.05+.021,'no route reset or vehicle teleport');
    assert.deepEqual(state.position,busSeatPosition(after));
    if(after.control==='npc'){rejoined=true;break;}
  }
  assert.equal(rejoined,true);assert.equal(state.busControls.role,'passenger');assert.deepEqual(state.personalVehicles,{});
});
test('BRT path visits terminal and existing stop approaches with rounded road junctions',()=>{
  const path=buildBusPath(BUS_BRT_ROUTE);
  assert.ok(path.points.length>BUS_BRT_ROUTE.points.length);
  for(const stop of BUS_BRT_ROUTE.stops)assert.ok(path.points.some(p=>distance(p,stop.position)<.001));
  assert.equal(path.legs[0].point.stop.id,'terminal');
  assert.equal(sampleLiveBus(createCyberState(),'bus-brt').stopId,'terminal');
  assert.equal(sampleLiveBus(createCyberState(),'bus-brt').heading,0);
  assert.deepEqual(BUS_BRT_ROUTE.stops[0].position,{x:-106,y:0,z:-49});
  assert.equal(BUS_BRT_ROUTE.stops[0].label,'Terminal · acesso pela Via Oeste');
  assert.ok(BUS_BRT_ROUTE.points.every(p=>p.z>=33||p.z<=-89||p.x<=-102||p.x>=105),'route stays outside the central monuments');
});

test('manual bus stops at a blocking object and keeps its wheel angle and seated player in place',()=>{
  let state=action(action(boardingState('bus-brt'),'BOARD',{vehicle:'bus-brt'}),'BUS_TAKE_WHEEL');
  state=action(state,'BUS_ENGINE');const before=sampleLiveBus(state,'bus-brt');
  const result=applyCyberAction(state,{type:'BUS_DRIVE',keys:{w:true},delta:.05},{obstacles:[{id:'wall',x:before.x,z:before.z+11.8,w:6,d:.4}]});
  assert.equal(result.ok,true);const stopped=sampleLiveBus(result.state,'bus-brt');
  assert.equal(distance(before,stopped),0);assert.equal(stopped.wheelAngle,before.wheelAngle);assert.equal(stopped.stopped,true);
  assert.deepEqual(result.state.position,busSeatPosition(stopped,'driver'));
});
test('BRT has one moving instance and no obsolete parked collider; boarding uses the authored front door side',()=>{
  const record=delivery.compositions.find(p=>p.id==='delivery-brt');assert.equal(record.role,'transit-vehicle');
  assert.equal(delivery.dynamicReplacements['bus-brt'],record.assetId);
  assert.ok(!newDeliveryColliders.some(c=>c.id===record.id));
  assert.deepEqual(record.position,[-106,0,-49]);assert.deepEqual(record.rotation,[0,0,0]);
  const bus=sampleLiveBus(createCyberState(),'bus-brt');
  const entrance=busDoorPosition({...bus,heading:0,x:0,z:0});
  assert.ok(entrance.x>1.77,'entrance must be outside the measured right body edge');
  assert.ok(Math.abs(entrance.z-6.325)<.01,'entry aligns between Door_01_A and Door_01_B');
});

test('external terminal boarding has a continuous three-metre pedestrian path around the original monument',async()=>{
  const link=delivery.roadConnections.pedestrianLinks.find(p=>p.id==='passagem-terminal');assert.equal(link.width,3);
  assert.deepEqual(link.points,[[-106,-49],[-55,-49],[-55,-39],[-42,-39],[-42,-32],[-25,-32],[-25,-30]]);
  const terminal=delivery.compositions.find(p=>p.id==='delivery-terminal');
  assert.deepEqual(terminal.position,[-25,0,-51]);assert.deepEqual(terminal.rotation,[0,0,0]);
  assert.deepEqual(delivery.zones.find(p=>p.id===terminal.id).approach,[-25,0,-30]);
  assert.equal(delivery.roadConnections.streets.some(s=>/^terminal-(frente|leste|oeste|retorno)$/.test(s.id)),false);
  const solids=[...await monumentFootprints(),...newDeliveryColliders,
    ...buildings.map(b=>({id:b.id,x:b.center[0],z:b.center[2],w:b.width+.26,d:b.depth+.26}))];
  for(let i=1;i<link.points.length;i++){
    const floor=deliveryRoadRectangle(link.points[i-1],link.points[i],link.width);
    for(const solid of solids){
      const obstacle=deliveryRoadRectangle([solid.x-solid.w/2,solid.z],[solid.x+solid.w/2,solid.z],solid.d);
      const overlap=deliveryPolygonArea(floor)-subtractDeliveryPolygon(floor,obstacle).reduce((area,p)=>area+deliveryPolygonArea(p),0);
      assert.ok(overlap<1e-5,`${solid.id}: pedestrian leg ${i}`);
    }
  }
});

test('the measured articulated bus clears buildings and preserved center props throughout its paved centerline',async()=>{
  const route=BUS_BRT_ROUTE,path=buildBusPath(route),definition=BUS_DEFINITIONS['bus-brt'];
  const solids=[...buildings.map(b=>({id:b.id,x:b.center[0],z:b.center[2],w:b.width+.26,d:b.depth+.26})),...newDeliveryColliders,
    ...originalCenterFootprints(),...await monumentFootprints()];
  assert.ok(solids.some(s=>s.id==='PLAZA_Base'));assert.ok(solids.some(s=>s.id==='STAT_LanguageBase_JavaScript'));
  assert.ok(solids.some(s=>s.id==='TELEPORT_Ring_1'));assert.ok(solids.some(s=>s.id.startsWith('PROP_Brain_Real')));
  const asphalt=[...delivery.roadConnections.existingRoads.map(r=>deliveryRoadRectangle(r.from,r.to,r.width)),
    ...buildDeliveryRoadSurfaces().filter(s=>s.material==='asfalto').map(s=>s.points)];
  let state=createCyberState(),articulated=false;
  for(let elapsed=0;elapsed<path.cycle;elapsed+=.05){
    const bus=sampleLiveBus(state,'bus-brt'),c=Math.cos(bus.heading),s=Math.sin(bus.heading);
    assert.equal(busPositionBlocked(bus,solids.filter(s=>!s.id.startsWith('delivery-stop-'))),false,`complete bounds at second ${elapsed.toFixed(2)}`);
    articulated ||= Math.abs(bus.articulationAngle)>.05;
    for(const polygon of busFootprintPolygons(bus))for(const solid of solids){
      const obstacle=deliveryRoadRectangle([solid.x-solid.w/2,solid.z],[solid.x+solid.w/2,solid.z],solid.d);
      const overlap=deliveryPolygonArea(polygon)-subtractDeliveryPolygon(polygon,obstacle).reduce((area,p)=>area+deliveryPolygonArea(p),0);
      assert.ok(overlap<1e-5,`${solid.id} at route second ${elapsed.toFixed(2)}`);
    }
    for(const offset of [-definition.width/2,0,definition.width/2]){
      const point=[bus.x+offset*c,bus.z-offset*s];
      assert.ok(asphalt.some(p=>deliveryPointInPolygon(point,p)),`uncovered bus lane at second ${elapsed.toFixed(2)}`);
    }
    state=tickCyberState(state,.05);
  }
  assert.equal(articulated,true,'audit must include the moving rear section');
});

test('disembarking clears the walking collider at every parking angle and refuses blocked exits',()=>{
  for(const id of BUS_IDS)for(const heading of [0,Math.PI/4,Math.PI/2,Math.PI,-Math.PI/4]){
    let state=action(action(boardingState(id),'BOARD',{vehicle:id}),'BUS_TAKE_WHEEL');
    const bus={...sampleLiveBus(state,id),x:20,z:0,heading};
    state={...state,liveBuses:{...state.liveBuses,[id]:bus},position:busSeatPosition(bus,'driver')};
    const exited=applyCyberAction(state,{type:'EXIT'},{obstacles:[]});assert.equal(exited.ok,true,exited.message);
    const box=busFootprint(bus),side=Math.sign(BUS_DEFINITIONS[id].door[0]);
    const moved=advanceCityPosition(exited.state.position,{x:side*Math.cos(heading),z:-side*Math.sin(heading)},.05,5,[box],.4);
    assert.ok(distance(moved,exited.state.position)>.2,`${id}, heading ${heading}: exit must allow walking`);
    const blocked=applyCyberAction(state,{type:'EXIT'},{obstacles:[{id:'closed-yard',x:20,z:0,w:200,d:200}]});
    assert.equal(blocked.ok,false);assert.equal(blocked.state,state);
  }
});

test('closed doors prevent boarding while a blocked automatic return stops before walls and can be resumed manually',()=>{
  let state=boardingState('bus-brt'),bus=sampleLiveBus(state,'bus-brt');
  assert.equal(canBoardBus(state,{...bus,doorOpen:false}),false);
  state=action(action(state,'BOARD',{vehicle:'bus-brt'}),'BUS_TAKE_WHEEL');
  bus={...sampleLiveBus(state,'bus-brt'),x:-56,z:-49,heading:0};
  state={...state,liveBuses:{...state.liveBuses,'bus-brt':bus},position:busSeatPosition(bus,'driver')};
  assert.equal(busPositionBlocked(bus),false,'initial off-route parking is clear');
  state=returnBusToRoute(state,'bus-brt');
  state={...state,busControls:{vehicleId:'bus-brt',role:'passenger'}};
  let blocked=false;
  for(let step=0;step<100;step++){
    state=tickCyberState(state,.05);bus=sampleLiveBus(state,'bus-brt');
    assert.equal(busPositionBlocked(bus),false,'neither translation nor steering may enter a wall');
    if(bus.returnBlocked){blocked=true;break;}
  }
  assert.equal(blocked,true);assert.equal(bus.engineOn,false);assert.equal(bus.doorOpen,true);
  const before={...bus};state=tickCyberState(state,.05);bus=sampleLiveBus(state,'bus-brt');
  assert.equal(distance(before,bus),0);assert.equal(before.heading,bus.heading);
  state=action(state,'BUS_TAKE_WHEEL');assert.equal(sampleLiveBus(state,'bus-brt').control,'player');
  assert.equal(sampleLiveBus(state,'bus-brt').returnBlocked,false);
});

test('both NPC buses circulate for 600 seconds without overlapping their measured articulated polygons or jumping after waits',()=>{
  let state=createCyberState(),waitSamples=0,resumed=0;
  const travel=Object.fromEntries(BUS_IDS.map(id=>[id,0]));
  for(let step=0;step<12000;step++){
    const previous=Object.fromEntries(BUS_IDS.map(id=>[id,sampleLiveBus(state,id)]));
    state=tickCyberState(state,.05);
    const buses=BUS_IDS.map(id=>sampleLiveBus(state,id));
    assert.ok(busOverlapArea(...buses)<1e-5,`measured body overlap at ${state.elapsed.toFixed(2)} s`);
    for(const bus of buses){
      const before=previous[bus.id],moved=distance(before,bus);travel[bus.id]+=moved;
      assert.ok(moved<=BUS_ROUTES[bus.id].speed*.05+.021,`${bus.id}: no catch-up teleport`);
      if(bus.trafficWaiting){
        waitSamples++;assert.equal(bus.stopped,true);assert.equal(bus.speed,0);
        assert.equal(moved,0);assert.equal(bus.wheelAngle,before.wheelAngle);
      }else if(before.trafficWaiting&&moved>0)resumed++;
    }
  }
  assert.ok(waitSamples>0,'faster bus must wait behind the stopped BRT');
  assert.ok(resumed>0,'a temporary queue must clear automatically');
  for(const id of BUS_IDS)assert.ok(travel[id]>2000,`${id}: both buses must keep circulating through several cycles`);
});

test('an NPC waits behind a parked player bus, keeps its passenger seated and resumes its own paused route clock',()=>{
  let state=createCyberState();
  state={...state,mode:'bus',busControls:{vehicleId:'bus',role:'passenger'},
    liveBuses:{...state.liveBuses,'bus-brt':{...sampleLiveBus(state,'bus-brt'),x:30,z:35,heading:Math.PI/2,control:'player',stopped:true,speed:0}}};
  let waited=false;
  for(let step=0;step<600;step++){
    state=tickCyberState(state,.05);const bus=sampleLiveBus(state,'bus');
    assert.ok(busOverlapArea(bus,sampleLiveBus(state,'bus-brt'))<1e-5);
    assert.deepEqual(state.position,busSeatPosition(bus));
    waited ||= bus.trafficWaiting;
  }
  assert.equal(waited,true);const held=sampleLiveBus(state,'bus');
  assert.equal(held.trafficWaiting,true);assert.equal(held.doorOpen,false);
  state={...state,liveBuses:{...state.liveBuses,'bus-brt':{...state.liveBuses['bus-brt'],x:70,z:0}}};
  for(let step=0;step<80;step++){
    const before=sampleLiveBus(state,'bus');state=tickCyberState(state,.05);const bus=sampleLiveBus(state,'bus');
    assert.ok(distance(before,bus)<=BUS_ROUTES.bus.speed*.05+.021);
    assert.deepEqual(state.position,busSeatPosition(bus));
  }
  assert.equal(sampleLiveBus(state,'bus').trafficWaiting,false);
  assert.ok(distance(held,sampleLiveBus(state,'bus'))>20);
});

test('a returning bus waits for another bus and rejoins continuously when traffic clears',()=>{
  let state=createCyberState();
  const bus={...sampleLiveBus(state,'bus'),x:0,z:15,heading:0,control:'player',stopped:true};
  const blocker={...sampleLiveBus(state,'bus-brt'),x:0,z:41.5,heading:0,control:'player',stopped:true,speed:0};
  state=returnBusToRoute({...state,mode:'bus',busControls:{vehicleId:'bus',role:'passenger'},liveBuses:{bus,'bus-brt':blocker}},'bus');
  let waited=false;
  for(let step=0;step<200;step++){
    const before=sampleLiveBus(state,'bus');state=tickCyberState(state,.05,{obstacles:[]});const after=sampleLiveBus(state,'bus');
    assert.ok(busOverlapArea(after,sampleLiveBus(state,'bus-brt'))<1e-5);
    assert.ok(distance(before,after)<=BUS_ROUTES.bus.speed*.05+.021);
    waited ||= after.trafficWaiting;
  }
  assert.equal(waited,true);assert.equal(sampleLiveBus(state,'bus').control,'rejoin');
  assert.equal(sampleLiveBus(state,'bus').returnBlocked,false);
  state={...state,liveBuses:{...state.liveBuses,'bus-brt':{...blocker,x:70,z:0}}};
  let rejoined=false;
  for(let step=0;step<400;step++){
    const before=sampleLiveBus(state,'bus');state=tickCyberState(state,.05,{obstacles:[]});const after=sampleLiveBus(state,'bus');
    assert.ok(distance(before,after)<=BUS_ROUTES.bus.speed*.05+.021);
    assert.ok(busOverlapArea(after,sampleLiveBus(state,'bus-brt'))<1e-5);
    assert.deepEqual(state.position,busSeatPosition(after));
    if(after.control==='npc'){rejoined=true;break;}
  }
  assert.equal(rejoined,true);
});

test('an NPC can move away when a player parks inside the preferred gap without touching its body',()=>{
  let state=createCyberState();state={...state,elapsed:9.2,
    liveBuses:{...state.liveBuses,'bus-brt':{...sampleLiveBus(state,'bus-brt'),x:-15.915,z:35,heading:Math.PI/2,articulationAngle:0,control:'player',stopped:true,speed:0}}};
  const initial=sampleLiveBus(state,'bus');assert.ok(busOverlapArea(initial,sampleLiveBus(state,'bus-brt'))<1e-5);
  for(let step=0;step<100;step++){
    const before=sampleLiveBus(state,'bus');state=tickCyberState(state,.05,{obstacles:[]});const bus=sampleLiveBus(state,'bus');
    assert.ok(busOverlapArea(bus,sampleLiveBus(state,'bus-brt'))<1e-5);
    assert.ok(distance(before,bus)<=BUS_ROUTES.bus.speed*.05+.021);
    assert.equal(Boolean(bus.trafficWaiting),false,'clearance preference must not trap a separating vehicle');
  }
  assert.ok(distance(initial,sampleLiveBus(state,'bus'))>40);
});

test('a returning bus refuses a turn that would sweep through a thin wall even when its final pose is clear',()=>{
  let state=createCyberState();const bus={...sampleLiveBus(state,'bus'),x:0,z:35,heading:0,control:'player',stopped:true};
  state=returnBusToRoute({...state,liveBuses:{...state.liveBuses,bus}},'bus');
  const wall={id:'thin-wall',x:0,z:41.35,w:.1,d:.01};
  assert.equal(busPositionBlocked(bus,[wall]),false);
  assert.equal(busPositionBlocked({...bus,heading:.2},[wall]),true,'the intermediate turn hits the wall');
  assert.equal(busPositionBlocked({...bus,heading:.4},[wall]),false,'the final pose alone misses that collision');
  state=tickCyberState(state,.5,{obstacles:[wall]});const held=sampleLiveBus(state,'bus');
  assert.equal(held.returnBlocked,true);assert.equal(held.heading,bus.heading);
  assert.equal(distance(held,bus),0);assert.equal(held.wheelAngle,bus.wheelAngle);
});
