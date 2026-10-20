import policyRaw from '../config/livingWorldDecorations.json' with {type:'json'};
import {resolveAssetReferences} from '../config/deploymentConfig.js';
const policy=resolveAssetReferences(policyRaw);

const exactHiddenNames=new Set(policy.hideNames);
const vegetation=/^(?:TREE_(?:Crown|Trunk)(?:\.\d+)?|(?:SHRUB|BUSH|ARBUST|HEDGE)_[\w.]+)$/;

export const livingWorldDecorationPolicy=policy;

// Exact, audited source names only. A renamed road, rail, sign or building can
// never become eligible merely because its box overlaps a new habitat.
export function shouldHideLivingWorldDecoration(object,sourceSceneUrl=policy.sourceSceneUrl){
  if(sourceSceneUrl!==policy.sourceSceneUrl)return false;
  const name=object?.userData?.name??object?.userData?.asset_node_name??object?.name??'';
  return vegetation.test(name)&&exactHiddenNames.has(name);
}

// Call on the private Environment clone before createSolidIndex. Its visibility
// check excludes both hidden meshes and descendants, preventing ghost trunks.
export function prepareLivingWorldDecorations(scene,sourceSceneUrl=policy.sourceSceneUrl){
  scene.traverse(object=>{
    if(shouldHideLivingWorldDecoration(object,sourceSceneUrl)){
      object.visible=false;
      object.userData.livingWorldDecorationHidden=true;
    }
  });
  return scene;
}
