import {assetUrl} from './deploymentConfig.js';
export const islandRegistry = {
  web: {url:assetUrl('/assets/models/MAP_Preparatorio_Island_Web.glb'),triangles:128225,textureSize:2048},
  mobile: {url:assetUrl('/assets/models/MAP_Preparatorio_Island_Mobile.glb'),triangles:38467,textureSize:1024},
  reference: assetUrl('/assets/maps/preparatorio-reference.jpg'),
  units: 'game meters',
  georeferenced: false,
};
