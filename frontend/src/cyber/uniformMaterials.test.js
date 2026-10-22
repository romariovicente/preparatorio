import test from 'node:test';
import assert from 'node:assert/strict';
import {ClampToEdgeWrapping,Group,Mesh,MeshStandardMaterial,PlaneGeometry,RepeatWrapping,Texture} from 'three';
import {applyUniformName,applyUniformOutfit,cloneUniformMaterials,prepareUniformSurfaceAttachment} from './uniformMaterials.js';
import {uniformDisplayName,createUniformNameTexture} from './uniformName.js';

function fixture(){
  const group=new Group();
  for(const name of ['Tops001','Bottoms001','SCRUB_Remy_Shirt','SCRUB_Remy_Trousers',
    'SCRUB_Remy_TrouserLegs','COAT_Remy_FittedShell','COAT_NAME_Remy_Player',
    'SCRUB_NAME_Remy_Player','SCRUB_BRAND_Remy_Crest']){
    const mesh=new Mesh(new PlaneGeometry(),new MeshStandardMaterial({color:'#ffffff',opacity:name.includes('NAME')?0:1}));
    mesh.name=name;group.add(mesh);
  }
  return group;
}

test('coat and scrubs use the same Portuguese player identity as the network',()=>{
  assert.equal(uniformDisplayName('  Ana\u0000  Maria <Silva>  '),'Ana Maria Silva');
  assert.equal(uniformDisplayName(null),'Jogador');
  assert.equal(Array.from(uniformDisplayName('Á'.repeat(60))).length,48);
});

test('independent users own name materials and cannot tint the supplied crest',()=>{
  const source=fixture(),alice=source.clone(),bruno=source.clone();
  const originalMaterial=source.getObjectByName('COAT_NAME_Remy_Player').material;
  const ownedA=cloneUniformMaterials(alice),ownedB=cloneUniformMaterials(bruno);
  const textureA=new Texture(),textureB=new Texture();
  assert.equal(applyUniformName(alice,textureA),2);assert.equal(applyUniformName(bruno,textureB),2);
  for(const name of ['COAT_NAME_Remy_Player','SCRUB_NAME_Remy_Player']){
    assert.equal(alice.getObjectByName(name).material.map,textureA);
    assert.equal(bruno.getObjectByName(name).material.map,textureB);
    assert.equal(alice.getObjectByName(name).material.opacity,1);
  }
  assert.equal(originalMaterial.opacity,0);assert.equal(originalMaterial.map,null);
  applyUniformOutfit(alice,{scrubs:true,coat:false,color:'#37664b'},['Tops001','Bottoms001']);
  assert.equal(alice.getObjectByName('SCRUB_Remy_Shirt').material.color.getHexString(),'ffffff');
  assert.equal(alice.getObjectByName('SCRUB_BRAND_Remy_Crest').material.color.getHexString(),'ffffff');
  ownedA.concat(ownedB).forEach(material=>material.dispose());
});

test('each outfit retains clothing while the coat hides the inner shirt and its labels',()=>{
  const group=fixture(),replaced=['Tops001','Bottoms001'];
  applyUniformOutfit(group,{scrubs:true,coat:true},replaced);
  for(const name of ['SCRUB_Remy_Trousers','SCRUB_Remy_TrouserLegs','COAT_Remy_FittedShell','COAT_NAME_Remy_Player'])assert.equal(group.getObjectByName(name).visible,true,name);
  for(const name of ['Tops001','Bottoms001','SCRUB_Remy_Shirt','SCRUB_NAME_Remy_Player','SCRUB_BRAND_Remy_Crest'])assert.equal(group.getObjectByName(name).visible,false,name);
  applyUniformOutfit(group,{scrubs:true,coat:false},replaced);
  assert.equal(group.getObjectByName('SCRUB_NAME_Remy_Player').visible,true);
  assert.equal(group.getObjectByName('COAT_Remy_FittedShell').visible,false);
  applyUniformOutfit(group,{scrubs:false,coat:true},replaced);
  assert.equal(group.getObjectByName('Tops001').visible,true);assert.equal(group.getObjectByName('Bottoms001').visible,true);
  assert.equal(group.getObjectByName('COAT_Remy_FittedShell').visible,true);
});

test('runtime lettering draws only the current user name, without a reference name',()=>{
  const labels=[];
  const context={clearRect(){},measureText(text){return {width:text.length*20};},fillText(text){labels.push(text);}};
  const originalDocument=globalThis.document;
  globalThis.document={createElement(){return {getContext(){return context;}};}};
  try{
    const texture=createUniformNameTexture('Beatriz Ação');
    assert.deepEqual(labels,['Técnico de Enfermagem','Beatriz Ação']);
    assert.equal(texture.flipY,false);texture.dispose();
  }finally{globalThis.document=originalDocument;}
});

test('new surface-attached embroidery clips outside UV bounds and keeps each player material private',()=>{
  const source=fixture();
  for(const name of ['COAT_NAME_Remy_Player','SCRUB_NAME_Remy_Player','SCRUB_BRAND_Remy_Crest']){
    const mesh=source.getObjectByName(name);
    mesh.userData={uniformSurfaceAttachment:true,uniformSurfaceMesh:name.startsWith('COAT_')?'COAT_Remy_FittedShell':'SCRUB_Remy_Shirt',uniformSurfaceVertexMap:[0,1,2,3]};
    mesh.castShadow=true;
  }
  const legacy=new Mesh(new PlaneGeometry(),new MeshStandardMaterial());legacy.name='COAT_Legacy_NameBadge';source.add(legacy);
  const originalNameMaterial=source.getObjectByName('COAT_NAME_Remy_Player').material;
  const alice=source.clone(),bruno=source.clone();
  cloneUniformMaterials(alice);cloneUniformMaterials(bruno);
  const aliceName=alice.getObjectByName('COAT_NAME_Remy_Player'),brunoName=bruno.getObjectByName('COAT_NAME_Remy_Player');
  assert.notEqual(aliceName.material,originalNameMaterial);assert.notEqual(aliceName.material,brunoName.material);
  assert.equal(originalNameMaterial.polygonOffset,false);assert.equal(source.getObjectByName('COAT_NAME_Remy_Player').castShadow,true);
  for(const mesh of [aliceName,alice.getObjectByName('SCRUB_NAME_Remy_Player'),alice.getObjectByName('SCRUB_BRAND_Remy_Crest')]){
    assert.equal(mesh.castShadow,false);assert.equal(mesh.material.polygonOffset,true);
    assert.equal(mesh.material.polygonOffsetFactor,-1);assert.equal(mesh.material.polygonOffsetUnits,-1);
    assert.equal(mesh.material.customProgramCacheKey(),aliceName.material.customProgramCacheKey());
  }
  assert.equal(prepareUniformSurfaceAttachment(alice.getObjectByName('COAT_Legacy_NameBadge')),false);
  assert.equal(alice.getObjectByName('COAT_Legacy_NameBadge').material.polygonOffset,false);
  const shader={fragmentShader:'void main() {\n#include <map_fragment>\n}'};
  aliceName.material.onBeforeCompile(shader,{});
  assert.match(shader.fragmentShader,/PREP_UNIFORM_SURFACE_UV_CLIP_V1/);
  assert.match(shader.fragmentShader,/USE_MAP[\s\S]*vMapUv[\s\S]*discard/);
  const textureA=new Texture(),textureB=new Texture();
  textureA.wrapS=RepeatWrapping;textureA.wrapT=RepeatWrapping;
  applyUniformName(alice,textureA);applyUniformName(bruno,textureB);
  assert.equal(textureA.wrapS,ClampToEdgeWrapping);assert.equal(textureA.wrapT,ClampToEdgeWrapping);
  assert.equal(aliceName.material.map,textureA);assert.equal(brunoName.material.map,textureB);
  assert.equal(originalNameMaterial.map,null);
});
