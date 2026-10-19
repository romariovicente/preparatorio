import test from 'node:test';
import assert from 'node:assert/strict';
import {createDemoServer} from './server.js';

test('two authenticated local sessions retain distinct names, coats and seated poses',async t=>{
  const server=createDemoServer({rpgConfigPath:null});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  t.after(()=>server.closeDemo());
  const base=`http://127.0.0.1:${server.address().port}`;
  const post=async(path,body,session)=>{
    const response=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json',...(session?{Authorization:`Bearer ${session.token}`}:{})},body:JSON.stringify(body)});
    return {status:response.status,...await response.json()};
  };
  const a=await post('/session',{}),b=await post('/session',{});
  assert.notEqual(a.actorId,b.actorId);
  assert.equal((await post('/position',{room:'cyber',position:{x:0,y:0,z:25},displayName:'Ana Luísa',outfit:{coat:true,color:'#37664b'},sitting:false},a)).ok,true);
  assert.equal((await post('/position',{room:'cyber',position:{x:2,y:1.1,z:25},actorId:a.actorId,displayName:'Bruno',outfit:{coat:true,color:'#247fba'},sitting:true,mode:'bus-brt'},b)).ok,true);
  const snapshot=await (await fetch(base+'/snapshot?room=cyber',{headers:{Authorization:`Bearer ${a.token}`}})).json();
  assert.equal(snapshot.state.players[a.actorId].displayName,'Ana Luísa');
  assert.equal(snapshot.state.players[b.actorId].displayName,'Bruno');
  assert.equal(snapshot.state.players[a.actorId].outfit.color,'#37664b');
  assert.equal(snapshot.state.players[b.actorId].sitting,true);
  assert.equal(snapshot.state.players[b.actorId].mode,'bus-brt');
  assert.equal((await post('/position',{room:'cyber',position:{x:999,y:0,z:0},displayName:'Intruso'},b)).status,400);
  const after=await (await fetch(base+'/snapshot?room=cyber',{headers:{Authorization:`Bearer ${b.token}`}})).json();
  assert.equal(after.state.players[b.actorId].displayName,'Bruno');
  assert.equal(after.state.players[a.actorId].displayName,'Ana Luísa');
});
