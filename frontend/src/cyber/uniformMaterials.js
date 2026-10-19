const clothing = object => /^(COAT_|SCRUB_)/.test(object.name);
export const isUniformNameMesh = object => object.isMesh && /^(COAT|SCRUB)_NAME_/.test(object.name);

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
  });
  return materials;
}

export function applyUniformOutfit(group, outfit, replacedMeshes=[]) {
  const coat=Boolean(outfit?.coat),scrubs=outfit?.scrubs!==false;
  const color=/^#[\da-f]{6}$/i.test(outfit?.color??'')?outfit.color:null;
  group.traverse(object=>{
    if(replacedMeshes.includes(object.name))object.visible=!scrubs;
    if(object.name.startsWith('COAT_'))object.visible=coat;
    if(!object.name.startsWith('SCRUB_'))return;
    // The coat covers the shirt; trousers remain present in both looks.
    object.visible=scrubs && (!coat || /Trouser|Legs/.test(object.name));
    if(!object.isMesh || !color)return;
    for(const material of Array.isArray(object.material)?object.material:[object.material]) {
      if(!/^SCRUB_(BRAND|NAME)_/.test(object.name))material.color?.set(color);
    }
  });
}

export function applyUniformName(group, texture) {
  let labels=0;
  group.traverse(object=>{
    if(!isUniformNameMesh(object))return;
    labels++;
    for(const material of Array.isArray(object.material)?object.material:[object.material]){
      material.map=texture;material.color?.set('#ffffff');material.opacity=1;
      material.transparent=true;material.alphaTest=.02;material.depthWrite=false;
      material.needsUpdate=true;
    }
  });
  return labels;
}
