import {useMemo} from 'react';
import {useGLTF} from '@react-three/drei';
import {SRGBColorSpace} from 'three';
import {assetUrl} from '../config/deploymentConfig.js';
import CityAssetBoundary from './CityAssetBoundary.js';
import {setWorldShadows} from './modelLighting.js';
import {mechanicWorkshopAsset,mechanicWorkshopZone} from './mechanicWorkshop.js';

const modelUrl = assetUrl(mechanicWorkshopAsset);

function WorkshopBox({position,size,color,walkable=false}) {
  return <mesh position={position} userData={{walkable}} castShadow={!walkable} receiveShadow>
    <boxGeometry args={size}/>
    <meshStandardMaterial color={color} roughness={.8}/>
  </mesh>;
}

function WorkshopSign({text,color,size,position,rotation}) {
  const canvas = useMemo(() => {
    const image = document.createElement('canvas');
    image.width = 1024;
    image.height = 128;
    const context = image.getContext('2d');
    context.font = 'bold 100px sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = color;
    context.fillText(text, 512, 64, 1000);
    return image;
  }, [text,color]);
  return <mesh position={position} rotation={rotation}>
    <planeGeometry args={size}/>
    <meshBasicMaterial transparent depthWrite={false}>
      <canvasTexture attach="map" args={[canvas]} colorSpace={SRGBColorSpace}/>
    </meshBasicMaterial>
  </mesh>;
}

// Match the Blender export's façade and both walkable surfaces while the GLB is unavailable.
function WorkshopFallback() {
  return <group name="PREP_OFICINA_MECANICA_RESERVA">
    <WorkshopBox position={[-1.5,-.04,15.55]} size={[30,.14,12.9]} color="#818a91" walkable/>
    <WorkshopBox position={[-1.5,-.04,6.47]} size={[22,.14,5.26]} color="#818a91" walkable/>
    <WorkshopBox position={[-.25,2.59,-2.53]} size={[16.8,5.14,12.38]} color="#c2cecb"/>
    <WorkshopBox position={[-.25,5.28,-2.51]} size={[17.18,.26,12.88]} color="#343c40"/>
    <WorkshopBox position={[-.25,4.84,3.95]} size={[17.18,.74,1.3]} color="#19464a"/>
    <WorkshopBox position={[-.25,5.17,4.613]} size={[17.18,.075,.035]} color="#ffcf46"/>
    {[-5.25,1.2].map(x => <group key={x} position={[x,0,0]}>
      <WorkshopBox position={[0,2.04,3.74]} size={[5.2,3.97,.22]} color="#343c40"/>
      <WorkshopBox position={[0,1.95,3.88]} size={[4.84,3.7,.095]} color="#985126"/>
      {Array.from({length:12},(_,row) => <WorkshopBox key={row} position={[0,.27+row*.295,3.934]}
        size={[4.76,.024,.025]} color="#663921"/>)}
    </group>)}
    <WorkshopBox position={[6.52,1.02,3.72]} size={[1.15,1.97,.2]} color="#19464a"/>
    <WorkshopBox position={[6.53,2.76,3.82]} size={[3.2,1.15,.16]} color="#335360"/>
    {[14.6,19.25].map(z => <WorkshopBox key={z} position={[-2.5,.034,z]} size={[21,.007,.12]} color="#ffcf46"/>)}
    {[-13,8].map(x => <WorkshopBox key={x} position={[x,.034,16.925]} size={[.12,.007,4.65]} color="#ffcf46"/>)}
    <WorkshopSign text="OFICINA MECÂNICA" color="#eaf4ee" position={[-.25,4.84,4.64]} size={[7.6,.95]}/>
    <WorkshopSign text="PÁTIO DE SERVIÇO" color="#ffcf46" position={[-2.5,.046,16.925]}
      size={[10.4,1.3]} rotation={[-Math.PI/2,0,0]}/>
  </group>;
}

function WorkshopModel() {
  const {scene} = useGLTF(modelUrl);
  const model = useMemo(() => setWorldShadows(scene.clone(true)), [scene]);
  return <primitive object={model} dispose={null}/>;
}

export default function MechanicWorkshop() {
  return <group name="PREP_OFICINA_MECANICA" position={mechanicWorkshopZone.position}
    rotation={[0, -Math.PI / 2, 0]} userData={{dynamicCollider:true}}>
    <CityAssetBoundary label={mechanicWorkshopZone.label} assetUrls={[modelUrl]} fallback={<WorkshopFallback/>}>
      <WorkshopModel/>
    </CityAssetBoundary>
  </group>;
}
