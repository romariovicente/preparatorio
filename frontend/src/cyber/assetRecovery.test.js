import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import manifest from '../config/cloudAssetManifest.json' with {type:'json'};
import {createAssetRecoveryStore,createAssetRetryResolver,resolveAssetRetryUrls} from './assetRecovery.js';
// Node resolves Drei/Fiber through CJS. Use that same real cache instance and
// loader constructor here; production Vite consistently selects their ESM build.
const require=createRequire(import.meta.url);
const {suspend,clear}=require('suspend-react');
const {GLTFLoader}=require('three-stdlib');

const chairPath='/assets/additions20261020/PROP_Hospital_Lounge_Chair_20261020.glb';
const hospitalPath='/assets/environments/ENV_Hospital_Reception_Module_20261015.glb';

test('transient GLTF failure stays cached until an explicit recovery clears the real loader key and permits success',async()=>{
  const url=resolveAssetRetryUrls([chairPath])[0],keys=[GLTFLoader,url];assert.ok(url);clear(keys);
  const store=createAssetRecoveryStore(),snapshots=[];
  const stop=store.subscribe(()=>snapshots.push(store.getSnapshot()));
  let calls=0,nextRequest,resets=0;
  const loader=()=>{calls++;return calls===1?Promise.reject(new Error(`Could not load ${url}: Failed to fetch`)):Promise.resolve({chair:'loaded'});};
  try{suspend(loader,keys);}catch(request){await request;}
  let failed;
  try{suspend(loader,keys);}catch(error){failed=error;}
  const player={position:{x:48,y:.272,z:-30},doors:{hospital:{open:true}},chairs:'original fallback'},before=structuredClone(player);
  const unregister=store.register({key:'chair-boundary',error:failed,urls:[url],retry:()=>{
    resets++;try{suspend(loader,keys);}catch(request){nextRequest=request;}
  }});
  assert.equal(store.getSnapshot(),1);assert.equal(calls,1);
  for(let render=0;render<3;render++)assert.throws(()=>suspend(loader,keys),/Failed to fetch/);
  assert.equal(calls,1,'rerenders and a registered failure cannot silently repeat network traffic');
  assert.equal(store.retryFailed(),1);assert.equal(resets,1);assert.equal(calls,2);
  await nextRequest;assert.deepEqual(suspend(loader,keys),{chair:'loaded'});
  assert.equal(store.getSnapshot(),0);assert.deepEqual(snapshots,[1,0]);
  assert.deepEqual(player,before,'recovery changes the failed asset cache/subtree, not gameplay or open doors');
  assert.equal(store.retryFailed(),0);assert.equal(calls,2);
  unregister();stop();clear(keys);
});

test('one click clears shared failed keys once, while a second failure waits for another click',()=>{
  const url=resolveAssetRetryUrls([hospitalPath])[0],cleared=[],store=createAssetRecoveryStore({clearCache:value=>cleared.push(value)});
  let first=0,second=0;
  store.register({key:'first',urls:[url],retry:()=>{first++;}});
  store.register({key:'second',urls:[url],retry:()=>{second++;}});
  assert.equal(store.getSnapshot(),2);assert.equal(store.retryFailed(),2);
  assert.deepEqual(cleared,[url]);assert.equal(first,1);assert.equal(second,1);
  store.register({key:'first',urls:[url],retry:()=>{first++;}});
  assert.equal(store.getSnapshot(),1);assert.equal(first,1,'failure registration is not an automatic retry');
  assert.equal(store.retryFailed(),1);assert.equal(first,2);assert.deepEqual(cleared,[url,url]);
});

test('only approved public model URLs may be recovered; private, withheld, unknown and credentialed URLs stay excluded',()=>{
  const canonical=resolveAssetRetryUrls([chairPath])[0];assert.ok(canonical);
  assert.deepEqual(resolveAssetRetryUrls(undefined,new Error(`Could not load ${canonical}: Failed to fetch`)),[canonical]);
  const withheld=Object.entries(manifest).find(([,url])=>url===null);assert.ok(withheld);
  const rejected=[withheld[0],'/assets/private-house.glb','blob:https://example.com/private-model',
    'https://example.com/not-in-catalog.glb',canonical+'?token=private',canonical+'#private',
    manifest[chairPath].replace('https://','https://user:secret@')];
  for(const value of rejected){
    assert.deepEqual(resolveAssetRetryUrls([value]),[],value);
    assert.deepEqual(resolveAssetRetryUrls(undefined,new Error(`Could not load ${value}: Failed to fetch`)),[],value);
  }
  const store=createAssetRecoveryStore({clearCache:()=>{throw new Error('unapproved cache key cleared');}});
  for(const value of rejected)store.register({key:value,urls:[value],retry:()=>{throw new Error('unapproved subtree retried');}});
  assert.equal(store.getSnapshot(),0);assert.equal(store.retryFailed(),0);
  assert.deepEqual(resolveAssetRetryUrls(undefined,new Error('Unrelated application failure')),[]);
});

test('a fresh catalog resolver rejects withheld model entries and malformed optional URLs even if development would serve them',()=>{
  const resolve=createAssetRetryResolver({assetManifest:{'/assets/allowed.glb':'https://cdn.example/allowed.glb','/assets/private.glb':null,
    '/assets/invalid.glb':'javascript:invalid','/assets/missing.glb':undefined},resolveUrl:path=>path==='/assets/invalid.glb'?'javascript:invalid':path==='/assets/missing.glb'?undefined:path});
  assert.deepEqual(resolve(['/assets/allowed.glb']),['/assets/allowed.glb']);
  for(const url of ['/assets/private.glb','/assets/invalid.glb','/assets/missing.glb',null,{},42])assert.deepEqual(resolve([url]),[]);
});

test('unmounted boundaries unregister their failures and earlier cleanup cannot erase a newer failure',()=>{
  const store=createAssetRecoveryStore({clearCache:()=>{}}),url=resolveAssetRetryUrls([chairPath])[0];
  let notices=0;const unsubscribe=store.subscribe(()=>{notices++;});
  const old=store.register({key:'chair',urls:[url],retry:()=>{}});
  const current=store.register({key:'chair',urls:[url],retry:()=>{}});
  assert.equal(store.getSnapshot(),1);old();assert.equal(store.getSnapshot(),1);
  current();assert.equal(store.getSnapshot(),0);assert.equal(store.retryFailed(),0);
  unsubscribe();store.register({key:'other',urls:[url],retry:()=>{}});assert.equal(notices,2);
});
