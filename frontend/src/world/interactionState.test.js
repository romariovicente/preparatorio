import test from 'node:test';
import assert from 'node:assert/strict';
import {carriedObject,createInteractionState,reduceInteraction,restoreInteractionState} from './interactionState.js';
const templates=[{id:'kit',name:'Kit',position:{x:0,y:.8,z:0},portable:true,movable:false},{id:'chair',name:'Cadeira',position:{x:3,y:0,z:0},portable:false,movable:true}];
const options={templates,playerPosition:{x:0,z:1},bounds:{minX:-5,maxX:5,minZ:-5,maxZ:5},obstacles:[{x:0,z:-3,w:2,d:1}]};
const cmd=(type,objectId,actorId='one',eventId='event1',extra={})=>({type,objectId,actorId,eventId,...extra});

test('two players receive separate carried copies while the authored base stays unchanged',()=>{
  const original=createInteractionState(templates);
  const first=reduceInteraction(original,cmd('PICKUP','base:kit'),options);
  const second=reduceInteraction(first.state,cmd('PICKUP','base:kit','two','event2'),options);
  assert.equal(first.ok,true);assert.equal(second.ok,true);
  assert.deepEqual(second.state.objects.find(o=>o.id==='base:kit'),original.objects[0]);
  assert.notEqual(carriedObject(second.state,'one').id,carriedObject(second.state,'two').id);
  assert.equal(second.state.objects.filter(o=>o.kind==='copy').length,2);
  assert.equal(reduceInteraction(second.state,cmd('PICKUP','base:kit','one','event3'),options).ok,false);
  assert.equal(reduceInteraction(second.state,cmd('DROP',carriedObject(second.state,'one').id,'two','event4',{position:{x:1,z:1}}),options).ok,false);
});
test('copies can be used, dropped, recollected and returned without duplication or cross-owner access',()=>{
  const pickup=reduceInteraction(createInteractionState(templates),cmd('PICKUP','base:kit'),options);
  const id=pickup.createdId;
  const used=reduceInteraction(pickup.state,cmd('USE',id,'one','use'),options);assert.equal(used.ok,true);
  const drop=reduceInteraction(used.state,cmd('DROP',id,'one','drop',{position:{x:1,y:0,z:1}}),options);
  assert.equal(drop.ok,true);assert.equal(carriedObject(drop.state,'one'),null);
  const recollect=reduceInteraction(drop.state,cmd('PICKUP',id,'one','recollect'),options);
  assert.equal(recollect.state.objects.length,3);assert.equal(carriedObject(recollect.state,'one').id,id);
  const returned=reduceInteraction(recollect.state,cmd('RETURN',id,'one','return'),options);
  assert.equal(returned.state.objects.length,2);assert.equal(carriedObject(returned.state,'one'),null);
  assert.equal(reduceInteraction(returned.state,cmd('RETURN','base:kit','one','bad'),options).ok,false);
});
test('placement refuses occupied, distant, out-of-bounds and static-furniture destinations',()=>{
  const pickup=reduceInteraction(createInteractionState(templates),cmd('PICKUP','base:kit'),options);
  for(const position of [{x:0,z:0},{x:0,z:-3},{x:6,z:1},{x:4,z:4},{x:NaN,z:0},{x:1,y:100,z:1}])assert.equal(reduceInteraction(pickup.state,cmd('DROP',pickup.createdId,'one',JSON.stringify(position),{position}),options).ok,false);
  const far={...options,playerPosition:{x:-4,z:4}};
  assert.equal(reduceInteraction(createInteractionState(templates),cmd('PICKUP','base:kit'),far).ok,false);
});
test('moving base furniture makes a personal copy and conflicting or replayed commands are rejected',()=>{
  const original=createInteractionState(templates),near={...options,playerPosition:{x:2,z:1}};
  const move=reduceInteraction(original,cmd('MOVE','base:chair','one','move',{position:{x:2,y:0,z:2},expectedRevision:0}),near);
  assert.equal(move.ok,true);assert.deepEqual(move.state.objects[1],original.objects[1]);
  assert.equal(reduceInteraction(move.state,cmd('MOVE','base:chair','one','move',{position:{x:2,z:2}}),near).ok,false);
  const moved=reduceInteraction(move.state,cmd('MOVE',move.createdId,'one','move2',{position:{x:1,z:2},expectedRevision:0}),near);
  assert.equal(moved.ok,true);
  assert.equal(reduceInteraction(moved.state,cmd('MOVE',move.createdId,'one','stale',{position:{x:2,z:2},expectedRevision:0}),near).ok,false);
});
test('saved state ignores unfamiliar objects and other owners while keeping authored bases intact',()=>{
  const initial=createInteractionState(templates);
  const corrupt={...initial,objects:[{...initial.objects[0],position:{x:4,y:0,z:4}},{...initial.objects[1],templateId:'missing'},
    {id:'item:two:test',templateId:'kit',kind:'copy',ownerId:'two',position:{x:1,z:1},revision:0}]};
  const restored=restoreInteractionState(corrupt,templates,'one',options);
  assert.deepEqual(restored.objects,initial.objects);assert.equal(carriedObject(restored,'one'),null);
});
