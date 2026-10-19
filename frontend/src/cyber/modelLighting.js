export function setWorldShadows(model) {
  model.traverse(object=>{
    if(!object.isMesh)return;
    const materials=Array.isArray(object.material)?object.material:[object.material];
    const transparent=materials.some(material=>material&&
      (material.opacity<.98||material.transmission>0||material.transparent&&!material.alphaTest||/glass|vidro/i.test(material.name)));
    object.castShadow=!transparent;
    object.receiveShadow=!transparent;
  });
  return model;
}
