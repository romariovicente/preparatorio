import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import { PCFShadowMap } from 'three';
import SuppliedModel from '../world/SuppliedModel.jsx';
import { runtimeAssets as assets } from '../config/runtimeAssets.js';
import { carriedObject, createInteractionState } from '../world/interactionState.js';
import { useSharedObjects } from '../network/useSharedObjects.js';
import { HOSPITAL_START, hospitalPlacementAllowed, hospitalTemplates, routeToHospitalObject, stepHospitalPlayer } from './hospitalObjects.js';
import interactionCss from './hospital-interactions.css?inline';

const asPoint = ([x, y, z]) => ({ x, y, z });
const asArray = ({ x, y, z }) => [x, y, z];
const templates = hospitalTemplates.map(template => ({ ...template, position: asPoint(template.position) }));
const shadowSettings = { type: PCFShadowMap };
const kit = assets.find(asset => asset.id === 'SUP_kit_hospital');
const defaultCharacter = () => assets.find(a => a.id === 'SUP_woman_standing_v16') ?? assets.find(a => a.playable);

function Box({ position, size, color, ...props }) {
  return <mesh position={position} castShadow receiveShadow {...props}>
    <boxGeometry args={size} /><meshStandardMaterial color={color} roughness={0.8} />
  </mesh>;
}
function Person({ position, color }) {
  return <group position={position}>
    <Box position={[0, 1, 0]} size={[0.55, 0.7, 0.35]} color={color} />
    <mesh position={[0, 1.65, 0]} castShadow><sphereGeometry args={[0.25, 16, 12]} /><meshStandardMaterial color="#ad7957" /></mesh>
    {[-0.17, 0.17].map(x => <Box key={x} position={[x, 0.35, 0]} size={[0.22, 0.7, 0.3]} color="#294556" />)}
  </group>;
}
function ObjectShape({ template, carried = false }) {
  if (template.kind === 'kit' && kit) return <Suspense fallback={<Box position={[0, .2, 0]} size={[.45, .35, .3]} color="#edc479"/>}><SuppliedModel asset={kit} height={carried ? .38 : .5}/></Suspense>;
  if (template.kind === 'tray') return <group>
    <Box position={[0, .05, 0]} size={[.6, .06, .4]} color="#b8dce3"/>
    {[-.29,.29].map(x => <Box key={x} position={[x, .08, 0]} size={[.025,.07,.4]} color="#7894a0"/>)}
  </group>;
  if (template.kind === 'chair') return <group>
    <Box position={[0, .5, 0]} size={[.6, .13, .6]} color="#71b4ac"/>
    <Box position={[0, .85, -.26]} size={[.6, .65, .12]} color="#71b4ac"/>
    {[-.24,.24].flatMap(x => [-.24,.24].map(z => <Box key={`${x}-${z}`} position={[x,.24,z]} size={[.05,.48,.05]} color="#697f88"/>))}
  </group>;
  return <group>
    {[.25,.9].map(y => <Box key={y} position={[0,y,0]} size={[.9,.09,.75]} color="#b4ccd2"/>)}
    {[-.37,.37].flatMap(x => [-.29,.29].map(z => <group key={`${x}-${z}`}>
      <Box position={[x,.52,z]} size={[.05,.8,.05]} color="#687f8e"/>
      <mesh position={[x,.09,z]} rotation={[0,0,Math.PI/2]} castShadow><cylinderGeometry args={[.085,.085,.06,12]}/><meshStandardMaterial color="#293e49"/></mesh>
    </group>))}
  </group>;
}
function RoomObject({ object, selected, onSelect }) {
  const template = templates.find(t => t.id === object.templateId);
  if (!template) return null;
  return <group position={asArray(object.position)} onClick={event => { event.stopPropagation(); onSelect(object.id); }}>
    <ObjectShape template={template}/>
    {selected && <mesh position={[0,.005,0]} rotation={[-Math.PI/2,0,0]}>
      <ringGeometry args={[.38,.46,32]}/><meshBasicMaterial color="#f6c876" transparent opacity={.95}/>
    </mesh>}
  </group>;
}
function Visitor({ character, position, heading, clip, held }) {
  const group = useRef(null);
  useFrame((_, delta) => {
    if (!group.current) return;
    const factor = 1 - Math.exp(-12 * delta);
    group.current.position.x += (position[0] - group.current.position.x) * factor;
    group.current.position.z += (position[2] - group.current.position.z) * factor;
    group.current.rotation.y = heading;
  });
  return <group ref={group} position={HOSPITAL_START}>
    <Suspense fallback={<Person position={[0,0,0]} color="#e7bb78"/>}>
      {character ? <SuppliedModel asset={character} height={1.7} playing clip={clip} holding={Boolean(held)}/> : <Person position={[0,0,0]} color="#e7bb78"/>}
    </Suspense>
    {held && <group position={[0,1,.4]}><ObjectShape template={templates.find(t => t.id === held.templateId)} carried/></group>}
  </group>;
}
function furnitureFrom(state) {
  return state.objects.filter(object => object.position && (object.kind === 'copy' || templates.find(t => t.id === object.templateId)?.movable)).map(object => ({
    id: object.id, position: asArray(object.position), size: templates.find(t => t.id === object.templateId)?.size ?? [.5,.5],
  }));
}

export default function HospitalScene({ onInteract }) {
  const shared = useSharedObjects('hospital');
  const { publishPosition } = shared;
  const fallback = useMemo(() => createInteractionState(templates), []);
  const state = shared.state ?? fallback, actorId = shared.actorId;
  const collisionState = useRef(state);
  const [position, setPosition] = useState([...HOSPITAL_START]);
  const [heading, setHeading] = useState(0), [path, setPath] = useState([]);
  const [selectedId, setSelectedId] = useState('base:hospital_kit');
  const [action, setAction] = useState('Idle'), [placeMode, setPlaceMode] = useState(null);
  const [notice, setNotice] = useState('Selecione um objeto e aproxime o personagem.');
  const [busy, setBusy] = useState(false);
  const [character, setCharacter] = useState(() => {
    let id; try { id = localStorage.getItem('prep.character.v1'); } catch { /* default visitor */ }
    return assets.find(a => a.id === id && a.category === 'Personagens') ?? defaultCharacter();
  });
  const selected = state.objects.find(object => object.id === selectedId);
  const selectedTemplate = templates.find(t => t.id === selected?.templateId);
  const held = carriedObject(state, actorId);
  const walking = path.length > 0, clip = walking ? 'Walk' : action;
  const canWalk = character?.playable, animations = character?.animations ?? [];
  const connected = shared.status === 'connected';
  const owned = selected?.kind !== 'copy' || selected.ownerId === actorId;

  useEffect(() => { collisionState.current = state; }, [state]);

  useEffect(() => {
    const update = event => {
      const next = assets.find(a => a.id === event.detail && a.category === 'Personagens');
      if (next) { setCharacter(next); setAction('Idle'); setPath([]); }
    };
    window.addEventListener('prep:character', update);
    return () => window.removeEventListener('prep:character', update);
  }, []);
  useEffect(() => {
    if (!path.length) return;
    const timer = window.setTimeout(() => {
      const next = path[0];
      if (!hospitalPlacementAllowed(next, [.5,.5], furnitureFrom(collisionState.current))) {
        setPath([]); setNotice('O corredor mudou. Escolha outro caminho.'); return;
      }
      setHeading(Math.atan2(next[0] - position[0], next[2] - position[2]));
      setPosition(next); setPath(path.slice(1));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [path, position]);
  useEffect(() => {
    if (action !== 'Interact') return;
    const timer = window.setTimeout(() => setAction('Idle'), 2200);
    return () => window.clearTimeout(timer);
  }, [action]);
  useEffect(() => {
    if (connected) publishPosition(asPoint(position), { heading, animation: clip, characterId: character?.id });
  }, [publishPosition, position, heading, clip, character?.id, connected]);

  function choose(id) { setSelectedId(id); setPlaceMode(null); }
  function approach() {
    if (!canWalk || !selected?.position) return;
    const route = routeToHospitalObject(position, asArray(selected.position), furnitureFrom(state));
    if (route === null) { setNotice('Não há um caminho livre até este objeto.'); return; }
    setPath(route); setAction('Idle'); setNotice(route.length ? 'O personagem está se aproximando pelo corredor livre.' : 'Você já está perto deste objeto.');
  }
  function step(direction) {
    if (!canWalk) return;
    setPath([]); setAction('Idle');
    const next = stepHospitalPlayer(position, direction, furnitureFrom(state));
    if (next === position) { setNotice('Esse caminho está ocupado. Use o corredor livre.'); return; }
    setHeading(Math.atan2(direction[0], direction[1])); setPath([next]);
  }
  async function perform(type, object = selected, target) {
    if (!object || busy) return;
    const template = templates.find(t => t.id === object.templateId);
    const occupied = [...furnitureFrom(state), { id: `player:${actorId}`, position, size: [.5,.5] },
      ...Object.entries(state.players).filter(([id, player]) => id !== actorId && player.online !== false && player.position)
        .map(([id, player]) => ({ id: `player:${id}`, position: asArray(player.position), size: [.5,.5] })),
    ];
    if (target && !hospitalPlacementAllowed(target, template.size, occupied, object.kind === 'base' && type === 'MOVE' ? undefined : object.id)) {
      setNotice('Esse espaço está ocupado ou fora da sala. Escolha um local livre.'); return;
    }
    setBusy(true);
    try {
      const result = await shared.dispatch({ type, objectId: object.id, expectedRevision: object.revision,
        ...(target ? { position: asPoint(target) } : {}) });
      setNotice(result.message);
      if (result.ok) {
        setPlaceMode(null);
        if (type === 'PICKUP') setSelectedId(carriedObject(result.state, actorId).id);
        if (type === 'MOVE' && object.kind === 'base') {
          const created = result.state.objects.find(item => item.kind === 'copy' && item.ownerId === actorId && !state.objects.some(previous => previous.id === item.id));
          if (created) setSelectedId(created.id);
        }
        if (type === 'USE' && animations.includes('Interact')) setAction('Interact');
        if (type === 'RETURN') setSelectedId(`base:${object.templateId}`);
      }
    } catch { setNotice('A conexão com a sala foi interrompida. Tente novamente quando a conexão voltar.');
    } finally { setBusy(false); }
  }
  function floorClick(event) {
    if (!placeMode) return;
    event.stopPropagation();
    perform(placeMode, placeMode === 'DROP' ? held : selected, [event.point.x, 0, event.point.z]);
  }
  function moveFurniture(direction) {
    if (!selected?.position) return;
    const step = selected.kind === 'base' ? 1.15 : .45;
    perform('MOVE', selected, [selected.position.x + direction[0] * step, 0, selected.position.z + direction[1] * step]);
  }
  function dropNear() {
    perform('DROP', held, [position[0] + Math.sin(heading) * .9, 0, position[2] + Math.cos(heading) * .9]);
  }
  const directions = [[0,-1,'↑','Norte'],[-1,0,'←','Oeste'],[1,0,'→','Leste'],[0,1,'↓','Sul']];
  const blocked = busy || walking || !connected || !owned;

  return <div className="hospital-viewer" data-hospital-held={held?.templateId ?? ''} data-hospital-copies={state.objects.filter(o => o.kind === 'copy').length} data-hospital-network={shared.status} data-hospital-player-x={position[0].toFixed(2)} data-hospital-player-z={position[2].toFixed(2)}>
    <style>{interactionCss}</style>
    <Canvas shadows={shadowSettings} dpr={[1, 1.5]} camera={{ position: [11, 10, 13], fov: 45 }} fallback={<p>A visualização 3D está indisponível. Use a atividade ao lado.</p>}>
      <color attach="background" args={['#c3dce0']} />
      <ambientLight intensity={1.5} /><directionalLight position={[5, 10, 4]} intensity={2} castShadow />
      <Box position={[0, -0.15, 0]} size={[11, 0.3, 9]} color="#dae5df" onClick={floorClick}/>
      <Box position={[0, 1.5, -4]} size={[11, 3, 0.2]} color="#72b6b0" />
      <Box position={[-5, 1.5, 0]} size={[0.2, 3, 8]} color="#eef0e5" />
      {[-2.8, 0].map(x => <group key={x} position={[x, 0, -1.6]}>
        <Box position={[0, 0.65, 0]} size={[1.7, 0.2, 2.5]} color="#78b8c5" />
        <Box position={[0, 0.82, -0.7]} size={[1.3, 0.18, 0.55]} color="#ffffff" />
        {[-0.6, 0.6].map(side => <Box key={side} position={[side, 0.3, 0]} size={[0.1, 0.6, 2]} color="#718896" />)}
      </group>)}
      <Box position={[2.8, 0.6, 1.6]} size={[2.5, 1.2, 0.9]} color="#427d86" />
      <Box position={[2.8, 1.6, 1.6]} size={[1.2, 0.75, 0.12]} color="#274654" />
      <Box position={[2.8, 1.6, 1.68]} size={[1, 0.55, 0.03]} color="#9ee4c3" />
      {state.objects.filter(object => object.position).map(object => <RoomObject key={object.id} object={object} selected={selectedId === object.id} onSelect={choose}/>)}
      <Person position={[1, 0, 2.1]} color="#5ab6ac" />
      <Visitor character={character} position={position} heading={heading} clip={clip} held={held}/>
      {Object.entries(state.players).filter(([id, player]) => id !== actorId && player.position && player.online !== false).map(([id, player]) => <Visitor key={id} character={assets.find(a => a.id === player.characterId) ?? defaultCharacter()} position={asArray(player.position)} heading={player.heading ?? 0} clip={player.animation ?? 'Idle'} held={carriedObject(state,id)}/>)}
      <Html position={[2.8, 2.6, 1.6]} center zIndexRange={[1, 0]}><button className="scene-start" onClick={onInteract}>Estação SBAR/SOAP</button></Html>
      <OrbitControls makeDefault target={[0, 0.5, 0]} minDistance={7} maxDistance={22} maxPolarAngle={Math.PI / 2.1} />
    </Canvas>
    <details className="hospital-object-panel" open>
      <summary>Objetos e ações no hospital</summary>
      <label htmlFor="hospital-object">Selecionar objeto</label>
      <select id="hospital-object" value={selectedId} onChange={event => choose(event.target.value)}>
        {state.objects.map(object => <option key={object.id} value={object.id}>{templates.find(t => t.id === object.templateId)?.name ?? 'Objeto'}{object.kind === 'copy' ? object.ownerId === actorId ? ' · sua cópia' : ' · cópia de outro jogador' : ' · base'}</option>)}
      </select>
      <div className="hospital-actions">
        <button onClick={approach} disabled={!canWalk || !selected?.position || walking}>Aproximar personagem</button>
        <button onClick={() => perform('INSPECT')} disabled={blocked}>Examinar</button>
        {selectedTemplate?.portable && !selected?.carriedBy && <button onClick={() => perform('PICKUP')} disabled={!!held || blocked}>{selected?.kind === 'base' ? 'Pegar cópia' : 'Recolher cópia'}</button>}
        <button onClick={() => perform('USE', held ?? selected)} disabled={busy || walking || !connected || (!held && !owned)}>Interagir com objeto</button>
      </div>
      {held && <><p>Carregando: <strong>{templates.find(t => t.id === held.templateId)?.name}</strong></p><div className="hospital-actions"><button onClick={dropNear} disabled={busy || walking || !connected}>Colocar à frente</button><button onClick={() => { setPlaceMode('DROP'); setNotice('Clique num ponto livre do chão, perto do personagem.'); }} disabled={busy || walking || !connected}>Escolher onde soltar</button></div></>}
      {selected?.kind === 'copy' && owned && <div className="hospital-actions"><button onClick={() => perform('RETURN')} disabled={blocked}>Devolver esta cópia</button></div>}
      {selectedTemplate?.movable && <><p>{selected?.kind === 'base' ? `Criar uma cópia de ${selectedTemplate.name.toLocaleLowerCase('pt-BR')} · afastamento de 1,15 m` : `Mover sua cópia · passo de 0,45 m`}</p><div className="hospital-controls">{directions.map(([x,z,symbol,name]) => <button key={name} aria-label={`Mover cópia de ${selectedTemplate.name} para ${name}`} onClick={() => moveFurniture([x,z])} disabled={blocked}>{symbol}</button>)}</div><div className="hospital-actions"><button onClick={() => { setPlaceMode('MOVE'); setNotice('Clique num ponto livre do chão, perto do personagem. O móvel base continuará no lugar.'); }} disabled={blocked}>Escolher destino da cópia</button></div></>}
      {placeMode && <div className="hospital-actions"><button onClick={() => setPlaceMode(null)}>Cancelar escolha no chão</button></div>}
      <p>Deslocar personagem pelo corredor</p>
      <div className="hospital-controls">{directions.map(([x,z,symbol,name]) => <button key={name} aria-label={`Personagem: ir para ${name}`} onClick={() => step([x,z])} disabled={!canWalk}>{symbol}</button>)}</div>
      <div className="hospital-actions"><button disabled={!animations.includes('Dance') || walking || !!held} onClick={() => setAction(action === 'Dance' ? 'Idle' : 'Dance')}>{action === 'Dance' ? 'Parar dança' : 'Dançar'}</button><button onClick={() => { setAction('Idle'); setPath([]); }}>Parar personagem</button></div>
      {!canWalk && <p>Esta pose ainda precisa de ajuste para caminhar. Escolha um personagem de caminhada no acervo.</p>}
      <p className="hospital-status" role="status" aria-live="polite">{notice}</p>
      <p className="hospital-session-note">{connected ? 'Sala local compartilhada: cada jogador recebe uma cópia pessoal; os objetos base continuam disponíveis.' : shared.status === 'offline' ? 'Servidor local indisponível. As ações com objetos estão suspensas; a atividade SBAR/SOAP continua disponível.' : 'Conectando à sala local. A atividade SBAR/SOAP continua disponível.'}</p>
    </details>
  </div>;
}
