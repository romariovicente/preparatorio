import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createDemoServer } from './server.js';

async function demo(t) {
  const server=createDemoServer({rpgConfigPath:null});
  await new Promise(done=>server.listen(0,'127.0.0.1',done));
  const baseUrl=`http://127.0.0.1:${server.address().port}`,feeds=[];
  t.after(async()=>{feeds.forEach(feed=>feed.controller.abort());await server.closeDemo();});
  async function post(path,body,session) {
    const response=await fetch(baseUrl+path,{method:'POST',headers:{'Content-Type':'application/json',Origin:'http://127.0.0.1:5173',...(session?{Authorization:`Bearer ${session.token}`}:{})},body:JSON.stringify(body)});
    return {status:response.status,...await response.json()};
  }
  const session=()=>post('/session',{});
  async function snapshot(player,room='cyber') {
    const response=await fetch(`${baseUrl}/snapshot?room=${room}`,{headers:{Authorization:`Bearer ${player.token}`}});
    return {status:response.status,...await response.json()};
  }
  const position=(player,point,room='cyber')=>post('/position',{room,position:point},player);
  const action=(player,type,objectId,fields={},room='cyber')=>post('/action',{room,type,objectId,eventId:randomUUID(),...fields},player);
  async function events(player) {
    const feed={snapshots:[],error:null,controller:new AbortController()};feeds.push(feed);
    const response=await fetch(`${baseUrl}/events?room=cyber`,{headers:{Authorization:`Bearer ${player.token}`},signal:feed.controller.signal});
    assert.equal(response.status,200);
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    (async()=>{
      try {
        while(true) {
          const {value,done}=await reader.read();if(done)break;
          buffer+=decoder.decode(value,{stream:true});let boundary;
          while((boundary=buffer.indexOf('\n\n'))>=0) {
            const block=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);
            const data=block.split('\n').find(line=>line.startsWith('data: '));
            if(data)feed.snapshots.push(JSON.parse(data.slice(6)));
          }
        }
      } catch(error) {if(!feed.controller.signal.aborted)feed.error=error;}
    })();
    return feed;
  }
  return {session,snapshot,position,action,events};
}
async function until(predicate) {
  const end=Date.now()+3000;
  while(Date.now()<end){if(predicate())return;await new Promise(done=>setTimeout(done,10));}
  assert.fail('Both cyber clients did not receive the authoritative snapshot.');
}

test('two cyber HTTP/SSE players carry distinct flower copies and retain authored bases',async t=>{
  const d=await demo(t),a=await d.session(),b=await d.session();
  assert.notEqual(a.actorId,b.actorId);
  const feedA=await d.events(a),feedB=await d.events(b);
  const original=(await d.snapshot(a)).state.objects.filter(object=>object.kind==='base');
  assert.deepEqual(original.map(object=>object.templateId),['cyber_flower','cyber_bench','cyber_fishing_rod']);
  await d.position(a,{x:-10,y:0,z:15.5});await d.position(b,{x:-10,y:0,z:15.5});
  const [pickA,pickB]=await Promise.all([
    d.action(a,'PICKUP','base:cyber_flower',{actorId:b.actorId,expectedRevision:0}),
    d.action(b,'PICKUP','base:cyber_flower',{expectedRevision:0}),
  ]);
  assert.equal(pickA.ok,true);assert.equal(pickB.ok,true);assert.notEqual(pickA.createdId,pickB.createdId);
  const after=await d.snapshot(a);
  assert.deepEqual(after.state.objects.filter(object=>object.kind==='base'),original);
  assert.equal(after.state.objects.find(object=>object.id===pickA.createdId).ownerId,a.actorId);
  assert.equal(after.state.objects.find(object=>object.id===pickB.createdId).ownerId,b.actorId);
  assert.equal((await d.action(b,'USE',pickA.createdId,{actorId:a.actorId})).status,409);
  assert.equal((await d.action(b,'RETURN',pickA.createdId)).status,409);
  await until(()=>feedA.snapshots.at(-1)?.revision===after.revision && feedB.snapshots.at(-1)?.revision===after.revision);
  assert.equal(feedA.error,null);assert.equal(feedB.error,null);
  assert.deepEqual(feedA.snapshots.at(-1).state,feedB.snapshots.at(-1).state);
  assert.equal(feedB.snapshots.at(-1).state.players[a.actorId].carriedId,pickA.createdId);
  assert.equal((await d.action(a,'USE',pickA.createdId,{expectedRevision:0})).ok,true);
  assert.equal((await d.action(a,'DROP',pickA.createdId,{expectedRevision:1,position:{x:-10,y:0,z:17}})).ok,true);
  assert.equal((await d.action(a,'RETURN',pickA.createdId,{expectedRevision:2})).ok,true);
  assert.equal((await d.action(b,'RETURN',pickB.createdId,{expectedRevision:0})).ok,true);
  await d.position(b,{x:11,y:0,z:11.5});
  const rod=await d.action(b,'PICKUP','base:cyber_fishing_rod');
  assert.equal(rod.ok,true);
  assert.equal((await d.snapshot(a)).state.objects.find(object=>object.id===rod.createdId).templateId,'cyber_fishing_rod');
});

test('bench MOVE creates an owned copy, retains base footprint and rejects occupied targets',async t=>{
  const d=await demo(t),a=await d.session(),b=await d.session();
  await d.events(a);await d.events(b);
  await d.position(a,{x:-13.7,y:0,z:9.3});await d.position(b,{x:20,y:0,z:20});
  const base=(await d.snapshot(a)).state.objects.find(object=>object.id==='base:cyber_bench');
  const overlapping=await d.action(a,'MOVE',base.id,{position:{x:-13.7,y:0,z:8}});
  assert.equal(overlapping.status,409);
  const copy=await d.action(a,'MOVE',base.id,{position:{x:-15,y:0,z:8},expectedRevision:0});
  assert.equal(copy.ok,true);
  assert.deepEqual((await d.snapshot(a)).state.objects.find(object=>object.id===base.id),base);
  const stolen=await d.action(b,'MOVE',copy.createdId,{actorId:a.actorId,position:{x:20,y:0,z:21}});
  assert.equal(stolen.status,409);
  await d.position(a,{x:-15,y:0,z:9.5});await d.position(b,{x:-16.5,y:0,z:8});
  assert.equal((await d.action(a,'MOVE',copy.createdId,{position:{x:-16.5,y:0,z:8}})).status,409);
  assert.equal((await d.action(a,'MOVE',copy.createdId,{position:{x:-16.5,y:1,z:8}})).status,400);
  assert.equal((await d.action(a,'MOVE',copy.createdId,{position:{x:-18,y:0,z:9.5}})).ok,true);
});

test('cyber presence supports underground lift and seated heights while other room limits stay unchanged',async t=>{
  const d=await demo(t),a=await d.session(),b=await d.session();
  const feed=await d.events(b);await d.events(a);
  for(const y of [-6.5,-6,.52,1.1,2])assert.equal((await d.position(a,{x:0,y,z:35})).status,200);
  const stable=await d.snapshot(a);
  for(const p of [{x:0,y:-6.501,z:35},{x:0,y:2.001,z:35},{x:118.001,y:0,z:35},{x:0,y:0,z:-118.001}])assert.equal((await d.position(a,p)).status,400);
  assert.deepEqual((await d.snapshot(a)).state.players[a.actorId].position,stable.state.players[a.actorId].position);
  await d.position(a,{x:-17,y:-6,z:56});
  const underground=await d.snapshot(a);
  await until(()=>feed.snapshots.at(-1)?.revision===underground.revision);
  assert.equal(feed.snapshots.at(-1).state.players[a.actorId].position.y,-6);
  for(const room of ['campus','hospital']) {
    assert.equal((await d.position(a,{x:0,y:1.01,z:0},room)).status,400);
    assert.equal((await d.position(a,{x:0,y:-1.01,z:0},room)).status,400);
    assert.equal((await d.position(a,{x:0,y:1,z:0},room)).status,200);
    assert.equal((await d.position(a,{x:0,y:-1,z:0},room)).status,200);
  }
});

test('cyber cannot pick surface objects or drop a carried item through underground floors',async t=>{
  const d=await demo(t),a=await d.session();
  await d.position(a,{x:-10,y:-6,z:14});
  assert.equal((await d.action(a,'PICKUP','base:cyber_flower')).status,409);
  assert.equal((await d.action(a,'USE','base:cyber_flower')).status,409);
  await d.position(a,{x:-10,y:1.1,z:15.5});
  const pick=await d.action(a,'PICKUP','base:cyber_flower');assert.equal(pick.ok,true);
  await d.position(a,{x:-10,y:-6,z:15.5});
  assert.equal((await d.action(a,'DROP',pick.createdId,{position:{x:-10,y:0,z:17}})).status,409);
  assert.equal((await d.snapshot(a)).state.players[a.actorId].carriedId,pick.createdId);
  await d.position(a,{x:-10,y:0,z:15.5});
  assert.equal((await d.action(a,'DROP',pick.createdId,{position:{x:-10,y:0,z:17}})).ok,true);
  await d.position(a,{x:-3,y:0,z:4.5},'campus');
  assert.equal((await d.action(a,'PICKUP','base:campus_kit',{},'campus')).ok,true);
});
