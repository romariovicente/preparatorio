import React, { useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Sky } from '@react-three/drei';
import PlayerController from './player/PlayerController';

export default function GameWorld() {
  const [playerPosition, setPlayerPosition] = useState([0, 0.9, 0]);
  const [cameraMode, setCameraMode] = useState('third'); // 'third' ou 'first'

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* UI Overlay para alternar câmera */}
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'rgba(0,0,0,0.6)', padding: '12px', color: '#fff', borderRadius: '8px', fontFamily: 'sans-serif' }}>
        <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 'bold' }}>PREPARATÓRIO 3D</p>
        <button 
          onClick={() => setCameraMode(prev => prev === 'third' ? 'first' : 'third')}
          style={{ background: '#4f46e5', color: '#fff', border: 'none', padding: '8px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          Câmera: {cameraMode === 'third' ? '3ª Pessoa' : '1ª Pessoa'}
        </button>
      </div>

      <Canvas>
        <ambientLight intensity={0.7} />
        <directionalLight position={[10, 20, 15]} intensity={1} />
        <Sky sunPosition={[100, 20, 100]} />
        
        {/* Chão do Mundo */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
          <planeGeometry args={[100, 100]} />
          <meshStandardMaterial color="#34d399" />
        </mesh>

        {/* Representação 3D do Jogador */}
        <mesh position={playerPosition}>
          <boxGeometry args={[0.8, 1.8, 0.8]} />
          <meshStandardMaterial color="#4f46e5" />
        </mesh>

        {/* Controlador de Movimento e Câmera */}
        <PlayerController 
          position={playerPosition} 
          setPosition={setPlayerPosition} 
          cameraMode={cameraMode} 
        />
      </Canvas>
    </div>
  );
}
