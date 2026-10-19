import {assetUrl} from '../config/deploymentConfig.js';
import { useGLTF } from "@react-three/drei";

export default function ServerHousing(props) {
  const { scene } = useGLTF(assetUrl("/assets/models/server_housing.glb"));
  return <primitive object={scene} {...props} />;
}
