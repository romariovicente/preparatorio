import {resolveAssetReferences} from '../config/deploymentConfig.js';
import raw from '../config/warpEngine.json' with {type:'json'};
export const warpEnginePlan=resolveAssetReferences(raw);
export const warpEngineColliders=[{id:raw.id,x:raw.position[0],z:raw.position[2],w:raw.footprint[0],d:raw.footprint[1]}];
export const warpEngineZones=[{id:raw.id,label:raw.label,position:raw.approach}];
