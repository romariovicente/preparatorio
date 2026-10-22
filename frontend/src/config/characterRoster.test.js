import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildCharacterRoster,characterSelectionOptions,resolveRosterCharacter,createCharacterRosterPlacements,characterRosterColliders,nearbyCharacterPlacements,hospitalPatientCharacters} from './characterRoster.js';

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
  assert.equal(players.length,20);assert.ok(players.every(entry=>entry.playerAsset?.playable));
  assert.equal(players.filter(entry=>entry.locomotionValidated).length,2);
  assert.equal(players.filter(entry=>entry.controlMode==='prototype-motion').length,11);
  assert.equal(players.filter(entry=>entry.controlMode==='static-pose').length,6);
  assert.equal(players.find(entry=>entry.id==='SUP_lowpoly_anime_character_cyberstyle').visualStyle,'stylized');
  assert.equal(players.find(entry=>entry.controlMode==='fixed-pose').playerAsset.allowedCharacterActions.length,0);
  assert.equal(players.find(entry=>entry.id==='SUP_lowpoly_anime_character_cyberstyle').playerAsset.characterCapabilities.sitting,false);
  assert.equal(players.find(entry=>entry.id==='CHR_Remy_Mixamo_20261005').playerAsset.characterCapabilities.riding,true);
  assert.equal(characterSelectionOptions(roster).length,20);
});

test('legacy fitted FK derivatives are selectable but only reviewed standing rigs gain preliminary walking',()=>{
  const legacy=roster.filter(entry=>entry.asset.quality==='prototype');assert.equal(legacy.length,16);
  assert.ok(legacy.every(entry=>entry.controllable&&!entry.locomotionValidated));
  assert.equal(legacy.filter(entry=>entry.controlMode==='prototype-motion').length,11);
  assert.equal(legacy.filter(entry=>entry.controlMode==='static-pose').length,5);
  const seated=roster.find(entry=>entry.id==='SUP_woman_seated_v15');
  assert.equal(seated.pose,'seated');assert.equal(seated.height,1.7);assert.match(seated.context,/Leitura/);
  assert.ok(roster.every(entry=>entry.height===1.7),'every character wrapper must match Remy height');
  for(const entry of legacy.filter(entry=>entry.asset.needsRepose)){
    assert.equal(entry.displayUrl,originals.find(original=>original.id===entry.id).url);
    assert.equal(entry.standingPose,null);
    assert.equal(entry.playerAsset.characterStandingPose.clip,'Idle');
  }
});

test('hash changes and incomplete clips disable native walking while keeping available characters selectable',()=>{
  const remy=assets.find(asset=>asset.id==='CHR_Remy_Mixamo_20261005');
  for(const altered of [{...remy,sha256:'new-file'}, {...remy,animations:['Idle']}, {...remy,needsRepose:true}]){
    const entry=buildCharacterRoster([altered],[],reviews)[0];
    assert.equal(entry.controllable,true);assert.equal(entry.locomotionValidated,false);
    assert.equal(entry.playerAsset.characterCapabilities.animatedLocomotion,false);
  }
  const missing=buildCharacterRoster([{...remy,url:null}],[],reviews)[0];
  assert.equal(missing.controllable,false);assert.equal(missing.playerAsset,null);
  assert.equal(resolveRosterCharacter(roster,'SUP_woman_seated_v15').id,'SUP_woman_seated_v15');
  assert.equal(resolveRosterCharacter(roster,'missing'),null);
  const source=JSON.stringify(assets);buildCharacterRoster(assets,originals,reviews);assert.equal(JSON.stringify(assets),source);
});

test('only characters with native validated walking enter the autonomous hospital patient flow',()=>{
  const patients=hospitalPatientCharacters(roster,8);
  assert.deepEqual(patients.map(entry=>entry.id).sort(),['CHR_Remy_Mixamo_20261005','SUP_lowpoly_anime_character_cyberstyle'].sort());
  assert.ok(patients.every(entry=>entry.patientEligible&&entry.locomotionValidated&&entry.playerAsset.walkClip&&entry.playerAsset.idleClip));
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
