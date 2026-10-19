import { Component, useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Bounds, Html, OrbitControls, useAnimations } from '@react-three/drei';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import { runtimeAssets } from '../config/runtimeAssets.js';
import {assetCatalogCategories,assetCatalogCategory,assetClipLabel,assetMotionDescription,filterAssetCatalog,isValidatedCatalogPlayer} from '../config/assetCatalog.js';
import {createCharacterClone,findCharacterAction,startCharacterAction} from './characterModel.js';
import {disposeAssetPreview} from './assetPreviewResources.js';
import './assets.css';

const assets=[...runtimeAssets].sort((a,b)=>Number(Boolean(b.catalogAdded))-Number(Boolean(a.catalogAdded)));

class AssetBoundary extends Component{
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?<Html center><span className="asset-preview-failure">Este modelo não carregou. Escolha outro item ou recarregue a página.</span></Html>:this.props.children;}
}

function PreviewModel({gltf,asset,playing,clip}){
  const model=useMemo(()=>createCharacterClone(gltf.scene,asset.height??2).group,[gltf.scene,asset.height]);
  const {actions,mixer}=useAnimations(gltf.animations,model);
  useEffect(()=>{
    const action=findCharacterAction(actions,clip);
    startCharacterAction(action,mixer,playing);
    return ()=>action?.stop();
  },[actions,mixer,playing,clip]);
  useEffect(()=>()=>{
    mixer.stopAllAction();mixer.uncacheRoot(model);
    model.traverse(object=>object.skeleton?.dispose());
  },[mixer,model]);
  return <primitive object={model} dispose={null}/>;
}

function OwnedAssetPreview({asset,playing,clip}){
  const [result,setResult]=useState(null);
  useEffect(()=>{
    let active=true,owned=null;
    // The private loader owns its GPU resources independently of gameplay's cache.
    new GLTFLoader().load(asset.url,gltf=>{
      owned=gltf;
      if(active)setResult({gltf});else disposeAssetPreview(gltf.scenes??gltf.scene);
    },undefined,()=>{if(active)setResult({failed:true});});
    return ()=>{active=false;if(owned)disposeAssetPreview(owned.scenes??owned.scene);};
  },[asset.url]);
  if(!result)return <Html center><span className="map-loading">Carregando modelo…</span></Html>;
  if(result.failed)return <Html center><span className="asset-preview-failure" role="status">Este modelo não carregou. Escolha outro item.</span></Html>;
  return <Bounds fit clip observe margin={1.3}><PreviewModel gltf={result.gltf} asset={asset} playing={playing} clip={clip}/></Bounds>;
}

export default function AssetLibrary({initialCategory='Todos',initialAssetId=null}){
  const categories=assetCatalogCategories(assets);
  const [category,setCategory]=useState(()=>{
    const requested=assets.find(asset=>asset.id===initialAssetId);
    return requested?assetCatalogCategory(requested):categories.includes(initialCategory)?initialCategory:'Todos';
  });
  const [selectedId,setSelectedId]=useState(()=>assets.find(asset=>asset.id===initialAssetId)?.id??filterAssetCatalog(assets,initialCategory)[0]?.id??assets[0]?.id);
  const [query,setQuery]=useState(''),[newOnly,setNewOnly]=useState(false);
  const [clip,setClip]=useState(null),[playing,setPlaying]=useState(false),[notice,setNotice]=useState('');
  const selected=assets.find(asset=>asset.id===selectedId)??assets[0];
  const additionsCount=assets.filter(asset=>asset.catalogAdded).length;
  const filtered=filterAssetCatalog(assets,category,query).filter(asset=>!newOnly||asset.catalogAdded);
  function selectAsset(asset){setSelectedId(asset.id);setClip(null);setPlaying(false);setNotice('');}
  function chooseCategory(next){
    setCategory(next);
    const first=filterAssetCatalog(assets,next,query).find(asset=>!newOnly||asset.catalogAdded);
    if(first&&assetCatalogCategory(selected)!==next)selectAsset(first);
  }
  function selectCharacter(){
    if(!isValidatedCatalogPlayer(selected))return;
    try{localStorage.setItem('prep.character.v1',selected.id);}catch{/* current session still works */}
    window.dispatchEvent(new CustomEvent('prep:character',{detail:selected.id}));
    setNotice('Personagem validado selecionado.');
  }
  if(!selected)return <p>Nenhum modelo validado disponível.</p>;
  const clips=selected.animations??[],selectedClip=clips.includes(clip)?clip:clips[0]??'Idle',credits=selected.credits??{};
  return <section className="asset-library" aria-label="Acervo de modelos 3D">
    <div className="asset-heading"><span className="eyebrow">CONSTRUINDO NOSSO MUNDO</span><h2>Acervo 3D</h2><p>{assets.length} modelos preparados a partir dos seus arquivos.{additionsCount>0&&` ${additionsCount} novos modelos disponíveis.`} Escolha um para inspecionar.</p></div>
    <div className="asset-search"><label>Buscar no acervo<input type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Nome, personagem, animal, trem ou anatomia"/></label>{additionsCount>0&&<label className="asset-new-filter"><input type="checkbox" checked={newOnly} onChange={event=>setNewOnly(event.target.checked)}/>Somente novos</label>}</div>
    <div className="asset-categories" aria-label="Categorias do acervo">{categories.map(c=><button key={c} aria-pressed={c===category} onClick={()=>chooseCategory(c)}>{c}</button>)}</div>
    <p className="asset-results" role="status">{filtered.length} {filtered.length===1?'modelo encontrado':'modelos encontrados'}</p>
    <div className="asset-workspace">
      <div className="asset-list" aria-label="Modelos do acervo">{filtered.length===0&&<p className="asset-empty">Nenhum modelo corresponde à busca. Experimente outra categoria ou nome.</p>}{filtered.map(asset=><button key={asset.id} aria-pressed={asset.id===selected.id} onClick={()=>selectAsset(asset)}>{asset.preview?<img loading="lazy" src={asset.preview} alt=""/>:<span className="asset-thumbnail-placeholder" aria-hidden="true">3D</span>}<span><strong>{asset.name}{asset.catalogAdded&&<span className="asset-new-badge">Novo</span>}</strong><small>{assetCatalogCategory(asset)}{Number.isFinite(asset.bytes)&&` · ${(asset.bytes/1048576).toFixed(1)} MB`}</small></span></button>)}</div>
      <div className="asset-detail"><div className="asset-viewport" data-asset-id={selected.id}>
        <Canvas dpr={[1,1.5]} camera={{position:[3,2,5],fov:45}}>
          <color attach="background" args={['#19323e']}/><ambientLight intensity={2}/><directionalLight position={[5,8,5]} intensity={3}/>
          <AssetBoundary key={selected.id}><OwnedAssetPreview asset={selected} playing={playing} clip={selectedClip}/></AssetBoundary><OrbitControls makeDefault/>
        </Canvas>
        <span className="asset-orbit-hint">Arraste para girar · role para aproximar</span>
      </div><div className="asset-description"><span className="eyebrow">{assetCatalogCategory(selected)}</span><h3>{selected.name}</h3><p>{assetMotionDescription(selected)}</p>{selected.description&&<p>{selected.description}</p>}
        <div className="asset-actions">{clips.length>0&&<><select aria-label="Animação do modelo" value={selectedClip} onChange={event=>setClip(event.target.value)}>{clips.map(name=><option key={name} value={name}>{assetClipLabel(name)}</option>)}</select><button onClick={()=>setPlaying(value=>!value)}>{playing?'Pausar animação':'Reproduzir animação'}</button></>}{isValidatedCatalogPlayer(selected)&&<><button onClick={()=>{selectCharacter();window.dispatchEvent(new Event('prep:play'));}}>Jogar no Campus com este personagem</button><button onClick={()=>{selectCharacter();window.dispatchEvent(new Event('prep:open-clinical'));}}>Abrir cena hospitalar</button></>}</div>
        {notice&&<p role="status">{notice}</p>}
        <details><summary>Créditos e informações do modelo</summary><p>{credits.author??'Autor não informado no arquivo.'}</p><p>{credits.license??selected.licenseStatus??'Licença não informada no arquivo original.'}</p>{credits.source&&<a href={credits.source} target="_blank" rel="noreferrer">Página original do modelo ↗</a>}{Number.isFinite(selected.triangles)&&<p>{selected.triangles.toLocaleString('pt-BR')} triângulos no modelo preparado.</p>}{selected.licenseStatus==='noncommercial'&&<p>Este modelo derivado mantém CC BY-NC-SA 4.0: uso não comercial.</p>}</details>
      </div></div>
    </div>
  </section>;
}
