import {assetUrl} from '../config/deploymentConfig.js';
import { Component, lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUpRight, BookOpen, Check, ChevronRight, Compass, GraduationCap, Layers3, Map, Maximize2, Moon, Search, Sun, X } from 'lucide-react';
import { categories, locationIds, locations } from './locations.js';
import { discover, INTRO_LOCATIONS, readProgress, rewardBalance, writeProgress } from './progress.js';
import {assetLibraryLocation} from '../config/assetCatalog.js';
import './world.css';

const WorldCanvas=lazy(() => import('./WorldCanvas.jsx'));
const KitCanvas=lazy(() => import('./KitCanvas.jsx'));
const KnowledgeLibrary=lazy(() => import('./KnowledgeLibrary.jsx'));
const PlayCampus=lazy(() => import('./PlayCampus.jsx'));
const AssetLibrary=lazy(() => import('./AssetLibrary.jsx'));
const CyberCity=lazy(() => import('../cyber/CyberCity.jsx'));

class ViewBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed ? <div className="map-fallback"><p>Não foi possível abrir a visualização 3D neste dispositivo.</p><button onClick={this.props.onReference}>Ver mapa de referência</button></div> : this.props.children;}
}

export default function WorldShell(){
  const [initialAssetView]=useState(()=>assetLibraryLocation(window.location.search));
  const [mode,setMode]=useState(initialAssetView?'assets':'cyber'); const [quality,setQuality]=useState(() => window.innerWidth<700?'mobile':'web');
  const [selected,setSelected]=useState(null); const [category,setCategory]=useState('all'); const [search,setSearch]=useState('');
  const [night,setNight]=useState(false); const [revision,setRevision]=useState(0); const [ready,setReady]=useState(null);
  const [failed,setFailed]=useState(false); const [library,setLibrary]=useState(false); const [notice,setNotice]=useState('');
  const [assetRequest,setAssetRequest]=useState({...initialAssetView,category:initialAssetView?.category??'Todos',assetId:initialAssetView?.assetId??null,revision:0});
  const [progress,setProgress]=useState(() => {try{return readProgress(window.localStorage,locationIds);}catch{return {version:1,visited:[]};}});
  const stage=useRef(null); const libraryDialog=useRef(null); const libraryTrigger=useRef(null);
  const onReady=useCallback(info => {setReady(info);setFailed(false);},[]);
  const onError=useCallback(() => setFailed(true),[]);
  const filtered=locations.filter(p => (category==='all'||p.category===category) && `${p.name} ${p.subtitle}`.toLocaleLowerCase('pt-BR').includes(search.toLocaleLowerCase('pt-BR')));
  const missionCount=INTRO_LOCATIONS.filter(id => progress.visited.includes(id)).length;
  useEffect(() => {
    const d=libraryDialog.current;
    if(library&&!d.open)d.showModal();
    if(!library&&d.open){d.close();libraryTrigger.current?.focus();}
  },[library]);
  useEffect(()=>{const play=()=>setMode('play'),learn=()=>setLibrary(true);window.addEventListener('prep:play',play);window.addEventListener('prep:open-learning',learn);return()=>{window.removeEventListener('prep:play',play);window.removeEventListener('prep:open-learning',learn);};},[]);
  useEffect(()=>{
    const openAssets=event=>{
      const detail=event.detail??{};
      setAssetRequest(previous=>({category:typeof detail.category==='string'?detail.category:'Todos',assetId:typeof detail.assetId==='string'?detail.assetId:null,revision:previous.revision+1}));
      setMode('assets');setFailed(false);
    };
    window.addEventListener('prep:open-assets',openAssets);
    return ()=>window.removeEventListener('prep:open-assets',openAssets);
  },[]);
  function select(point){setSelected(point);setMode('world');setRevision(r=>r+1);}
  function overview(){setSelected(null);setRevision(r=>r+1);}
  function recordVisit(){
    if(!selected)return;
    const next=discover(progress,selected.id,locationIds);setProgress(next);
    let saved=false;try{saved=writeProgress(window.localStorage,next);}catch{/* session remains usable */}
    setNotice(saved?'Descoberta registrada neste dispositivo.':'Descoberta registrada nesta sessão; o armazenamento está indisponível.');
  }
  function changeMode(next){setMode(next);setFailed(false);if(next==='assets')setAssetRequest(previous=>({category:'Todos',assetId:null,revision:previous.revision+1}));}
  function fullscreen(){
    if(document.fullscreenElement){document.exitFullscreen?.().catch(()=>setNotice('Não foi possível sair da tela cheia.'));return;}
    if(stage.current?.requestFullscreen)stage.current.requestFullscreen().catch(()=>setNotice('Tela cheia indisponível neste navegador.'));
    else setNotice('Tela cheia indisponível neste navegador.');
  }
  return <div className={`world-app ${mode==='cyber'?'world-cyber':''}`}>
    <header className="world-header">
      <a className="world-brand" href="#" onClick={e=>{e.preventDefault();changeMode('world');overview();}}><span className="brand-mark"><GraduationCap size={26}/></span><div><strong>PREPARATÓRIO</strong><small>CONHECIMENTO QUE TRANSFORMA</small></div></a>
      <div className="world-region"><span className="live-dot"/> {mode==='cyber'?'ARAPIRACA · AL':'MACEIÓ · AL'} <span className="region-divider">/</span><span>{mode==='cyber'?'Cidade futurista':'Ilha conceitual'}</span></div>
      <button ref={libraryTrigger} className="header-library" aria-label="Biblioteca" onClick={()=>setLibrary(true)}><BookOpen size={17}/><span>Biblioteca</span></button>
      <div className="coin-balance" title="Pontos locais de demonstração, sem valor financeiro"><span>◈</span><strong>{rewardBalance(progress)}</strong><small>CV · DEMO</small></div>
    </header>
    <main className="world-layout">
      <aside className="destinations" aria-label="Destinos da ilha">
        <div className="sidebar-heading"><span className="eyebrow">SEU MUNDO COMEÇA AQUI</span><h1>Explore.<br/><em>Aprenda. Evolua.</em></h1><p>Do primeiro passo a novos horizontes.</p></div>
        <label className="destination-search"><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Encontrar um destino" aria-label="Buscar destino"/></label>
        <div className="category-list" aria-label="Categorias">{categories.map(c=><button key={c.id} aria-pressed={category===c.id} className={category===c.id?'active':''} onClick={()=>setCategory(c.id)}>{c.name}</button>)}</div>
        <div className="destinations-caption"><span>DESTINOS</span><span>{filtered.length.toString().padStart(2,'0')}</span></div>
        <div className="destination-list">{filtered.length===0?<p className="empty-state">Nenhum destino encontrado.</p>:filtered.map(p=><button key={p.id} className={`destination-row ${selected?.id===p.id?'active':''}`} onClick={()=>select(p)} aria-pressed={selected?.id===p.id}><span className="location-icon" style={{color:p.color}}>{p.symbol}</span><span><strong>{p.name}</strong><small>{p.subtitle}</small></span>{progress.visited.includes(p.id)?<Check size={15} className="visited-check"/>:<ChevronRight size={15}/>}</button>)}</div>
        <div className="sidebar-footer"><span className="live-dot"/> Seu progresso fica neste dispositivo.</div>
      </aside>
      <section className="map-column">
        <div className="map-stage" ref={stage} data-map-status={failed?'error':ready?'ready':'loading'} data-map-triangles={ready?.triangles ?? ''}>
          <div className="map-view" aria-label="Visualização do mundo">
            {mode==='reference'?<img className="reference-map" src={assetUrl("/assets/maps/preparatorio-reference.jpg")} alt="Mapa conceitual original do PREPARATÓRIO fornecido pelo criador"/>:
            <ViewBoundary key={`${mode}-${quality}`} onReference={()=>changeMode('reference')}><Suspense fallback={<div className="map-fallback">Abrindo o mundo…</div>}>
              {mode==='cyber'?<CyberCity/>:mode==='play'?<PlayCampus/>:mode==='assets'?<AssetLibrary key={assetRequest.revision} initialCategory={assetRequest.category} initialAssetId={assetRequest.assetId}/>:mode==='kit'?<KitCanvas/>:<WorldCanvas quality={quality} night={night} locations={filtered} selected={selected} onSelect={select} onReady={onReady} onError={onError} cameraRevision={revision}/>}
            </Suspense></ViewBoundary>}
            {failed&&mode==='world'&&<div className="map-fallback"><p>Não foi possível carregar a ilha.</p><button onClick={()=>changeMode('reference')}>Abrir a imagem do mapa</button><button onClick={()=>{setQuality('mobile');setFailed(false);}}>Tentar versão leve</button></div>}
          </div>
          <div className="map-topbar"><div className="map-title"><span className="eyebrow">{mode==='kit'?'OFICINA DO MUNDO':'UM UNIVERSO DE POSSIBILIDADES'}</span><h2>{mode==='kit'?'Kit modular · 32 peças':'Sua ilha, seu futuro.'}</h2></div><div className="map-modes" aria-label="Tipo de mapa"><button aria-pressed={mode==='cyber'} onClick={()=>changeMode('cyber')}>Arapiraca</button><button aria-pressed={mode==='world'} onClick={()=>changeMode('world')}><Compass size={16}/>Ilha</button><button aria-pressed={mode==='reference'} onClick={()=>changeMode('reference')}><Map size={16}/>Referência</button><button aria-pressed={mode==='kit'} onClick={()=>changeMode('kit')}><Layers3 size={16}/>Kit</button><button aria-pressed={mode==='assets'} onClick={()=>changeMode('assets')}>Acervo 3D</button><button aria-pressed={mode==='play'} onClick={()=>changeMode('play')}>Campus</button></div></div>
          {mode==='world'&&<div className="map-tools"><button title="Visão geral" aria-label="Visão geral" onClick={overview}><Compass size={19}/></button><button title="Alternar luz do dia" aria-label="Alternar dia e noite" aria-pressed={night} onClick={()=>setNight(n=>!n)}>{night?<Sun size={19}/>:<Moon size={19}/>}</button><button title="Tela cheia" aria-label="Tela cheia" onClick={fullscreen}><Maximize2 size={18}/></button></div>}
          {mode==='world'&&<div className="map-quality"><label>Visualização<select aria-label="Qualidade do mapa" value={quality} onChange={e=>{setReady(null);setQuality(e.target.value);}}><option value="mobile">Leve · 2 MB</option><option value="web">Detalhada · 7 MB</option></select></label></div>}
          {!selected&&mode==='world'&&<div className="map-intro"><span className="intro-rule"/><p>Um lugar para estudar.<br/><strong>Um mundo para descobrir.</strong></p><small>Selecione um destino para se aproximar.</small></div>}
          {selected&&mode==='world'&&<article className="destination-card"><button className="card-close" aria-label="Fechar destino" onClick={overview}><X size={17}/></button><span className="eyebrow" style={{color:selected.color}}>{selected.subtitle}</span><h3>{selected.name}</h3><p>{selected.description}</p><div className="destination-actions"><button className="primary-action" disabled={progress.visited.includes(selected.id)||!ready||failed} onClick={recordVisit}>{progress.visited.includes(selected.id)?<><Check size={16}/>Descoberto</>:<>Registrar descoberta <ArrowUpRight size={16}/></>}</button>{selected.id==='hospital'&&<button onClick={()=>window.dispatchEvent(new Event('prep:open-clinical'))}>Atividade hospitalar</button>}</div><small>Marco aproximado no mapa conceitual · sem interiores navegáveis</small></article>}
          {['world','kit'].includes(mode)&&<div className="map-help"><span>ARRASTE PARA GIRAR</span><i/> <span>ROLE OU PINCE PARA APROXIMAR</span></div>}
        </div>
        <section className="journey-strip" aria-label="Progresso da exploração">
          <div className="journey-title"><span className="journey-icon"><GraduationCap size={23}/></span><div><span className="eyebrow">PRIMEIRA JORNADA</span><h3>Conheça sua rede de formação</h3><p>Descubra SENAC, UFAL e Hospital Universitário no mapa.</p></div></div>
          <div className="journey-progress"><div><strong>{missionCount} <span>/ 3 destinos</span></strong><small>{missionCount===3?'Jornada concluída':'Seu futuro começa com um passo'}</small></div><progress max={3} value={missionCount}/></div>
          <button className="journey-next" onClick={()=>select(locations.find(p=>p.id===(INTRO_LOCATIONS.find(id=>!progress.visited.includes(id))??'plaza')))}>{missionCount===3?'Explorar a praça':'Próximo destino'}<ArrowUpRight size={17}/></button>
        </section>
        <div className="world-footer"><span>ESTUDE <b>·</b> PRATIQUE <b>·</b> CONSTRUA SEU FUTURO</span><span>Criação de Romário Vicente Amaro</span></div>
      </section>
    </main>
    {notice&&<div className="world-toast" role="status">{notice}<button aria-label="Fechar aviso" onClick={()=>setNotice('')}><X size={16}/></button></div>}
    <dialog ref={libraryDialog} className="library-dialog" onCancel={e=>{e.preventDefault();setLibrary(false);}} aria-labelledby="library-title"><button className="library-back" onClick={()=>setLibrary(false)}><ArrowLeft size={17}/> Voltar à ilha</button><span className="eyebrow">BIBLIOTECA DE ALEXANDRIA</span><h2 id="library-title">Conhecimento abre caminhos.</h2><p>Uma primeira coleção para orientar sua jornada no PREPARATÓRIO.</p><Suspense fallback={<p>Abrindo aulas…</p>}><KnowledgeLibrary/></Suspense><div className="library-articles"><article><Compass/><h3>Explore a ilha</h3><p>Escolha um destino na lista ou toque em um marcador. Arraste para girar e use dois dedos para aproximar no celular. A imagem original está na aba Referência.</p></article><article><GraduationCap/><h3>Aprenda com situações fictícias</h3><p>No Hospital Universitário, abra a atividade de comunicação hospitalar para organizar informações. O exercício é educacional e não substitui formação ou protocolos profissionais.</p><button onClick={()=>{setLibrary(false);window.dispatchEvent(new Event('prep:open-clinical'));}}>Abrir atividade <ArrowUpRight size={15}/></button></article><article><BookOpen/><h3>Chronovitae nesta versão</h3><p>Cada destino descoberto soma 20 CV uma única vez. São pontos locais de demonstração, sem compra, Pix, carteira digital ou valor financeiro. A limpeza do navegador pode apagar o progresso.</p></article></div><p className="library-note">Ilha inspirada em Maceió. Locais e distâncias são conceituais. As novas instituições, serviços e interiores do documento de referência ainda serão desenvolvidos.</p></dialog>
  </div>;
}
