import {resolveAssetReferences} from './deploymentConfig.js';
import {runtimeAssets} from './runtimeAssets.js';
import originalsRaw from './suppliedAssets.json' with {type:'json'};
import manifestRaw from './cyberWorldManifest.json' with {type:'json'};
import realisticWorldRaw from './realisticWorldManifest.json' with {type:'json'};
import characterReviews from './characterMotionReviews.json' with {type:'json'};
import warpEngine from './warpEngine.json' with {type:'json'};
import {buildCharacterRoster,characterSelectionOptions,createCharacterRosterPlacements,characterRosterColliders,hospitalPatientCharacters as selectHospitalPatients} from './characterRoster.js';
import {newDeliveryColliders} from '../cyber/newDeliveryWorld.js';
import {classroomColliders,createClassroomRuntime} from '../cyber/classroomWorld.js';
import {livingWorldColliders} from '../cyber/cityLivingWorld.js';
import {footprintCollider} from '../cyber/collisions.js';

const suppliedCatalog=resolveAssetReferences(originalsRaw);
const manifest=resolveAssetReferences(manifestRaw);
const realisticWorld=resolveAssetReferences(realisticWorldRaw);

export const characterRoster=buildCharacterRoster(runtimeAssets,suppliedCatalog,characterReviews);
export const characterOptions=characterSelectionOptions(characterRoster);
export const hospitalPatientCharacters=selectHospitalPatients(characterRoster);
export const rosterPlacementExclusions=[
  ...manifest.colliders,...newDeliveryColliders,...classroomColliders(createClassroomRuntime()),
  ...livingWorldColliders,
  {id:warpEngine.id,x:warpEngine.position[0],z:warpEngine.position[2],w:warpEngine.footprint[0],d:warpEngine.footprint[1]},
  ...realisticWorld.environmentReplacements.map(record=>footprintCollider(record,suppliedCatalog)).filter(Boolean),
  {id:'roster-central-monument',x:0,z:0,w:18,d:18},
  {id:'roster-player-arrival',x:0,z:25,w:3,d:3},
  {id:'roster-east-road',x:35,z:0,w:14,d:236},
  {id:'roster-west-road',x:-35,z:0,w:14,d:236},
  {id:'roster-south-road',x:0,z:35,w:236,d:14},
  {id:'roster-north-road',x:0,z:-75,w:236,d:14},
];
export const rosterPlan=createCharacterRosterPlacements(characterRoster,{colliders:rosterPlacementExclusions});
export const rosterObstacles=characterRosterColliders(rosterPlan.placements);
export const rosterZones=rosterPlan.placements.filter(entry=>entry.position).map(entry=>({
  id:entry.actorId,label:entry.name,position:[entry.position[0]+1.5,entry.position[1],entry.position[2]+2],
}));
