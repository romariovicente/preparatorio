const categoryAliases = {
  animal:'Animais', animals:'Animais', animais:'Animais', fauna:'Animais',
  train:'Trens', trains:'Trens', trem:'Trens', trens:'Trens', rail:'Trens', railway:'Trens', ferrovia:'Trens',
  anatomy:'Anatomia', anatomia:'Anatomia',
  vehicle:'Veículos', vehicles:'Veículos', veiculos:'Veículos', car:'Veículos', carro:'Veículos', bus:'Veículos', onibus:'Veículos',
  character:'Personagens', characters:'Personagens', personagem:'Personagens', personagens:'Personagens',
};
const fold = value => String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
const categorySearchTerms={Animais:'animal animais fauna',Trens:'trem trens train rail trilho trilhos ferrovia',Anatomia:'anatomia anatomy',Veículos:'veiculo veiculos carro carros onibus bus',Personagens:'personagem personagens humano humanos character'};
const clipsOf = asset => {
  const clips=asset.animations??asset.clips;
  return Array.isArray(clips)?clips.filter(clip=>typeof clip==='string'):[];
};

export function assetCatalogCategory(asset){
  if(asset.id==='SUP_african_wild_dog')return 'Animais';
  if(asset.id==='SUP_modular_futuristic_train')return 'Trens';
  return categoryAliases[fold(asset.category)]??categoryAliases[fold(asset.sourceCategory)]??asset.category??'Cenários';
}

export function normalizeCatalogAddition(asset){
  const animations=clipsOf(asset),category=assetCatalogCategory(asset);
  return {...asset,name:asset.name??asset.label??asset.id,category,catalogAdded:asset.catalogAdded??'2026-10-16',credits:asset.credits??asset.sourceCredits??{},
    animations,animated:animations.length>0&&asset.animated!==false,rigged:asset.rigged===true,
    playable:category==='Personagens'&&asset.playable===true&&asset.rigged===true&&asset.reimportValidated===true&&
      asset.quality!=='prototype'&&animations.some(name=>/walk/i.test(name))&&animations.some(name=>/idle/i.test(name)),
  };
}

// Historical records win. A source and its prepared derivative remain one entry.
export function mergeAssetCatalog(historical,additions=[]){
  const ids=new Set(),hashes=new Set(),merged=[];
  for(const asset of [...historical,...additions]){
    if(!asset?.id||!asset.url)continue;
    const keys=[asset.sha256,asset.sourceSha256].filter(Boolean).map(value=>String(value).toLowerCase());
    if(ids.has(asset.id)||keys.some(key=>hashes.has(key)))continue;
    ids.add(asset.id);keys.forEach(key=>hashes.add(key));merged.push(asset);
  }
  return merged;
}

export function assetCatalogCategories(assets){
  const available=new Set(assets.map(assetCatalogCategory));
  const preferred=['Personagens','Veículos','Motocicletas','Trens','Animais','Anatomia'];
  return ['Todos',...preferred.filter(category=>available.delete(category)),...available];
}

export function filterAssetCatalog(assets,category='Todos',query=''){
  const words=fold(query).trim().split(/\s+/).filter(Boolean);
  return assets.filter(asset=>{
    const displayCategory=assetCatalogCategory(asset);
    const tags=Array.isArray(asset.tags)?asset.tags:[];
    const text=fold([asset.name,asset.label,asset.id,asset.category,displayCategory,categorySearchTerms[displayCategory],asset.description,...tags].join(' '));
    return (category==='Todos'||displayCategory===category)&&words.every(word=>text.includes(word));
  });
}

export function isValidatedCatalogPlayer(asset){
  const clips=clipsOf(asset);
  return assetCatalogCategory(asset)==='Personagens'&&asset.rigged===true&&asset.playable===true&&
    asset.reimportValidated===true&&asset.visualStyle==='realistic'&&asset.quality!=='prototype'&&
    clips.some(name=>/walk/i.test(name))&&clips.some(name=>/idle/i.test(name));
}

export function assetMotionDescription(asset){
  if(asset.quality==='prototype')return 'Rig de protótipo com movimentos procedurais. A locomoção realista ainda precisa de revisão.';
  if(isValidatedCatalogPlayer(asset))return 'Personagem com esqueleto e animações validadas para uso no jogo.';
  if(clipsOf(asset).length)return asset.rigged
    ?'Esqueleto e animações presentes no modelo. Explore os clipes disponíveis; o uso como jogador depende de validação.'
    :'Animações presentes no arquivo de origem. Os clipes disponíveis podem ser inspecionados nesta prévia.';
  return 'Modelo estático para exposição e inspeção. A pose e as peças recebidas foram preservadas.';
}

export function assetClipLabel(clip){
  const name=String(clip??''),parts=name.split('|'),namespace=parts.at(-2);
  let plain=parts.at(-1).split('::').at(-1);
  if(namespace&&plain.toLowerCase().startsWith(namespace.toLowerCase()+'_'))plain=plain.slice(namespace.length+1);
  const key=plain.toLowerCase().replace(/[\s_-]/g,'');
  const labels={idle:'Parado',stand:'Em pé',walk:'Caminhar',run:'Correr',breathing:'Respirar',howl:'Uivar',
    animation:'Animação original',dance:'Dançar',interact:'Interagir',gesture:'Gesto',motion:'Movimento original',
    dooropen:'Abrir porta',opendoor:'Abrir porta',doorclose:'Fechar porta',closedoor:'Fechar porta',
    openalldoors:'Abrir todas as portas',frontleftdoor:'Porta dianteira esquerda',frontrightdoor:'Porta dianteira direita',
    rearleftdoor:'Porta traseira esquerda',rearrightdoor:'Porta traseira direita',slidingsidedoor:'Porta lateral deslizante',
    tailgateandshelf:'Porta-malas e prateleira',sunroof:'Teto solar',airbags:'Airbags',cupholder:'Porta-copos'};
  if(labels[key])return labels[key];
  const walk=key.match(/^walk(fast|slow)?([fbrl])?$/);
  if(walk){
    const pace={fast:' rápido',slow:' devagar'},direction={f:'à frente',b:'para trás',r:'à direita',l:'à esquerda'};
    return 'Caminhar'+(pace[walk[1]]??'')+(walk[2]?' · '+direction[walk[2]]:'');
  }
  return name;
}

export function assetLibraryLocation(search){
  if(typeof search!=='string'||search.length>4096)return null;
  const params=new URLSearchParams(search);
  if(params.getAll('view').length!==1||params.get('view')!=='assets')return null;
  const knownCategories=new Set(['Todos','Personagens','Veículos','Motocicletas','Trens','Animais','Anatomia','Naves','Equipamentos','Cenários','Edifícios','Monumentos']);
  const requestedCategory=params.getAll('category').length===1?assetCatalogCategory({category:params.get('category')}):'Todos';
  const requestedAsset=params.getAll('asset').length===1?params.get('asset'):null;
  return {category:knownCategories.has(requestedCategory)?requestedCategory:'Todos',
    assetId:requestedAsset&&/^[\p{L}\p{N}_().“”‘’'-]{1,160}$/u.test(requestedAsset)?requestedAsset:null};
}
