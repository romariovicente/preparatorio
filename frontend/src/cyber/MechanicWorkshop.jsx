import {useMemo} from 'react';
import {useGLTF} from '@react-three/drei';
import {assetUrl} from '../config/deploymentConfig.js';
import CityAssetBoundary from './CityAssetBoundary.js';
import {setWorldShadows} from './modelLighting.js';
import {mechanicWorkshopAsset,mechanicWorkshopZone} from './mechanicWorkshop.js';

const modelUrl = assetUrl(mechanicWorkshopAsset);

function WorkshopModel() {
  const {scene} = useGLTF(modelUrl);
  const model = useMemo(() => setWorldShadows(scene.clone(true)), [scene]);
  return <group name="PREP_OFICINA_MECANICA" position={mechanicWorkshopZone.position}
    rotation={[0, -Math.PI / 2, 0]} userData={{dynamicCollider:true}}>
    <primitive object={model} dispose={null}/>
  </group>;
}

export default function MechanicWorkshop() {
  return <CityAssetBoundary label={mechanicWorkshopZone.label} assetUrls={[modelUrl]}>
    <WorkshopModel/>
  </CityAssetBoundary>;
}
