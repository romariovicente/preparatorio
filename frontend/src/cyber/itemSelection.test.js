import test from 'node:test';
import assert from 'node:assert/strict';
import {cycleItem} from './itemSelection.js';
test('Q/E wrap through bases and owned copies without selecting another player inventory',()=>{
  const objects=[{id:'a',kind:'base'},{id:'foreign',kind:'copy',ownerId:'other'},{id:'b',kind:'copy',ownerId:'me'}];
  assert.equal(cycleItem(objects,null,1,'me').id,'a');assert.equal(cycleItem(objects,'a',1,'me').id,'b');
  assert.equal(cycleItem(objects,'b',1,'me').id,'a');assert.equal(cycleItem(objects,'a',-1,'me').id,'b');
  assert.equal(cycleItem([],null,1,'me'),null);
});
