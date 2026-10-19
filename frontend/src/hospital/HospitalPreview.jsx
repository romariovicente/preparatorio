import {applicationPath} from '../config/deploymentConfig.js';
import { Component, useCallback, useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Environment, Html, Lightformer, OrbitControls, useCursor } from '@react-three/drei';
import { ACESFilmicToneMapping, MathUtils, PCFSoftShadowMap, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { ArrowLeft, ArrowUpRight, DoorOpen, Layers3, MousePointer2, RotateCcw } from 'lucide-react';
import { createDoorController, disposeHospitalModel, hasNamedAncestor, HOSPITAL_ASSET_URL, inspectHospitalModel, PUBLIC_DOOR_PREFIX } from './hospitalModel.js';
import './hospital-preview.css';

function Unavailable({ onRetry, graphics = false }) {
  return <div className="hospital-stage-message" role="alert">
    <span className="hospital-message-mark">!</span>
    <h2>{graphics ? 'A prévia 3D não pôde ser aberta.' : 'O módulo ainda não pôde ser carregado.'}</h2>
    <p>{graphics ? 'Este navegador não conseguiu iniciar a visualização. Você pode tentar abrir novamente.' : 'O arquivo da recepção está indisponível no momento. Tente carregar novamente em instantes.'}</p>
    <button onClick={onRetry}><RotateCcw size={16} /> Tentar novamente</button>
  </div>;
}

class PreviewBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <Unavailable graphics onRetry={this.props.onRetry} /> : this.props.children;
  }
}

function HospitalModel({ model, doorOpen, roomsOpen, roofVisible, onToggleDoor }) {
  const controllers = useRef({ publicDoor: null, rooms: null });
  const [hovered, setHovered] = useState(false);
  useCursor(hovered);
  useEffect(() => {
    controllers.current = {
      publicDoor: createDoorController(model.scene, model.info.doorClips),
      rooms: createDoorController(model.scene, model.info.roomClips),
    };
    return () => {
      controllers.current.publicDoor?.dispose();
      controllers.current.rooms?.dispose();
      controllers.current = { publicDoor: null, rooms: null };
    };
  }, [model]);
  useEffect(() => {
    model.info.roofNodes.forEach(object => { object.visible = roofVisible; });
  }, [model, roofVisible]);
  useFrame((_, delta) => {
    controllers.current.publicDoor?.update(doorOpen, delta);
    controllers.current.rooms?.update(roomsOpen, delta);
  });
  function isDoor(event) {
    return Boolean(model.info.doorClips.length && hasNamedAncestor(event.object, PUBLIC_DOOR_PREFIX));
  }
  return <><primitive object={model.scene} dispose={null}
    onClick={event => { if (isDoor(event)) { event.stopPropagation(); onToggleDoor(); } }}
    onPointerOver={event => { if (isDoor(event)) setHovered(true); }}
    onPointerOut={() => setHovered(false)}
  />{!roofVisible && model.info.triageWaypoints.map(waypoint => <Html key={waypoint.id} position={waypoint.position} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}><span className="hospital-waypoint"><span />{waypoint.label}</span></Html>)}</>;
}

function InspectionCamera({ info, revision }) {
  const controls = useRef(null);
  const { camera, size } = useThree();
  useEffect(() => {
    const center = info.bounds.getCenter(new Vector3());
    const target = new Vector3(center.x, info.bounds.min.y + info.size.y * 0.38, center.z);
    const verticalFov = MathUtils.degToRad(camera.fov);
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * size.width / size.height);
    const radius = info.size.length() / 2;
    const distance = radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.05;
    const direction = new Vector3(0.72, 0.55, 1).normalize();
    camera.position.copy(target).addScaledVector(direction, distance);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
    if (controls.current) {
      controls.current.target.copy(target);
      controls.current.update();
    }
  }, [camera, info, revision, size.width, size.height]);
  return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.08} minDistance={2} maxDistance={180} minPolarAngle={0.08} maxPolarAngle={Math.PI / 2 - 0.01} />;
}

function StudioLighting({ info }) {
  const center = info.bounds.getCenter(new Vector3());
  return <>
    <hemisphereLight args={['#e6f3ff', '#66736b', 1.7]} />
    <directionalLight castShadow position={[center.x + 20, 34, center.z + 24]} intensity={3.2} color="#fff2dc"
      shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-camera-left={-34} shadow-camera-right={34}
      shadow-camera-top={34} shadow-camera-bottom={-34} shadow-camera-near={1} shadow-camera-far={100} shadow-bias={-0.0003} shadow-normalBias={0.04} />
    <directionalLight position={[center.x - 22, 16, center.z - 10]} intensity={1.1} color="#c5deff" />
    <Environment resolution={128}>
      <Lightformer form="rect" intensity={2.5} color="#e6f0ff" position={[0, 20, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[28, 28, 1]} />
      <Lightformer form="rect" intensity={1.3} color="#fff0d9" position={[0, 10, 24]} rotation={[0, Math.PI, 0]} scale={[30, 16, 1]} />
      <Lightformer form="rect" intensity={0.9} color="#a5c8e2" position={[-24, 8, 0]} rotation={[0, Math.PI / 2, 0]} scale={[24, 14, 1]} />
    </Environment>
  </>;
}

export default function HospitalPreview() {
  const [attempt, setAttempt] = useState(0);
  const [asset, setAsset] = useState({ status: 'loading', model: null });
  const [doorOpen, setDoorOpen] = useState(false);
  const [roomsOpen, setRoomsOpen] = useState(false);
  const [roofVisible, setRoofVisible] = useState(true);
  const [cameraRevision, setCameraRevision] = useState(0);
  const doorAvailable = Boolean(asset.model?.info.doorClips.length);
  const roofAvailable = Boolean(asset.model?.info.roofNodes.length);
  const roomsAvailable = Boolean(asset.model?.info.roomClips.length);
  const toggleDoor = useCallback(() => { if (doorAvailable) setDoorOpen(value => !value); }, [doorAvailable]);
  const resetCamera = useCallback(() => setCameraRevision(value => value + 1), []);

  useEffect(() => {
    let active = true;
    let loadedScene = null;
    const abort = new AbortController();
    async function load() {
      try {
        const response = await fetch(HOSPITAL_ASSET_URL, { signal: abort.signal });
        if (!response.ok) throw new Error('Arquivo indisponível.');
        const data = await response.arrayBuffer();
        const base = new URL('./', new URL(HOSPITAL_ASSET_URL, window.location.href)).href;
        const gltf = await new GLTFLoader().parseAsync(data, base);
        loadedScene = gltf.scene;
        if (!active) { disposeHospitalModel(loadedScene); loadedScene = null; return; }
        const info = inspectHospitalModel(gltf.scene, gltf.animations);
        setAsset({ status: 'ready', model: { scene: gltf.scene, info } });
      } catch (error) {
        if (active && error.name !== 'AbortError') setAsset({ status: 'error', model: null });
      }
    }
    load();
    return () => { active = false; abort.abort(); if (loadedScene) disposeHospitalModel(loadedScene); };
  }, [attempt]);

  useEffect(() => {
    function handleKey(event) {
      if (event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
      if (event.key.toLowerCase() === 'o') { event.preventDefault(); toggleDoor(); }
      if (event.key.toLowerCase() === 'r') { event.preventDefault(); resetCamera(); }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [toggleDoor, resetCamera]);

  function retry() {
    setAsset({ status: 'loading', model: null });
    setDoorOpen(false);
    setRoomsOpen(false);
    setAttempt(value => value + 1);
  }

  return <main className="hospital-preview">
    <header className="hospital-header">
      <a className="hospital-back" href={applicationPath('')}><ArrowLeft size={17} /><span>Voltar à cidade</span></a>
      <a href={applicationPath('')} className="hospital-brand">PREPARATÓRIO<span>ESPAÇOS PARA APRENDER</span></a>
      <span className="hospital-edition">ESTUDO ESPACIAL <b>01</b></span>
    </header>

    <section className="hospital-heading" aria-labelledby="hospital-title">
      <div><span className="hospital-eyebrow">ARQUITETURA · AMBIENTE DE APRENDIZAGEM</span><h1 id="hospital-title">Recepção hospitalar<span>.</span></h1></div>
      <p className="hospital-status"><span />Inspeção do módulo · disponível na cidade</p>
    </section>

    <div className="hospital-workspace">
      <section className="hospital-stage" aria-label="Visualização 3D do módulo hospitalar" aria-busy={asset.status === 'loading'} data-hospital-status={asset.status}>
        {asset.status === 'loading' && <div className="hospital-stage-message" role="status"><span className="hospital-loader" /><h2>Carregando o módulo hospitalar…</h2><p>Preparando a recepção para a inspeção em 3D.</p></div>}
        {asset.status === 'error' && <Unavailable onRetry={retry} />}
        {asset.status === 'ready' && <PreviewBoundary key={attempt} onRetry={retry}>
          <Canvas shadows camera={{ position: [31, 23, 39], fov: 42, near: 0.1, far: 500 }} dpr={[1, 1.75]}
            gl={{ antialias: true, alpha: false, toneMapping: ACESFilmicToneMapping, toneMappingExposure: 1 }}
            onCreated={({ gl }) => { gl.shadowMap.type = PCFSoftShadowMap; }} fallback={<Unavailable graphics onRetry={retry} />}>
            <color attach="background" args={['#182b33']} />
            <StudioLighting info={asset.model.info} />
            <HospitalModel model={asset.model} doorOpen={doorOpen} roomsOpen={roomsOpen} roofVisible={roofVisible} onToggleDoor={toggleDoor} />
            <InspectionCamera info={asset.model.info} revision={cameraRevision} />
          </Canvas>
        </PreviewBoundary>}
        <div className="hospital-stage-caption"><span className="hospital-stage-dot" />MÓDULO DE RECEPÇÃO <span className="hospital-caption-line" /><span>ESCALA EM METROS</span></div>
        <div className="hospital-stage-help"><MousePointer2 size={14} /><span>Arraste para girar · role para aproximar</span></div>
      </section>

      <aside className="hospital-inspector" aria-label="Controles da prévia">
        <div className="hospital-inspector-title"><span className="hospital-eyebrow">EXPLORE O ESPAÇO</span><h2>Um primeiro<br /> contato.</h2><p>Inspecione o acesso público, a recepção e a disposição dos ambientes deste módulo.</p></div>
        <div className="hospital-control-card">
          <div className="hospital-control-caption"><DoorOpen size={19} /><span>ACESSO PÚBLICO</span><kbd>O</kbd></div>
          <h3>Porta deslizante</h3>
          <p>Use o botão ou clique na porta dupla para acompanhar sua abertura.</p>
          <button className="hospital-primary" disabled={!doorAvailable} onClick={toggleDoor} aria-pressed={doorOpen}>{doorOpen ? 'Fechar porta' : 'Abrir porta'}<ArrowUpRight size={17} /></button>
          <span className="hospital-control-state" role="status">{asset.status !== 'ready' ? 'Aguardando o modelo' : !doorAvailable ? 'Animação indisponível neste arquivo' : doorOpen ? 'Porta aberta' : 'Porta fechada'}</span>
        </div>
        <div className="hospital-control-card hospital-roof-card">
          <div className="hospital-control-caption"><Layers3 size={18} /><span>VISÃO DO INTERIOR</span></div>
          <p>Oculte a cobertura para observar a organização interna.</p>
          <button className="hospital-secondary" disabled={!roofAvailable} aria-pressed={!roofVisible} onClick={() => setRoofVisible(value => !value)}>{roofVisible ? 'Ocultar cobertura' : 'Mostrar cobertura'}</button>
          {roomsAvailable && <button className="hospital-secondary" aria-pressed={roomsOpen} onClick={() => setRoomsOpen(value => !value)}>{roomsOpen ? 'Fechar portas internas' : 'Abrir portas internas'}</button>}
        </div>
        <button className="hospital-reset" disabled={asset.status !== 'ready'} onClick={resetCamera}><RotateCcw size={15} />Redefinir câmera<kbd>R</kbd></button>
        <p className="hospital-module-note">Módulo em desenvolvimento. Esta prévia apresenta a recepção e seu acesso; novos setores serão construídos em etapas.</p>
      </aside>
    </div>
    <footer className="hospital-footer"><span>01 / RECEPÇÃO & ACESSO</span><span>Arraste com o botão direito ou use dois dedos para deslocar a vista.</span><span>1 unidade = 1 metro</span></footer>
  </main>;
}
