import test from 'node:test';
import assert from 'node:assert/strict';
import {directionKey,setDirectionKey,textEntryTarget} from './directionControls.js';
test('arrow keys and WASD share all four directions, including capital letters',()=>{
  for(const [letter,arrow]of [['w','ArrowUp'],['s','ArrowDown'],['a','ArrowLeft'],['d','ArrowRight']]){assert.equal(directionKey(letter),letter);assert.equal(directionKey(letter.toUpperCase()),letter);assert.equal(directionKey(arrow),letter);}
  assert.equal(directionKey('x'),null);
});
test('releasing one alias keeps a direction held by the other key',()=>{
  const held=new Set();setDirectionKey(held,'w',true);setDirectionKey(held,'ArrowUp',true);
  assert.equal(setDirectionKey(held,'w',false).pressed,true);assert.equal(setDirectionKey(held,'ArrowUp',false).pressed,false);
  setDirectionKey(held,'W',true);assert.equal(setDirectionKey(held,'w',false).pressed,false);
  assert.equal(textEntryTarget({closest:()=>({})}),true);assert.equal(textEntryTarget({closest:()=>null}),false);
});
