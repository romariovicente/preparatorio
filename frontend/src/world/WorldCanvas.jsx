import { Component, Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html, OrbitControls, useGLTF, useProgress } from '@react-three/drei';
import { Box3, Raycaster, Vector3 } from 'three';
import { islandRegistry } from '../config/islandRegistry.js';

class MapBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onError(); }
  render() { return this.state.failed ? null : this.props.children; }
}

function Loading() {
  const { progress } = useProgress();
  return <Html center><div className="map-loading" role="status">Preparando sua ilha…<strong>{Math.round(progress)}%</strong></div></Html>;
}

function Island({ url, locations, selected, onSelect, onReady }) {
  const { scene } = useGLTF(url);
  const map = useMemo(() => scene.clone(true), [scene]);
  const markers = useMemo(() => {
    map.updateMatrixWorld(true);
    const ray = new Raycaster();
    return locations.map(point => {
      ray.set(new Vector3(point.position[0], 100, point.position[1]), new Vector3(0,-1,0));
      const hit = ray.intersectObject(map,true)[0];
      return {...point, height: (hit?.point.y ?? 12) + 5};
    });
  }, [map,locations]);
  useEffect(() => {
    const bounds = new Box3().setFromObject(map); let meshes=0,triangles=0;
    map.traverse(o => {if(o.isMesh){meshes++; triangles+=(o.geometry.index?.count ?? o.geometry.attributes.position.count)/3;}});
    onReady({ meshes, triangles, dimensions:bounds.getSize(new Vector3()).toArray() });
  },[map,onReady]);
  return <>
    <primitive object={map} />
    {markers.map(point => <Html key={point.id} position={[point.position[0],point.height,point.position[1]]} center zIndexRange={[30,10]}>
      <button className={`map-pin ${selected?.id === point.id ? 'selected' : ''}`} style={{'--pin-color':point.color}} onClick={() => onSelect(point)} aria-label={`Selecionar ${point.name}`} title={point.name}>
        <span>{point.symbol}</span>{selected?.id === point.id && <b>{point.name}</b>}
      </button>
    </Html>)}
  </>;
}

function CameraRig({ destination, revision }) {
  const controls = useRef(); const { camera, size } = useThree();
  const motion = useRef(null);
  useEffect(() => {
    const target = destination ? new Vector3(destination.position[0],10,destination.position[1]) : new Vector3(0,8,0);
    const fit = Math.max(1, 1.15 / (size.width / size.height));
    const position = destination ? target.clone().add(new Vector3(0,85,105).multiplyScalar(Math.sqrt(fit))) : new Vector3(30,340,365).multiplyScalar(fit);
    motion.current={target,position};
  },[destination,revision,size.width,size.height]);
  useFrame((_,dt) => {
    if(!motion.current || !controls.current) return;
    const factor=1-Math.exp(-dt*4);
    camera.position.lerp(motion.current.position,factor);
    controls.current.target.lerp(motion.current.target,factor);
    controls.current.update();
    if(camera.position.distanceTo(motion.current.position)<.05) motion.current=null;
  });
  return <OrbitControls ref={controls} makeDefault enableDamping minDistance={35} maxDistance={1250} maxPolarAngle={Math.PI*.46} onStart={() => { motion.current=null; }} />;
}

export default function WorldCanvas({ quality, night, locations, selected, onSelect, onReady, onError, cameraRevision }) {
  const url=islandRegistry[quality === 'web' ? 'web' : 'mobile'].url;
  return <Canvas dpr={[1,1.5]} camera={{position:[30,340,365],fov:47,near:1,far:2600}} gl={{antialias:true}} aria-label="Mapa tridimensional da ilha PREPARATÓRIO">
    <color attach="background" args={[night ? '#061421':'#143d50']} />
    <ambientLight intensity={night ? 1.0:2.1} />
    <directionalLight position={[-100,280,140]} intensity={night ? .5:2.2} color={night ? '#a2c7ff':'#fff3de'} />
    <hemisphereLight args={['#cbf3ff','#364e42',night ? .4:1.2]} />
    <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.6,0]}><planeGeometry args={[2000,2000]} /><meshStandardMaterial color={night ? '#072637':'#116579'} roughness={.5} metalness={.1}/></mesh>
    <MapBoundary key={url} onError={onError}><Suspense fallback={<Loading/>}><Island url={url} locations={locations} selected={selected} onSelect={onSelect} onReady={onReady}/></Suspense></MapBoundary>
    <CameraRig destination={selected} revision={cameraRevision}/>
  </Canvas>;
}
