import test from 'node:test';
import assert from 'node:assert/strict';
import {createDemoServer} from './server.js';
test('doors require a local authenticated player and their state is shared with a second player',async t=>{
  const server=createDemoServer();await new Promise(done=>server.listen(0,'127.0.0.1',done));t.after(()=>server.closeDemo());
  const base=`http://127.0.0.1:${server.address().port}`;
  const post=async(path,body,session)=>{const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json',...(session?{Authorization:`Bearer ${session.token}`}:{})},body:JSON.stringify(body)});return {status:r.status,...await r.json()};};
  const first=await post('/session',{}),second=await post('/session',{});
  assert.equal((await post('/door',{room:'cyber',doorId:'hospital',open:true})).status,401);
  assert.equal((await post('/door',{room:'cyber',doorId:'hospital',open:true},first)).status,409);
  await post('/position',{room:'cyber',position:{x:48,y:0,z:-21}},first);
  assert.equal((await post('/door',{room:'cyber',doorId:'hospital',open:true,actorId:second.actorId},first)).ok,true);
  const snapshot=await fetch(base+'/snapshot?room=cyber',{headers:{Authorization:`Bearer ${second.token}`}}).then(r=>r.json());
  assert.equal(snapshot.state.doors.hospital.open,true);assert.equal(snapshot.state.doors.hospital.revision,1);
  assert.equal((await post('/door',{room:'cyber',doorId:'hospital',open:false},second)).status,409);
  assert.equal((await post('/door',{room:'cyber',doorId:'not-real',open:true},first)).status,400);
});
