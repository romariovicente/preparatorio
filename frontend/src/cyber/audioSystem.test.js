import test from 'node:test';
import assert from 'node:assert/strict';
import {actionSound,createGameAudio} from './audioSystem.js';

class Param{
  value=0;events=[];
  setValueAtTime(v,t){this.value=v;this.events.push(['set',v,t]);}
  setTargetAtTime(v,t,c){this.value=v;this.events.push(['target',v,t,c]);}
  linearRampToValueAtTime(v,t){this.value=v;this.events.push(['ramp',v,t]);}
  cancelScheduledValues(t){this.events.push(['cancel',t]);}
}
class Node{
  gain=new Param();frequency=new Param();Q=new Param();pan=new Param();threshold=new Param();ratio=new Param();
  connections=[];started=[];stopped=[];disconnected=false;
  connect(n){this.connections.push(n);return n;}
  disconnect(){this.disconnected=true;}
  start(t){this.started.push(t);}
  stop(t){this.stopped.push(t);}
}
class Context{
  static created=[];
  currentTime=0;sampleRate=8000;state='suspended';destination=new Node();nodes=[];resumeCount=0;
  constructor(){Context.created.push(this);}
  node(kind){const node=new Node();node.kind=kind;this.nodes.push(node);return node;}
  createGain(){return this.node('gain');}
  createOscillator(){return this.node('oscillator');}
  createBufferSource(){return this.node('noise');}
  createBiquadFilter(){return this.node('filter');}
  createStereoPanner(){return this.node('panner');}
  createDynamicsCompressor(){return this.node('compressor');}
  createBuffer(_channels,length){return {getChannelData:()=>new Float32Array(length)};}
  async resume(){this.resumeCount++;this.state='running';}
  async close(){this.state='closed';}
  advance(dt){this.currentTime+=dt;for(const n of this.nodes)if(!n.ended&&n.onended&&n.stopped.some(t=>t!==undefined&&t<=this.currentTime)){n.ended=true;n.onended();}}
}
const state=(fields={})=>({mode:'foot',position:{x:0,y:0,z:25},action:'Idle',carControls:{engineOn:false,doorOpen:false},...fields});

test('all required game actions have original sound cues and unknown actions stay silent',()=>{
  for(const type of ['JUMP','JUMP_LAND','CAR_ENTER','CAR_DOOR','CAR_WINDOWS','CAR_ENGINE','DRIVE','BOARD','EXIT','BUS_TAKE_WHEEL','BUS_RELEASE_WHEEL','BUS_ENGINE','BUS_STOP','PARK','DOOR','TELEPORT','PICKUP','DROP','MOVE','USE','RETURN','FLOWER','DANCE','PLANT','HARVEST','SEEDS','CAST','REEL','ELEVATOR','OUTFIT','PHONE','MENU','JARVIS_ASK','JARVIS_REPLY'])assert.equal(typeof actionSound(type),'string',type);
  assert.equal(actionSound({type:'PICKUP'}),'pickup');assert.equal(actionSound('unknown'),null);
});

test('unsupported and locked audio do not construct nodes or interrupt gameplay',async()=>{
  const unsupported=createGameAudio({AudioContextCtor:null});assert.equal(await unsupported.unlock(),false);
  assert.equal(unsupported.play('JUMP'),false);assert.equal(unsupported.update(state(),.1),false);unsupported.dispose();
  const count=Context.created.length,audio=createGameAudio({AudioContextCtor:Context});
  audio.play('JUMP');audio.update(state(),.1);assert.equal(Context.created.length,count);
  assert.equal(await audio.unlock(),true);assert.equal(Context.created.length,count+1);
  assert.equal(await audio.unlock(),true);assert.equal(Context.created.length,count+1);audio.dispose();
});

test('voices are bounded, master mute is exactly zero, unmute restores volume and disposal releases every node',async()=>{
  const audio=createGameAudio({AudioContextCtor:Context});await audio.unlock();const ctx=Context.created.at(-1);
  audio.setVolume(.38);
  // Deliberately defer ended callbacks to exercise voice eviction as well as
  // the normal scheduled cleanup tested through Context.advance elsewhere.
  for(let i=0;i<100;i++){ctx.currentTime+=.08;audio.play('TELEPORT');}
  assert.ok(audio.getStatus().activeVoices<=32);
  assert.ok(ctx.nodes.some(node=>node.stopped.includes(undefined)));
  audio.setMuted(true);assert.equal(ctx.nodes.find(n=>n.kind==='gain').gain.value,0);assert.equal(audio.getStatus().activeVoices,0);
  assert.equal(audio.play('JUMP'),false);audio.setMuted(false);assert.equal(ctx.nodes.find(n=>n.kind==='gain').gain.value,.38);
  audio.update(state(),.1);audio.dispose();audio.dispose();assert.equal(audio.getStatus().activeVoices,0);
  assert.equal(ctx.state,'closed');assert.ok(ctx.nodes.every(n=>n.disconnected));assert.equal(await audio.unlock(),false);
});

test('ambient and engine loops are reused per frame, stop once and follow indoor/ocean/night changes',async()=>{
  const audio=createGameAudio({AudioContextCtor:Context});await audio.unlock();const ctx=Context.created.at(-1);
  audio.update(state(),.016);const first=ctx.nodes.length;
  for(let i=0;i<30;i++){ctx.advance(.016);audio.update(state(),.016);}
  assert.equal(ctx.nodes.length,first);assert.deepEqual(audio.getStatus().loops.sort(),['traffic','wind']);
  const car=state({mode:'car',carControls:{engineOn:true,doorOpen:false}});audio.update(car,.1);
  const engine=ctx.nodes.find(n=>n.kind==='oscillator'&&n.started.length&&n.type==='sawtooth'&&n.stopped.length===0),started=ctx.nodes.length;
  for(let i=0;i<20;i++){ctx.advance(.016);audio.update(car,.016);}
  assert.equal(ctx.nodes.length,started);assert.ok(audio.getStatus().loops.includes('engine'));
  audio.update(state(),.016);assert.equal(engine.stopped.length,1);assert.ok(!audio.getStatus().loops.includes('engine'));
  audio.update(state({position:{x:102,y:0,z:0},environment:{night:true}}),.016);
  assert.ok(audio.getStatus().loops.includes('ocean'));assert.ok(audio.getStatus().loops.includes('insects'));
  audio.update(state({environment:{indoor:true}}),.016);assert.deepEqual(audio.getStatus().loops,['room']);audio.dispose();
});

test('footsteps require actual ground distance; jump landing and elevator completion create transition cues',async()=>{
  const audio=createGameAudio({AudioContextCtor:Context});await audio.unlock();const ctx=Context.created.at(-1);
  audio.update(state(),.1);audio.update(state({action:'Walk'}),.1);assert.equal(audio.getStatus().lastSound,null);
  ctx.advance(.1);audio.update(state({position:{x:.7,y:0,z:25},action:'Walk'}),.14);assert.equal(audio.getStatus().lastSound,'step');
  ctx.advance(.1);audio.update(state({position:{x:70,y:0,z:25}}),.1);assert.equal(audio.getStatus().lastSound,'step');
  ctx.advance(.1);audio.update(state({jump:{startedAt:0},jumpHeight:.5}),.1);assert.equal(audio.getStatus().lastSound,'jump');
  ctx.advance(.2);audio.update(state(),.1);assert.equal(audio.getStatus().lastSound,'landing');
  ctx.advance(.2);audio.update(state({elevator:{to:-6}}),.1);assert.ok(audio.getStatus().loops.includes('elevator'));
  ctx.advance(.2);audio.update(state(),.1);assert.equal(audio.getStatus().lastSound,'elevator-stop');assert.ok(!audio.getStatus().loops.includes('elevator'));audio.dispose();
});

test('a shared door only sounds when its state changes nearby, and repeated snapshots stay silent',async()=>{
  const audio=createGameAudio({AudioContextCtor:Context});await audio.unlock();const ctx=Context.created.at(-1),p={x:48,y:0,z:-24.5};
  audio.update(state({position:p}),.1,{hospital:{open:false,revision:0}});assert.equal(audio.getStatus().lastSound,null);
  ctx.advance(.1);audio.update(state({position:p}),.1,{hospital:{open:true,revision:1}});assert.equal(audio.getStatus().lastSound,'door');
  const count=ctx.nodes.length;audio.update(state({position:p}),.1,{hospital:{open:true,revision:1}});assert.equal(ctx.nodes.length,count);
  ctx.advance(1);audio.update(state(),.1,{hospital:{open:false,revision:2}});assert.equal(ctx.nodes.length,count);audio.dispose();
});
