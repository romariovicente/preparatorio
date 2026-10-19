import {resolveAssetReferences} from '../config/deploymentConfig.js';
import {useEffect, useMemo} from 'react';
import {useAnimations, useGLTF} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import costumesRaw from '../config/costumeAssets.json';
const costumes=resolveAssetReferences(costumesRaw);
import {createCarryAnimations} from '../world/carryAnimation.js';
import {createSeatedClone} from './seating.js';
import {createUprightPosture} from './posture.js';
import {createCharacterClone,findCharacterAction,startCharacterAction} from '../world/characterModel.js';
import {createUniformNameTexture} from './uniformName.js';
import {applyUniformName,applyUniformOutfit,cloneUniformMaterials} from './uniformMaterials.js';

function AnimatedCharacter({url, costumed, replacedMeshes, height, outfit, playing, clip, holding, sitting, riding, displayName}) {
  const gltf = useGLTF(url);
  const prepared = useMemo(() => {
    let group;
    if (sitting) {
      const pose = createSeatedClone(gltf.scene, height ?? 1.7, riding);
      group = pose.group;
      group.position.y = pose.offset;
    } else {
      group = createCharacterClone(gltf.scene,height).group;
    }
    group.traverse(object => {
      if (!object.isMesh) return;
      object.castShadow = true;
      object.receiveShadow = true;
      if(object.isSkinnedMesh)object.frustumCulled=false;
    });
    // SkeletonUtils copies the skeleton, while the loader's materials remain
    // shared. Give recolorable clothing its own materials before any changes.
    const materials = costumed ? cloneUniformMaterials(group) : [];
    return {group, materials};
  }, [gltf.scene, costumed, height, sitting, riding]);
  const carry = useMemo(() => createCarryAnimations(gltf.animations), [gltf.animations]);
  const {actions,mixer} = useAnimations(carry.clips, prepared.group);
  const upright=useMemo(()=>createUprightPosture(prepared.group),[prepared.group]);
  useFrame(()=>{if(!sitting&&playing)upright(clip);});
  const coat = Boolean(outfit?.coat), scrubs = outfit?.scrubs !== false;
  const color = /^#[\da-f]{6}$/i.test(outfit?.color ?? '') ? outfit.color : null;

  useEffect(() => {
    if (!costumed) return;
    applyUniformOutfit(prepared.group,{coat,scrubs,color},replacedMeshes);
  }, [prepared, costumed, replacedMeshes, coat, scrubs, color]);
  useEffect(() => () => prepared.materials.forEach(material => material.dispose()), [prepared]);
  useEffect(() => {
    if (!costumed) return;
    const texture=createUniformNameTexture(displayName);
    applyUniformName(prepared.group,texture);
    return ()=>texture.dispose();
  },[prepared,costumed,displayName]);

  useEffect(() => {
    if (sitting) return;
    const locomotion = clip?.toLowerCase().endsWith('walk') ? 'Walk' : 'Idle';
    const requested = holding && carry.overlayName ? carry.holdingNames[locomotion] ?? clip : clip;
    const wanted = requested?.toLowerCase();
    const action = findCharacterAction(actions,playing?wanted:'Idle');
    startCharacterAction(action,mixer,playing);
    return () => action?.stop();
  }, [actions, mixer, playing, clip, holding, sitting, carry]);
  useEffect(() => {
    if (sitting) return;
    const overlay = carry.overlayName && actions[carry.overlayName];
    if (!overlay) return;
    if (holding && playing) {
      overlay.reset().setEffectiveWeight(1).play();
      // A frozen sample of the real Interact arm tracks retains Walk leg motion.
      /* eslint-disable react-hooks/immutability -- Three.js AnimationAction is an imperative mixer object. */
      overlay.time = carry.overlayTime;
      overlay.paused = true;
      /* eslint-enable react-hooks/immutability */
    } else overlay.stop();
    return () => overlay.stop();
  }, [actions, holding, playing, sitting, carry]);
  return <primitive object={prepared.group} dispose={null}/>;
}

// Only independently reimported derivatives can receive fitted clothing.
export default function CostumedCharacter({asset, height=1.7, outfit, playing=false, clip='Idle', holding=false, sitting=false, riding=false, displayName}) {
  const costume = costumes.find(record => record.baseId === asset.id && record.reimportValidated);
  const costumed = Boolean(costume && outfit && (outfit.scrubs !== false || outfit.coat));
  const url = costumed ? costume.url : asset.url;
  return <AnimatedCharacter key={`${url}:${sitting ? 'seated' : 'standing'}`} url={url}
    costumed={costumed} replacedMeshes={costume?.replacedMeshes} height={height} outfit={outfit} playing={playing} clip={clip}
    holding={holding} sitting={sitting} riding={riding} displayName={displayName}/>;
}
