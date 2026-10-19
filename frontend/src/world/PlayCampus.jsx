import {sharedServiceLabel} from '../config/serviceStatus.js';
import {assetUrl} from '../config/deploymentConfig.js';
import {Suspense,useEffect,useRef,useState} from 'react';
import {Canvas,useFrame} from '@react-three/fiber';
import {Html,OrbitControls,useGLTF} from '@react-three/drei';
import {PCFShadowMap,Vector3} from 'three';
import {playableCharacters,runtimeAssets} from '../config/runtimeAssets.js';
import SuppliedModel from './SuppliedModel.jsx';
import {advancePosition,campusObstacles} from './movement.js';
import {campusTemplates as templates} from './campusObjects.js';
import {carriedObject} from './interactionState.js';
import {useSharedObjects} from '../network/useSharedObjects.js';
import './play.css';

const kit = runtimeAssets.find(a=>a.id==='SUP_kit_hospital');
const eventId = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function Environment(){const {scene}=useGLTF(assetUrl('/assets/models/ENV_PREP_Campus_v2.glb'));return <primitive object={scene}/>;}
function Part({position=[0,0,0],size,color='#d9e9e9',metalness=.1}){
  return <mesh castShadow receiveShadow position={position}><boxGeometry args={size}/><meshStandardMaterial color={color} roughness={.6} metalness={metalness}/></mesh>;
}
function ObjectShape({kind,carried=false}){
  if(kind==='kit'&&kit)return <SuppliedModel asset={kit} height={carried?.3:.5}/>;
  if(kind==='supplies')return <group><Part position={[0,.2,0]} size={[.48,.4,.36]} color="#267d88"/><Part position={[0,.4,0]} size={[.49,.045,.37]} color="#b9e6e2"/><Part position={[0,.23,.185]} size={[.19,.065,.012]} color="#f2f9f5"/><Part position={[0,.23,.187]} size={[.065,.19,.013]} color="#f2f9f5"/></group>;
  if(kind==='chair')return <group><Part position={[0,.5,0]} size={[.65,.12,.65]} color="#247b89"/><Part position={[0,.89,-.28]} size={[.65,.65,.1]} color="#247b89"/>{[-.23,.23].flatMap(x=>[-.23,.23].map(z=><Part key={`${x}:${z}`} position={[x,.23,z]} size={[.07,.46,.07]} color="#8ab5b5" metalness={.7}/>))}</group>;
  return <group><Part position={[0,.76,0]} size={[.95,.09,.6]}/><Part position={[0,.26,0]} size={[.85,.07,.55]} color="#79aeb4"/>{[-.36,.36].flatMap(x=>[-.2,.2].map(z=><group key={`${x}:${z}`}><Part position={[x,.45,z]} size={[.05,.8,.05]} color="#7dabb4" metalness={.7}/><mesh position={[x,.07,z]} rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.075,.075,.07,12]}/><meshStandardMaterial color="#284653"/></mesh></group>))}<Part position={[0,.85,0]} size={[.32,.1,.3]} color="#26a0a1"/></group>;
}
function Interactable({object,template,selected,onSelect,owned}){
  return <group position={[object.position.x,object.position.y,object.position.z]} onClick={e=>{e.stopPropagation();onSelect(object.id);}}>
    <ObjectShape kind={template.kind}/>
    <mesh rotation={[-Math.PI/2,0,0]} position={[0,.008,0]}><ringGeometry args={[.58,.62,40]}/><meshBasicMaterial color={selected?'#ffbb55':object.kind==='copy'?'#58b39b':'#478c9b'} transparent opacity={selected?.95:.35} depthWrite={false}/></mesh>
    <Html position={[0,template.kind==='cart'||template.kind==='chair'?1.4:.8,0]} center distanceFactor={9} zIndexRange={[1,0]}><button className={`play-object-label ${selected?'selected':''}`} data-object-id={object.id} onClick={e=>{e.stopPropagation();onSelect(object.id);}}>{template.name}{object.kind==='copy'?owned?' · sua cópia':' · outro jogador':''}</button></Html>
  </group>;
}
function Player({asset,input,controls,onMove,action,onMovement,onTargetReached,held,objects}){
  const ref=useRef(null),previous=useRef(false),elapsed=useRef(0);
  const [walking,setWalking]=useState(false);
  const heldTemplate=templates.find(t=>t.id===held?.templateId);
  const clip=walking?'Walk':action??(held&&asset.clips?.includes('Carry')?'Carry':'Idle');
  useFrame(({camera},delta)=>{
    const current=ref.current;if(!current)return;
    const keys=input.current;
    const forward=new Vector3();camera.getWorldDirection(forward);forward.y=0;forward.normalize();
    const right=new Vector3().crossVectors(forward,new Vector3(0,1,0));
    const direction=forward.multiplyScalar((keys.w?1:0)-(keys.s?1:0)).add(right.multiplyScalar((keys.d?1:0)-(keys.a?1:0)));
    if(keys.target&&direction.lengthSq()===0){
      if(Math.hypot(keys.target.x-current.position.x,keys.target.z-current.position.z)>1.55)direction.set(keys.target.x-current.position.x,0,keys.target.z-current.position.z);
      else onTargetReached();
    }else if(direction.lengthSq()>0&&keys.target)onTargetReached();
    const obstacles=[...campusObstacles,...objects.filter(o=>o.position).map(o=>({x:o.position.x,z:o.position.z,w:.5,d:.5}))];
    const next=advancePosition(current.position,direction,delta,keys.shift?3.6:2.2,obstacles);
    const dx=next.x-current.position.x,dz=next.z-current.position.z,moving=Math.hypot(dx,dz)>.00001;
    if(moving){current.rotation.y=Math.atan2(dx,dz);current.position.x=next.x;current.position.z=next.z;camera.position.add(new Vector3(dx,0,dz));controls.current?.target.add(new Vector3(dx,0,dz));}
    if(previous.current!==moving){previous.current=moving;setWalking(moving);if(moving)onMovement();}
    elapsed.current+=delta;if(elapsed.current>.15){elapsed.current=0;onMove({x:current.position.x,z:current.position.z,heading:current.rotation.y,clip});}
  });
  return <group ref={ref} position={[0,0,6]}><SuppliedModel asset={asset} height={1.7} playing clip={clip} holding={Boolean(held)}/>{heldTemplate&&<group position={[0,1.0,.4]}><ObjectShape kind={heldTemplate.kind} carried/></group>}</group>;
}
function RemotePlayer({player,actorId,world}){
  const asset=playableCharacters.find(a=>a.id===player.characterId)??playableCharacters[0];
  const held=carriedObject(world,actorId),heldTemplate=templates.find(t=>t.id===held?.templateId);
  if(!asset||!player.position)return null;
  return <group position={[player.position.x,0,player.position.z]} rotation={[0,player.heading??0,0]}><SuppliedModel asset={asset} height={1.7} playing clip={player.animation??'Idle'} holding={Boolean(held)}/>{heldTemplate&&<group position={[0,1.0,.4]}><ObjectShape kind={heldTemplate.kind} carried/></group>}<Html position={[0,2,0]} center zIndexRange={[1,0]}><span className="play-other-player">Outro jogador</span></Html></group>;
}

export default function PlayCampus(){
  const [character,setCharacter]=useState(()=>{let id;try{id=localStorage.getItem('prep.character.v1');}catch{/* default */}return playableCharacters.find(a=>a.id===id)??playableCharacters.find(a=>a.id==='SUP_doctor_horror_hospital')??playableCharacters[0];});
  const {state:world,actorId,status,dispatch,publishPosition}=useSharedObjects('campus');
  const [selectedId,setSelectedId]=useState(null),[placement,setPlacement]=useState(null),[action,setAction]=useState(null);
  const [notice,setNotice]=useState('Clique em um objeto e aproxime seu personagem para interagir.');
  const input=useRef({}),controls=useRef(null),actionTimer=useRef(null);
  const [position,setPosition]=useState({x:0,z:6,heading:0,clip:'Idle'});
  const selected=world.objects.find(o=>o.id===selectedId),template=templates.find(t=>t.id===selected?.templateId);
  const held=carriedObject(world,actorId);
  const connected=status==='connected';
  const nearby=selected&&(selected.carriedBy===actorId||selected.position&&Math.hypot(position.x-selected.position.x,position.z-selected.position.z)<=2.25);
  const permitted=selected&&(selected.kind==='base'||selected.ownerId===actorId)&&connected;
  const hasDance=character?.clips?.includes('Dance');
  const others=Object.entries(world.players).filter(([id,p])=>id!==actorId&&p.online);
  useEffect(()=>()=>window.clearTimeout(actionTimer.current),[]);
  async function command(type,object,target){
    if(!object)return;
    if(!connected){setNotice('Conecte o servidor local para compartilhar ações e objetos.');return;}
    const result=await dispatch({type,eventId:eventId(),objectId:object.id,expectedRevision:object.revision,position:target});
    setNotice(result.message);
    if(result.ok){setPlacement(null);if(result.createdId)setSelectedId(result.createdId);if(type==='PICKUP')setAction(null);if(type==='RETURN')setSelectedId(null);if(type==='USE'&&character.clips?.includes('Interact')){setAction('Interact');window.clearTimeout(actionTimer.current);actionTimer.current=window.setTimeout(()=>setAction(null),1600);}}
  }
  function onMove(next){setPosition(next);publishPosition({x:next.x,y:0,z:next.z},{animation:next.clip,heading:next.heading,characterId:character.id});}
  function selectObject(id){setSelectedId(id);setPlacement(null);setNotice('Escolha uma ação para o objeto selecionado.');}
  function toggleDance(){input.current={};window.clearTimeout(actionTimer.current);setAction(value=>value==='Dance'?null:'Dance');setNotice(action==='Dance'?'Dança encerrada.':'Seu personagem está dançando. Caminhar também encerra a dança.');}
  useEffect(()=>{
    const map={ArrowUp:'w',ArrowDown:'s',ArrowLeft:'a',ArrowRight:'d'};
    function key(e,pressed){if(pressed&&(document.querySelector('dialog[open]')||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)))return;const code=map[e.key]??e.key.toLowerCase();if(['w','a','s','d','shift'].includes(code)){e.preventDefault();input.current[code]=pressed;}}
    const down=e=>key(e,true),up=e=>key(e,false),blur=()=>{input.current={};};
    window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',blur);
    return()=>{window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',blur);};
  },[]);
  if(!character)return <p>Preparando personagens.</p>;
  return <section className="play-surface" aria-label="Pátio jogável" data-player-id={actorId} data-player-x={position.x.toFixed(3)} data-player-z={position.z.toFixed(3)} data-player-animation={position.clip} data-carried-item={held?.id??''} data-object-copies={world.objects.filter(o=>o.kind==='copy').length}>
    <Canvas key={character.id} shadows={{type:PCFShadowMap}} dpr={[1,1.5]} camera={{position:[7,5,14],fov:48,near:.1,far:300}}><color attach="background" args={['#b8dce1']}/><fog attach="fog" args={['#b8dce1',45,100]}/><ambientLight intensity={1.8}/><directionalLight position={[8,20,10]} intensity={2.5} castShadow shadow-mapSize={[1024,1024]}/>
      <Suspense fallback={<Html center><div className="map-loading">Preparando o pátio…</div></Html>}><Environment/><Player asset={character} input={input} controls={controls} onMove={onMove} action={action} onMovement={()=>setAction(null)} onTargetReached={()=>{input.current={...input.current,target:null};}} held={held} objects={world.objects}/>{others.map(([id,p])=><RemotePlayer key={id} actorId={id} player={p} world={world}/>)}{world.objects.filter(o=>o.position).map(o=><Interactable key={o.id} object={o} template={templates.find(t=>t.id===o.templateId)} selected={selectedId===o.id} owned={o.ownerId===actorId} onSelect={selectObject}/>)}</Suspense>
      {placement&&<mesh position={[0,.012,0]} rotation={[-Math.PI/2,0,0]} onClick={e=>{e.stopPropagation();command(placement,placement==='DROP'?held:selected,{x:e.point.x,y:0,z:e.point.z});}}><planeGeometry args={[18,17]}/><meshBasicMaterial color="#6dc9be" transparent opacity={.18} depthWrite={false}/></mesh>}
      <OrbitControls ref={controls} makeDefault target={[0,1,6]} minDistance={3} maxDistance={25} maxPolarAngle={Math.PI/2.1}/>
    </Canvas>
    <div className="play-heading"><span className="eyebrow">CAMPUS DE TESTES</span><h2>Caminhe. Interaja. Organize.</h2><p>WASD ou setas · clique nos objetos para escolher uma ação</p></div>
    <label className="play-character">Personagem<select value={character.id} onChange={e=>{const next=playableCharacters.find(a=>a.id===e.target.value);setCharacter(next);setAction(null);setPlacement(null);input.current={};setPosition({x:0,z:6,heading:0,clip:'Idle'});try{localStorage.setItem('prep.character.v1',next.id);}catch{/* session only */}}}>{playableCharacters.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select><button className="play-dance" disabled={!hasDance||Boolean(held)} aria-pressed={action==='Dance'} onClick={toggleDance}>{action==='Dance'?'Parar de dançar':'Dançar'}</button>{!hasDance&&<small>Este personagem ainda não possui a animação de dança.</small>}</label>
    <div className="play-pad" aria-label="Controles de movimento">{[['w','↑','Caminhar para frente'],['a','←','Caminhar para esquerda'],['s','↓','Caminhar para trás'],['d','→','Caminhar para direita']].map(([key,icon,label])=><button key={key} aria-label={label} onClick={e=>{if(e.detail===0){input.current[key]=true;window.setTimeout(()=>{input.current[key]=false;},180);}}} onPointerDown={e=>{e.currentTarget.setPointerCapture(e.pointerId);input.current[key]=true;}} onPointerUp={()=>{input.current[key]=false;}} onPointerCancel={()=>{input.current[key]=false;}}>{icon}</button>)}</div>
    {selected&&<aside className="play-interactions" aria-label="Ações do objeto">
      <div><span className="eyebrow">{selected.kind==='copy'?selected.ownerId===actorId?'SUA CÓPIA':'CÓPIA DE OUTRO JOGADOR':'OBJETO BASE'}</span><button aria-label="Fechar ações do objeto" onClick={()=>{setSelectedId(null);setPlacement(null);}}>×</button></div>
      <h3>{template.name}</h3><p>{template.description}</p>
      {!nearby&&<button onClick={()=>{input.current.target=selected.position;setNotice('O personagem está se aproximando do objeto.');}}>Ir até o objeto</button>}
      <div className="play-object-actions">
        {template.portable&&!selected.carriedBy&&<button disabled={!nearby||Boolean(held)||!permitted} onClick={()=>command('PICKUP',selected)}>{selected.kind==='base'?'Pegar cópia':'Recolher cópia'}</button>}
        <button disabled={!nearby||!permitted} onClick={()=>command('USE',selected)}>{template.actionLabel}</button>
        {template.movable&&selected.position&&<button disabled={!nearby||!permitted} onClick={()=>{setPlacement('MOVE');input.current={};setNotice('Clique em um espaço livre próximo do personagem para reposicionar.');}}>{selected.kind==='base'?'Mover uma cópia':'Reposicionar'}</button>}
        {selected.carriedBy===actorId&&<button disabled={!connected} onClick={()=>{setPlacement('DROP');input.current={};setNotice('Clique no chão próximo do personagem para colocar sua cópia.');}}>Colocar no chão</button>}
        {selected.kind==='copy'&&selected.ownerId===actorId&&<button disabled={!connected||!nearby} onClick={()=>command('RETURN',selected)}>Devolver cópia</button>}
      </div>
      {placement&&<div className="play-placement"><p>Clique na área verde para escolher a posição.</p><button onClick={()=>command(placement,placement==='DROP'?held:selected,{x:position.x+Math.sin(position.heading+Math.PI/2)*1.15,y:0,z:position.z+Math.cos(position.heading+Math.PI/2)*1.15})}>Colocar ao lado</button><button onClick={()=>setPlacement(null)}>Cancelar</button></div>}
    </aside>}
    {held&&selectedId!==held.id&&<button className="play-held" onClick={()=>selectObject(held.id)}>Carregando: {templates.find(t=>t.id===held.templateId).name} · ações</button>}
    <div className="play-notice" role="status">{notice}</div>
    <div className="play-footer"><span className={connected?'play-connected':'play-offline'}>{sharedServiceLabel(connected?'connected':'offline',others.length+1)}</span><button onClick={()=>window.dispatchEvent(new Event('prep:open-learning'))}>Entrar nas aulas</button></div>
  </section>;
}
