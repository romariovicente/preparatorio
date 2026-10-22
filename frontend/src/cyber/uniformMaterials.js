import {ClampToEdgeWrapping} from 'three';
import {HOSPITAL_SCRUB_COLOR} from '../network/playerIdentity.js';

const clothing = object => /^(COAT_|SCRUB_)/.test(object.name);
export const isUniformNameMesh = object => object.isMesh && /^(COAT|SCRUB)_NAME_/.test(object.name);
export const isUniformSurfaceAttachment = object => object.isMesh && object.userData?.uniformSurfaceAttachment === true;

const uniformSurfaceProgramKey='prep-uniform-surface-uv-clip-v1';
const uniformSurfaceShaderMarker='// PREP_UNIFORM_SURFACE_UV_CLIP_V1';
const preparedUniformSurfaceMaterials=new WeakSet();

function prepareUniformSurfaceMaterial(material) {
  if(!material || preparedUniformSurfaceMaterials.has(material))return;
  const inheritedCompile=material.onBeforeCompile;
  const inheritedKey=material.customProgramCacheKey();
  material.polygonOffset=true;
  material.polygonOffsetFactor=-1;
  material.polygonOffsetUnits=-1;
  material.onBeforeCompile=function(shader,renderer){
    inheritedCompile.call(this,shader,renderer);
    if(shader.fragmentShader.includes(uniformSurfaceShaderMarker))return;
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`${uniformSurfaceShaderMarker}
#ifdef USE_MAP
  if ( any( lessThan( vMapUv, vec2( 0.0 ) ) ) || any( greaterThan( vMapUv, vec2( 1.0 ) ) ) ) discard;
#endif
#include <map_fragment>`);
  };
  material.customProgramCacheKey=()=>`${inheritedKey}:${uniformSurfaceProgramKey}`;
  material.needsUpdate=true;
  preparedUniformSurfaceMaterials.add(material);
}

// New Blender exports mark only the coplanar logo/name triangle subsets. The
// legacy block costumes keep their previous materials and shadow behavior.
export function prepareUniformSurfaceAttachment(object) {
  if(!isUniformSurfaceAttachment(object))return false;
  object.castShadow=false;
  for(const material of Array.isArray(object.material)?object.material:[object.material])prepareUniformSurfaceMaterial(material);
  return true;
}

// GLTFLoader caches source materials. Every player owns the materials that can
// be tinted or carry a personal name; the supplied logo pixels stay untouched.
export function cloneUniformMaterials(group) {
  const materials=[];
  group.traverse(object=>{
    if(!object.isMesh || !clothing(object))return;
    const array=Array.isArray(object.material);
    const owned=(array?object.material:[object.material]).map(material=>{
      const copy=material.clone();materials.push(copy);return copy;
    });
    object.material=array?owned:owned[0];
    prepareUniformSurfaceAttachment(object);
  });
  return materials;
}

export function applyUniformOutfit(group, outfit, replacedMeshes=[]) {
  const coat=Boolean(outfit?.coat),scrubs=outfit?.scrubs!==false;
  group.traverse(object=>{
    if(replacedMeshes.includes(object.name))object.visible=!scrubs;
    if(object.name.startsWith('COAT_'))object.visible=coat;
    if(!object.name.startsWith('SCRUB_'))return;
    // The coat covers the shirt; trousers remain present in both looks.
    object.visible=scrubs && (!coat || /Trouser|Legs/.test(object.name));
    if(!object.isMesh)return;
    for(const material of Array.isArray(object.material)?object.material:[object.material]) {
      if(!/^SCRUB_(BRAND|NAME)_/.test(object.name))material.color?.set(HOSPITAL_SCRUB_COLOR);
    }
  });
}

export function applyUniformName(group, texture) {
  let labels=0;
  group.traverse(object=>{
    if(!isUniformNameMesh(object))return;
    labels++;
    if(isUniformSurfaceAttachment(object)){
      texture.wrapS=ClampToEdgeWrapping;texture.wrapT=ClampToEdgeWrapping;
      texture.needsUpdate=true;
    }
    for(const material of Array.isArray(object.material)?object.material:[object.material]){
      material.map=texture;material.color?.set('#ffffff');material.opacity=1;
      material.transparent=true;material.alphaTest=.02;material.depthWrite=false;
      material.needsUpdate=true;
    }
  });
  return labels;
}
