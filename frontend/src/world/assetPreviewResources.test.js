import test from 'node:test';
import assert from 'node:assert/strict';
import {disposeAssetPreview} from './assetPreviewResources.js';

test('private preview releases shared mesh resources only once per owned scene',()=>{
  const calls={geometry:0,material:0,texture:0,image:0,bones:0};
  const geometry={dispose:()=>calls.geometry++},image={close:()=>calls.image++};
  const map={isTexture:true,source:{data:image},dispose:()=>calls.texture++};
  const material={map,normalMap:map,dispose:()=>calls.material++};
  const boneTexture={dispose:()=>calls.bones++};
  const nodes=[{geometry,material,skeleton:{boneTexture}},{geometry,material:[material]}];
  const scene={traverse:visit=>nodes.forEach(visit)};
  disposeAssetPreview([scene,scene]);
  assert.deepEqual(calls,{geometry:1,material:1,texture:1,image:1,bones:1});
});
