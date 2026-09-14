import { Canvas } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';

function Box({ position, size, color }) {
  return (
    <mesh position={position} castShadow receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color={color} roughness={0.8} />
    </mesh>
  );
}

function Person({ position, color }) {
  return (
    <group position={position}>
      <Box
        position={[0, 1, 0]}
        size={[0.55, 0.7, 0.35]}
        color={color}
      />
      <mesh position={[0, 1.65, 0]} castShadow>
        <sphereGeometry args={[0.25, 16, 12]} />
        <meshStandardMaterial color="#ad7957" />
      </mesh>
      {[-0.17, 0.17].map(x => (
        <Box
          key={x}
          position={[x, 0.35, 0]}
          size={[0.22, 0.7, 0.3]}
          color="#294556"
        />
      ))}
    </group>
  );
}

export default function HospitalScene({ onInteract }) {
  return (
    <Canvas
      shadows
      dpr={[1, 1.5]}
      camera={{ position: [11, 10, 13], fov: 45 }}
      fallback={
        <p>A visualização 3D está indisponível. Use a atividade ao lado.</p>
      }
    >
      <color attach="background" args={['#c3dce0']} />
      <ambientLight intensity={1.5} />
      <directionalLight
        position={[5, 10, 4]}
        intensity={2}
        castShadow
      />

      <Box
        position={[0, -0.15, 0]}
        size={[11, 0.3, 9]}
        color="#dae5df"
      />
      <Box
        position={[0, 1.5, -4]}
        size={[11, 3, 0.2]}
        color="#72b6b0"
      />
      <Box
        position={[-5, 1.5, 0]}
        size={[0.2, 3, 8]}
        color="#eef0e5"
      />

      {[-2.8, 0].map(x => (
        <group key={x} position={[x, 0, -1.6]}>
          <Box
            position={[0, 0.65, 0]}
            size={[1.7, 0.2, 2.5]}
            color="#78b8c5"
          />
          <Box
            position={[0, 0.82, -0.7]}
            size={[1.3, 0.18, 0.55]}
            color="#ffffff"
          />
          {[-0.6, 0.6].map(side => (
            <Box
              key={side}
              position={[side, 0.3, 0]}
              size={[0.1, 0.6, 2]}
              color="#718896"
            />
          ))}
        </group>
      ))}

      <Box
        position={[2.8, 0.6, 1.6]}
        size={[2.5, 1.2, 0.9]}
        color="#427d86"
      />
      <Box
        position={[2.8, 1.6, 1.6]}
        size={[1.2, 0.75, 0.12]}
        color="#274654"
      />
      <Box
        position={[2.8, 1.6, 1.68]}
        size={[1, 0.55, 0.03]}
        color="#9ee4c3"
      />

      <Person position={[1, 0, 2.1]} color="#5ab6ac" />
      <Person position={[-2, 0, 2.1]} color="#e7bb78" />

      <Html position={[2.8, 2.6, 1.6]} center>
        <button className="scene-start" onClick={onInteract}>
          Estação SBAR/SOAP
        </button>
      </Html>

      <OrbitControls
        makeDefault
        target={[0, 0.5, 0]}
        minDistance={7}
        maxDistance={22}
        maxPolarAngle={Math.PI / 2.1}
      />
    </Canvas>
  );
}
