import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizePlayerName,readPlayerName,savePlayerName,normalizePlayerOutfit} from '../network/playerIdentity.js';

test('coat identity preserves Portuguese user names and bounds untrusted input',()=>{
  assert.equal(normalizePlayerName('  Ana   Luísa  '),'Ana Luísa');
  assert.equal(normalizePlayerName('José\u0000\u202e <Silva>'),'José Silva');
  assert.equal(Array.from(normalizePlayerName('😀'.repeat(80))).length,48);
  assert.equal(normalizePlayerName({name:'Alice'}),'Jogador');
  assert.equal(normalizePlayerName('  '),'Jogador');
});
test('each user session persists its own coat name, even if storage is unavailable',()=>{
  const storage=()=>{const values=new Map();return {getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};};
  const alice=storage(),bruno=storage();
  savePlayerName(alice,'Alice');savePlayerName(bruno,'Bruno');
  assert.equal(readPlayerName(alice),'Alice');assert.equal(readPlayerName(bruno),'Bruno');
  const blocked={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};
  assert.equal(readPlayerName(blocked),'Jogador');assert.equal(savePlayerName(blocked,'Maria'),'Maria');
});
test('remote coat state preserves garment choices and migrates every scrub color to white',()=>{
  assert.deepEqual(normalizePlayerOutfit({coat:true,color:'#37664b'}),{scrubs:true,coat:true,color:'#ffffff'});
  assert.deepEqual(normalizePlayerOutfit({scrubs:false,coat:false,color:'url(evil)'}),{scrubs:false,coat:false,color:'#ffffff'});
});
