import test from 'node:test';
import assert from 'node:assert/strict';
import {Group,Mesh,MeshStandardMaterial,PlaneGeometry,Texture} from 'three';
import {applyUniformName,applyUniformOutfit,cloneUniformMaterials} from './uniformMaterials.js';
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
  assert.equal(alice.getObjectByName('SCRUB_Remy_Shirt').material.color.getHexString(),'37664b');
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
