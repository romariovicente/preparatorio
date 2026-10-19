// Only call this for scenes loaded privately by the catalog preview. Gameplay's
// shared useGLTF cache may still own its geometries, materials and textures.
export function disposeAssetPreview(scenes){
  const geometries=new Set(),materials=new Set(),textures=new Set(),images=new Set();
  for(const scene of Array.isArray(scenes)?scenes:[scenes])scene?.traverse(object=>{
    if(object.geometry)geometries.add(object.geometry);
    for(const material of (Array.isArray(object.material)?object.material:[object.material]).filter(Boolean)){
      materials.add(material);
      for(const value of Object.values(material))if(value?.isTexture)textures.add(value);
    }
    if(object.skeleton?.boneTexture)textures.add(object.skeleton.boneTexture);
  });
  for(const texture of textures){
    const image=texture.source?.data??texture.image;
    if(image)images.add(image);
    texture.dispose();
  }
  geometries.forEach(geometry=>geometry.dispose());materials.forEach(material=>material.dispose());
  images.forEach(image=>image.close?.());
}
