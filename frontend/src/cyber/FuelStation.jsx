import {useMemo} from 'react';
import {useGLTF} from '@react-three/drei';
import CityAssetBoundary from './CityAssetBoundary.js';
import {fuelStationCanopy,fuelStationPavement,fuelStationPumpX,fuelStationShop,fuelStationZone} from './fuelStation.js';
import modelBase64 from './fuelStationModel.json';
import {setWorldShadows} from './modelLighting.js';

// The small Blender model ships with the city bundle, without a second remote request.
const modelUrl = `data:model/gltf-binary;base64,${modelBase64}`;

function StationBox({position,size,color,walkable=false}) {
  return <mesh position={position} userData={{walkable}} castShadow={!walkable} receiveShadow>
    <boxGeometry args={size}/>
    <meshStandardMaterial color={color} roughness={.7}/>
  </mesh>;
}

function StationFallback() {
  return <group name="PREP_POSTO_RESERVA">
    <StationBox {...fuelStationPavement} color="#959c9e" walkable/>
    <StationBox {...fuelStationCanopy} color="#263a42"/>
    <StationBox position={[-3,5.15,-5.43]} size={[19,.52,.16]} color="#218b8b"/>
    <StationBox {...fuelStationShop} color="#e2e9e5"/>
    {fuelStationPumpX.map(x=><group key={x} position={[x,0,0]}>
      <StationBox position={[0,.10,0]} size={[1.65,.2,5.8]} color="#293c43"/>
      <StationBox position={[0,1.01,0]} size={[.85,1.66,.75]} color="#e2e9e5"/>
      {[-2.2,2.2].map(z=><StationBox key={z} position={[0,2.56,z]} size={[.4,4.72,.4]} color="#e2e9e5"/>)}
    </group>)}
  </group>;
}

function StationModel() {
  const {scene} = useGLTF(modelUrl);
  const model = useMemo(() => setWorldShadows(scene.clone(true)),[scene]);
  return <primitive object={model} dispose={null}/>;
}

export default function FuelStation() {
  return <group name="PREP_POSTO_GASOLINA" position={fuelStationZone.position} userData={{dynamicCollider:true}}>
    <CityAssetBoundary label={fuelStationZone.label} fallback={<StationFallback/>}>
      <StationModel/>
    </CityAssetBoundary>
  </group>;
}
