import test from 'node:test';
import assert from 'node:assert/strict';
import { createDemoServer } from './server.js';
import { createSharedTransport } from '../frontend/src/network/sharedTransport.js';

const memoryStorage = () => {
  const data=new Map();return {getItem:key=>data.get(key) ?? null,setItem:(key,value)=>data.set(key,value)};
};
async function waitFor(predicate) {
  const end=Date.now()+3000;
  while(Date.now()<end){if(predicate())return;await new Promise(done=>setTimeout(done,10));}
  assert.fail('Browser transport did not receive the shared state.');
}

test('frontend SSE transport shares objects across separate tab stores and resumes its own session',async t=>{
  const server=createDemoServer();await new Promise(done=>server.listen(0,'127.0.0.1',done));
  const baseUrl=`http://127.0.0.1:${server.address().port}`,storageA=memoryStorage(),storageB=memoryStorage();
  let snapshotA,snapshotB,actorA,actorB,statusA,statusB;
  const a=createSharedTransport({baseUrl,storage:storageA,onSnapshot:s=>{snapshotA=s;},onStatus:(status,id)=>{statusA=status;actorA=id ?? actorA;}});
  const b=createSharedTransport({baseUrl,storage:storageB,onSnapshot:s=>{snapshotB=s;},onStatus:(status,id)=>{statusB=status;actorB=id ?? actorB;}});
  const connections=[a.connect('campus'),b.connect('campus')];
  t.after(async()=>{a.close();b.close();await Promise.all(connections);await server.closeDemo();});
  await waitFor(()=>statusA==='connected' && statusB==='connected' && snapshotA && snapshotB);
  assert.notEqual(actorA,actorB);
  await a.publishPosition({x:-3,y:0,z:4.5},{animation:'Dance',heading:.5});
  await b.publishPosition({x:-3,y:0,z:4.5},{animation:'Idle'});
  const [pickA,pickB]=await Promise.all([a.action({type:'PICKUP',objectId:'base:campus_kit',actorId:actorB}),b.action({type:'PICKUP',objectId:'base:campus_kit'})]);
  assert.equal(pickA.ok,true);assert.equal(pickB.ok,true);
  await waitFor(()=>snapshotA.state.objects.filter(o=>o.kind==='copy').length===2 && snapshotB.state.objects.filter(o=>o.kind==='copy').length===2);
  assert.equal(snapshotB.state.objects.find(o=>o.id===pickA.createdId).ownerId,actorA);
  assert.equal(snapshotB.state.players[actorA].animation,'Dance');
  assert.equal((await b.action({type:'RETURN',objectId:pickA.createdId})).ok,false);
  a.close();await connections[0];
  let resumed;
  const reload=createSharedTransport({baseUrl,storage:storageA,onSnapshot:s=>{resumed=s;}});
  const reloading=reload.connect('campus');
  await waitFor(()=>resumed?.actorId===actorA);
  assert.equal(resumed.state.players[actorA].carriedId,pickA.createdId);
  reload.close();await reloading;
});

test('frontend reconnects after an actual same-port server restart and accepts the new actor and lower revision',async t=>{
  let server=createDemoServer();await new Promise(done=>server.listen(0,'127.0.0.1',done));
  const port=server.address().port,storage=memoryStorage(),baseUrl=`http://127.0.0.1:${port}`;
  let snapshot,status,actor,highestRevision=-1;
  const transport=createSharedTransport({baseUrl,storage,onStatus:(value,id)=>{status=value;actor=id ?? actor;},onSnapshot:value=>{snapshot=value;highestRevision=Math.max(highestRevision,value.revision);}});
  const connecting=transport.connect('campus');
  t.after(async()=>{transport.close();await connecting;await server.closeDemo();});
  await waitFor(()=>status==='connected' && snapshot);
  const originalActor=actor;
  await transport.publishPosition({x:-3,y:0,z:4.5});
  const picked=await transport.action({type:'PICKUP',objectId:'base:campus_kit'});assert.equal(picked.ok,true);
  const beforeRestartRevision=highestRevision;
  await server.closeDemo();
  await waitFor(()=>status==='offline');
  assert.equal((await transport.action({type:'PICKUP',objectId:'base:campus_kit'})).ok,false);
  server=createDemoServer();await new Promise(done=>server.listen(port,'127.0.0.1',done));
  await waitFor(()=>status==='connected' && actor!==originalActor && snapshot.actorId===actor);
  assert.ok(snapshot.revision<beforeRestartRevision);
  assert.equal(snapshot.state.objects.filter(o=>o.kind==='copy').length,0);
  assert.ok(snapshot.state.players[actor]);
  await transport.publishPosition({x:-3,y:0,z:4.5});
  const freshCopy=await transport.action({type:'PICKUP',objectId:'base:campus_kit'});
  assert.equal(freshCopy.ok,true);assert.equal(freshCopy.state.objects.find(o=>o.id===freshCopy.createdId).ownerId,actor);
});
