import test from 'node:test';
import assert from 'node:assert/strict';
import {assetCatalogCategory,assetCatalogCategories,assetClipLabel,assetLibraryLocation,filterAssetCatalog,isValidatedCatalogPlayer,mergeAssetCatalog,normalizeCatalogAddition} from './assetCatalog.js';

test('additive catalog preserves history and rejects duplicate ids, exports and sources',()=>{
  const historical=[{id:'original',url:'/original.glb',sha256:'EXPORT',sourceSha256:'SOURCE'}];
  const additions=[{id:'original',url:'/replacement.glb'},{id:'same-export',url:'/copy.glb',sha256:'export'},
    {id:'same-source',url:'/derivative.glb',sourceSha256:'source'},{id:'new',url:'/new.glb',sha256:'NEW'}];
  assert.deepEqual(mergeAssetCatalog(historical,additions).map(asset=>asset.id),['original','new']);
});

test('category and accent-insensitive search reveal animal, rail and anatomy sources',()=>{
  const assets=[{id:'SUP_african_wild_dog',category:'Equipamentos',name:'African Wild Dog'},
    {id:'rail',category:'rail',name:'Trilho de estação'},{id:'body',category:'anatomy',name:'Órgãos humanos'},
    {id:'student',category:'Personagens',name:'Estudante'}];
  assert.equal(assetCatalogCategory(assets[0]),'Animais');
  assert.equal(assetCatalogCategory({id:'SUP_modular_futuristic_train',category:'Cenários'}),'Trens');
  assert.deepEqual(filterAssetCatalog(assets,'Trens','estacao').map(asset=>asset.id),['rail']);
  assert.deepEqual(filterAssetCatalog(assets,'Todos','trem').map(asset=>asset.id),['rail']);
  assert.deepEqual(filterAssetCatalog(assets,'Todos','animal').map(asset=>asset.id),['SUP_african_wild_dog']);
  assert.deepEqual(filterAssetCatalog(assets,'Todos','anatomia orgaos').map(asset=>asset.id),['body']);
  assert.deepEqual(assetCatalogCategories(assets),['Todos','Personagens','Trens','Animais','Anatomia']);
});

test('new static or incomplete characters cannot become playable through catalog normalization',()=>{
  const base={id:'human',url:'/human.glb',category:'Personagens',playable:true,visualStyle:'realistic',reimportValidated:true,animations:['Idle','Walk']};
  assert.equal(normalizeCatalogAddition(base).playable,false);
  assert.equal(isValidatedCatalogPlayer(normalizeCatalogAddition(base)),false);
  assert.equal(isValidatedCatalogPlayer(normalizeCatalogAddition({...base,rigged:true})),true);
  assert.equal(isValidatedCatalogPlayer({...base,rigged:true,quality:'prototype'}),false);
  assert.equal(isValidatedCatalogPlayer({...base,rigged:true,animations:['motion']}),false);
});

test('clip labels translate familiar actions without changing their source identifiers',()=>{
  assert.equal(assetClipLabel('Idle'),'Parado');
  assert.equal(assetClipLabel('Stand'),'Em pé');
  assert.equal(assetClipLabel('WalkFast_F'),'Caminhar rápido · à frente');
  assert.equal(assetClipLabel('WalkSlow_F'),'Caminhar devagar · à frente');
  assert.equal(assetClipLabel('Armature|Walk'),'Caminhar');
  assert.equal(assetClipLabel('Breathing'),'Respirar');
  assert.equal(assetClipLabel('Howl'),'Uivar');
  assert.equal(assetClipLabel('Animation'),'Animação original');
  assert.equal(assetClipLabel('DoorOpen'),'Abrir porta');
  assert.equal(assetClipLabel('custom-source-action'),'custom-source-action');
});

test('actual supplied animal clip namespaces retain their exact ids and receive Portuguese labels',()=>{
  const labels={
    'Fox|Fox_Howl':'Uivar',
    'Fox|Fox_Stand':'Em pé',
    'Fox|Fox_WalkFast_F':'Caminhar rápido · à frente',
    'Lioness|Lioness_Breathing':'Respirar',
    'Lioness|Lioness_Idle':'Parado',
    'Lioness|Lioness_WalkFast_F':'Caminhar rápido · à frente',
    'Rabbit|Rabbit_Idle':'Parado',
    'Rabbit|Rabbit_WalkSlow_F':'Caminhar devagar · à frente',
    'Wolf|Wolf_Howl':'Uivar',
    'Wolf|Wolf_WalkFast_F':'Caminhar rápido · à frente',
    'Horse|Horse_Idle':'Parado',
    'Horse|Horse_Walk':'Caminhar',
  };
  for(const [id,label] of Object.entries(labels))assert.equal(assetClipLabel(id),label,id);
  assert.equal(assetClipLabel('Fox|Wolf_Stand'),'Fox|Wolf_Stand','A mismatched namespace must remain identifiable');
});

test('asset deep links accept known categories and safe ids while ignoring invalid parameters',()=>{
  assert.equal(assetLibraryLocation(''),null);
  assert.equal(assetLibraryLocation('?view=unknown'),null);
  assert.equal(assetLibraryLocation('?view=assets&view=cyber'),null);
  assert.deepEqual(assetLibraryLocation('?view=assets'),{category:'Todos',assetId:null});
  assert.deepEqual(assetLibraryLocation('?view=assets&category=animals&asset=FAUNA_Wolf_20261016'),{category:'Animais',assetId:'FAUNA_Wolf_20261016'});
  assert.deepEqual(assetLibraryLocation('?view=assets&category=unknown&asset=../escape.glb'),{category:'Todos',assetId:null});
});
