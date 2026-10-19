import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";
import ServerHousing from "./ServerHousing";

function LoadingCube() {
  return (
    <mesh position={[0, 1, 0]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="orange" wireframe={true} />
    </mesh>
  );
}

export default function GameWorld() {
  return (
    <Canvas camera={{ position: [0, 5, 10] }} style={{ width: "100vw", height: "100vh" }}>
      <color attach="background" args={['#111111']} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[10, 20, 10]} intensity={1} />
      
      <Grid infiniteGrid cellSize={1} sectionSize={5} fadeDistance={30} />

      {/* Tenta carregar o Servidor. Enquanto carrega, mostra o Cubo Laranja */}
      <Suspense fallback={<LoadingCube />}>
        <ServerHousing scale={1} position={[0, 0, 0]} />
      </Suspense>

      <OrbitControls />
    </Canvas>
  );
}
