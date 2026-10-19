import test from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createDemoServer } from './server.js';

async function demo(t) {
  const server=createDemoServer();
  await new Promise(done=>server.listen(0,'127.0.0.1',done));
  const url=`http://127.0.0.1:${server.address().port}`;
  const controllers=[];
  t.after(async()=>{controllers.forEach(c=>c.abort());await server.closeDemo();});
  async function post(path,body,session,origin='http://127.0.0.1:5173') {
    const response=await fetch(url+path,{method:'POST',headers:{'Content-Type':'application/json',Origin:origin,...(session?{Authorization:`Bearer ${session.token}`}:{})},body:JSON.stringify(body)});
    return {status:response.status,...await response.json()};
  }
  const session=()=>post('/session',{});
  async function getState(player,room='campus') {
    return (await fetch(`${url}/snapshot?room=${room}`,{headers:{Authorization:`Bearer ${player.token}`}})).json();
  }
  async function events(player,room='campus') {
    const controller=new AbortController();controllers.push(controller);
    const response=await fetch(`${url}/events?room=${room}`,{headers:{Authorization:`Bearer ${player.token}`},signal:controller.signal});
    assert.equal(response.status,200);
    const snapshots=[],reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    (async()=>{
      try {
        while(true){const{value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let boundary;
          while((boundary=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const data=block.split('\n').find(line=>line.startsWith('data: '));if(data)snapshots.push(JSON.parse(data.slice(6)));}
        }
      }catch(error){if(error.name!=='AbortError')throw error;}
    })();
    return snapshots;
  }
  const action=(player,type,objectId,fields={},room='campus')=>post('/action',{room,type,objectId,eventId:randomUUID(),...fields},player);
  const position=(player,p,room='campus')=>post('/position',{room,position:p},player);
  return {url,post,session,getState,events,action,position};
}

async function until(predicate) {
  const end=Date.now()+3000;
  while(Date.now()<end){if(predicate())return;await new Promise(done=>setTimeout(done,10));}
  assert.fail('Shared snapshots did not arrive at both clients.');
}

test('two real HTTP clients receive distinct owned copies, preserve base, and cannot impersonate another owner',async t=>{
  const d=await demo(t),a=await d.session(),b=await d.session();assert.notEqual(a.actorId,b.actorId);
  const feedA=await d.events(a),feedB=await d.events(b);
  await d.position(a,{x:-3,y:0,z:4.5});await d.position(b,{x:-3,y:0,z:4.5});
  const before=await d.getState(a),base=before.state.objects.find(o=>o.id==='base:campus_kit');
  const [pickA,pickB]=await Promise.all([d.action(a,'PICKUP',base.id,{actorId:b.actorId,expectedRevision:0}),d.action(b,'PICKUP',base.id,{expectedRevision:0})]);
  assert.equal(pickA.ok,true);assert.equal(pickB.ok,true);assert.notEqual(pickA.createdId,pickB.createdId);
  const after=await d.getState(b);
  assert.deepEqual(after.state.objects.find(o=>o.id===base.id),base);
  assert.equal(after.state.objects.find(o=>o.id===pickA.createdId).ownerId,a.actorId);
  assert.equal(after.state.objects.find(o=>o.id===pickB.createdId).ownerId,b.actorId);
  const stolen=await d.action(b,'USE',pickA.createdId,{actorId:a.actorId});assert.equal(stolen.status,409);assert.equal(stolen.ok,false);
  const stolenReturn=await d.action(b,'RETURN',pickA.createdId);assert.equal(stolenReturn.ok,false);
  await until(()=>feedA.at(-1)?.revision===after.revision && feedB.at(-1)?.revision===after.revision);
  assert.equal(feedA.at(-1).state.objects.filter(o=>o.kind==='copy').length,2);
  assert.deepEqual(feedA.at(-1).state,feedB.at(-1).state);
  const drop=await d.action(a,'DROP',pickA.createdId,{position:{x:-4,y:0,z:4.5},expectedRevision:0});assert.equal(drop.ok,true);
  const ownReturn=await d.action(a,'RETURN',pickA.createdId,{expectedRevision:1});assert.equal(ownReturn.ok,true);
  assert.equal((await d.getState(a)).state.objects.filter(o=>o.kind==='copy').length,1);
});

test('server serializes competing revisions and validates bounds, room, origin, and hospital furniture footprints',async t=>{
  const d=await demo(t),a=await d.session();
  await d.position(a,{x:-3,y:0,z:4.5});
  const pick=await d.action(a,'PICKUP','base:campus_kit');
  const [first,second]=await Promise.all([d.action(a,'USE',pick.createdId,{expectedRevision:0}),d.action(a,'USE',pick.createdId,{expectedRevision:0})]);
  assert.deepEqual([first.ok,second.ok].sort(),[false,true]);
  assert.equal((await d.getState(a)).state.objects.find(o=>o.id===pick.createdId).uses,1);
  assert.equal((await d.position(a,{x:100,y:0,z:0})).status,400);
  assert.equal((await d.post('/action',{room:'unknown',type:'PICKUP',objectId:'base:campus_kit',eventId:randomUUID()},a)).status,400);
  assert.equal((await d.post('/session',{},null,'https://example.com')).status,403);
  await d.position(a,{x:3.1,y:0,z:-.3},'hospital');
  const hospitalBefore=await d.getState(a,'hospital'),cart=hospitalBefore.state.objects.find(o=>o.id==='base:hospital_cart');
  const blocked=await d.action(a,'MOVE',cart.id,{position:{x:0,y:0,z:-1.6}},'hospital');assert.equal(blocked.ok,false);
  const moved=await d.action(a,'MOVE',cart.id,{position:{x:3.1,y:0,z:-3}},'hospital');assert.equal(moved.ok,true);
  const hospitalAfter=await d.getState(a,'hospital');assert.deepEqual(hospitalAfter.state.objects.find(o=>o.id===cart.id),cart);
  assert.equal(hospitalAfter.state.objects.find(o=>o.id===moved.createdId).ownerId,a.actorId);
});
