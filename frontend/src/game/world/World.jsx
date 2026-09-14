import { Canvas } from "@react-three/fiber";
import { Environment, Grid, OrbitControls } from "@react-three/drei";

function Ground() {
    return (
        <mesh rotation-x={-Math.PI / 2}>
            <planeGeometry args={[80, 80]} />
            <meshStandardMaterial color="#07131b" />
        </mesh>
    );
}

function HospitalBlock() {
    return (
        <mesh position={[0, 2, -8]}>
            <boxGeometry args={[14, 4, 8]} />
            <meshStandardMaterial color="#dbe9ef" />
        </mesh>
    );
}

function Player() {
    return (
        <group position={[0, 1, 2]}>
            <mesh>
                <capsuleGeometry args={[0.45, 1.2, 4, 12]} />
                <meshStandardMaterial color="#45ddff" />
            </mesh>

            <mesh position={[0, 1, 0]}>
                <sphereGeometry args={[0.4, 24, 24]} />
                <meshStandardMaterial color="#e8b999" />
            </mesh>
        </group>
    );
}

export default function World() {
    return (
        <main className="world">
            <div className="world-hud">
                <strong>PREPARATÓRIO</strong>
                <span>Hospital Central</span>
                <span>📍 Entrada Principal</span>
            </div>

            <Canvas
                camera={{
                    position: [0, 4, 9],
                    fov: 55
                }}
            >
                <color attach="background" args={["#03070c"]} />
                <ambientLight intensity={1.5} />
                <directionalLight
                    position={[5, 10, 5]}
                    intensity={2}
                />
                <Environment preset="city" />
                <Ground />
                <HospitalBlock />
                <Player />
                <Grid
                    infiniteGrid
                    cellSize={1}
                    sectionSize={5}
                    fadeDistance={70}
                    position={[0, 0.01, 0]}
                />
                <OrbitControls />
            </Canvas>
        </main>
    );
}
