import test from 'node:test';
import assert from 'node:assert/strict';
import {createSharedTransport} from './sharedTransport.js';

test('a public build without a service endpoint stays offline and never fetches a session',async context=>{
  const originalFetch=globalThis.fetch;
  context.after(()=>{globalThis.fetch=originalFetch;});
  let requests=0;
  globalThis.fetch=async()=>{requests++;throw new Error('No service should be contacted.');};
  const states=[];
  const transport=createSharedTransport({baseUrl:null,storage:null,onStatus:state=>states.push(state)});
  await transport.connect('city');
  assert.deepEqual(states,['offline']);
  assert.equal((await transport.action({type:'TAKE',objectId:'flower'})).ok,false);
  assert.equal((await transport.publishPosition({x:0,y:0,z:0})).ok,false);
  assert.equal((await transport.door('front',true)).ok,false);
  transport.close();
  assert.equal(requests,0);
});
