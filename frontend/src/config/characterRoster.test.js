import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildCharacterRoster,characterSelectionOptions,resolveRosterCharacter,createCharacterRosterPlacements,characterRosterColliders,nearbyCharacterPlacements} from './characterRoster.js';

const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const originals=read('./suppliedAssets.json'),rigs=read('./riggedAssets.json'),reviews=read('./characterMotionReviews.json');
const assets=[...originals.map(asset=>{
  const rig=rigs.find(rig=>rig.id===asset.id);
  return {...asset,...rig,rigged:Boolean(rig||asset.originalRig),sourceUrl:asset.url,animations:rig?.clips??asset.animations};
}),...read('./mixamoAssets.json'),...read('./newDeliveryAssets.json').filter(asset=>asset.category==='character').map(asset=>({...asset,category:'Personagens',name:asset.label,rigged:false}))];
const roster=buildCharacterRoster(assets,originals,reviews);

test('all twenty character assets and twenty-one figures remain represented without an art-style exclusion',()=>{
  assert.equal(roster.length,20);assert.equal(roster.reduce((sum,entry)=>sum+entry.figures,0),21);
  const players=roster.filter(entry=>entry.controllable);
  assert.deepEqual(players.map(entry=>entry.id).sort(),['CHR_Remy_Mixamo_20261005','SUP_character_cyberpunk_free_3d_by_oscar_cre','SUP_lowpoly_anime_character_cyberstyle'].sort());
  assert.equal(players.filter(entry=>entry.locomotionValidated).length,2);
  assert.equal(players.find(entry=>entry.id==='SUP_lowpoly_anime_character_cyberstyle').visualStyle,'stylized');
  assert.equal(players.find(entry=>entry.controlMode==='fixed-pose').playerAsset.allowedCharacterActions.length,0);
  assert.equal(players.find(entry=>entry.id==='SUP_lowpoly_anime_character_cyberstyle').playerAsset.characterCapabilities.sitting,false);
  assert.equal(players.find(entry=>entry.id==='CHR_Remy_Mixamo_20261005').playerAsset.characterCapabilities.riding,true);
  assert.equal(characterSelectionOptions(roster).length,20);
});

test('legacy fitted FK derivatives never gain locomotion from old playable:true metadata',()=>{
  const legacy=roster.filter(entry=>entry.asset.quality==='prototype');assert.equal(legacy.length,16);
  assert.ok(legacy.every(entry=>!entry.controllable&&!entry.locomotionValidated&&entry.controlMode==='npc-static'));
  const seated=roster.find(entry=>entry.id==='SUP_woman_seated_v15');
  assert.equal(seated.pose,'seated');assert.equal(seated.height,1.22);assert.match(seated.context,/Leitura/);
  for(const entry of legacy.filter(entry=>entry.asset.needsRepose)){
    assert.equal(entry.displayUrl,originals.find(original=>original.id===entry.id).url);
    assert.equal(entry.standingPose,null);
  }
});

test('hash changes, missing files and incomplete native clips fail closed but do not erase a roster entry',()=>{
  const remy=assets.find(asset=>asset.id==='CHR_Remy_Mixamo_20261005');
  for(const altered of [{...remy,sha256:'new-file'}, {...remy,url:null}, {...remy,animations:['Idle']}, {...remy,needsRepose:true}]){
    const entry=buildCharacterRoster([altered],[],reviews)[0];
    assert.equal(entry.controllable,false);assert.equal(entry.playerAsset,null);
  }
  assert.equal(resolveRosterCharacter(roster,'SUP_woman_seated_v15'),null);
  assert.equal(resolveRosterCharacter(roster,'missing'),null);
  const source=JSON.stringify(assets);buildCharacterRoster(assets,originals,reviews);assert.equal(JSON.stringify(assets),source);
});

test('every actor gets a deterministic non-overlapping city position outside supplied obstacles',()=>{
  const colliders=[{x:25,z:0,w:10,d:10},{x:0,z:25,w:12,d:12}];
  const first=createCharacterRosterPlacements(roster,{colliders}),second=createCharacterRosterPlacements(roster,{colliders});
  assert.equal(first.allRepresented,true);assert.equal(first.unplaced.length,0);assert.deepEqual(first,second);
  for(let a=0;a<first.placements.length;a++){
    const position=first.placements[a].position;
    for(const box of colliders)assert.ok(Math.abs(position[0]-box.x)>=box.w/2+.65||Math.abs(position[2]-box.z)>=box.d/2+.65);
    for(let b=0;b<a;b++)assert.ok(Math.hypot(position[0]-first.placements[b].position[0],position[2]-first.placements[b].position[2])>=3.8);
  }
  assert.equal(characterRosterColliders(first.placements).length,20);
  const blocked=createCharacterRosterPlacements(roster,{colliders:[{x:0,z:0,w:1000,d:1000}]});
  assert.equal(blocked.allRepresented,false);assert.equal(blocked.unplaced.length,20);
});

test('proximity selects only nearest models within explicit count and byte budgets',()=>{
  const placements=createCharacterRosterPlacements(roster).placements;
  const first=placements[0].position;
  const nearby=nearbyCharacterPlacements(placements,{x:first[0],y:first[1],z:first[2]},{distance:20,maxVisible:3,maxBytes:120*1024*1024});
  assert.ok(nearby.length>0&&nearby.length<=3);assert.equal(nearby[0].id,placements[0].id);
  assert.ok(nearby.reduce((sum,entry)=>sum+entry.displayBytes,0)<=120*1024*1024);
  assert.equal(nearbyCharacterPlacements(placements,{x:9000,z:9000}).length,0);
  assert.equal(nearbyCharacterPlacements(placements,{x:NaN,z:0}).length,0);
  assert.equal(nearbyCharacterPlacements(placements,first,{maxBytes:0}).length,0);
});
