import {resolveAssetReferences} from '../config/deploymentConfig.js';
import {useEffect, useMemo} from 'react';
import {useAnimations, useGLTF} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {Box3,Vector3} from 'three';
import costumesRaw from '../config/costumeAssets.json';
const costumes=resolveAssetReferences(costumesRaw);
import {createCarryAnimations} from '../world/carryAnimation.js';
import {createSeatedClone} from './seating.js';
import {createUprightPosture} from './posture.js';
import {createCharacterClone,findCharacterAction,startCharacterAction} from '../world/characterModel.js';
import {createUniformNameTexture} from './uniformName.js';
import {applyUniformName,applyUniformOutfit,cloneUniformMaterials} from './uniformMaterials.js';
import {createFrozenCharacterClone} from '../world/frozenCharacter.js';

function AnimatedCharacter({assetId,url, costumed, replacedMeshes, height, outfit, playing, clip, idleClip, holding, sitting, riding, displayName,standingPose}) {
  const gltf = useGLTF(url);
  const prepared = useMemo(() => {
    let group;
    if (sitting) {
      const pose = createSeatedClone(gltf.scene, height ?? 1.7, riding);
      group = pose.group;
      group.position.y = pose.offset;
    } else {
      // Several supplied rigs have a very different bind pose from their real
      // Idle/Walk. Normalize them from the authored Idle sample; otherwise the
      // Anime CyberStyle becomes ~8 m tall as soon as its clip starts. Remy's
      // verified Mixamo derivative keeps its already-correct preparation.
      const normalizationPose=standingPose??(assetId!=='CHR_Remy_Mixamo_20261005'&&idleClip?{clip:idleClip,time:0}:null);
      if(normalizationPose){
        const normalized=createFrozenCharacterClone(gltf.scene,height,gltf.animations,normalizationPose);
        group=normalized.group;
        normalized.poseMixer?.stopAllAction();
        normalized.poseMixer?.uncacheRoot(group);
      }else group=createCharacterClone(gltf.scene,height).group;
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
    return {group, materials,groundBounds:new Box3(),parentOrigin:new Vector3(),parentScale:new Vector3()};
  }, [gltf.scene, gltf.animations, assetId, idleClip, costumed, height, sitting, riding,standingPose]);
  const carry = useMemo(() => createCarryAnimations(gltf.animations), [gltf.animations]);
  const {actions,mixer} = useAnimations(carry.clips, prepared.group);
  const upright=useMemo(()=>createUprightPosture(prepared.group),[prepared.group]);
  useFrame(()=>{
    if(sitting)return;
    if(playing)upright(clip);
    // Remy already has a verified ground-preserving Mixamo export. Other
    // animated sources may contain vertical root motion; pin their visible
    // shoes to the actor parent's floor after the animation sample is applied.
    if(!playing||assetId==='CHR_Remy_Mixamo_20261005')return;
    const bounds=prepared.groundBounds.makeEmpty();prepared.group.updateMatrixWorld(true);
    prepared.group.traverse(object=>{if(object.isMesh&&object.visible!==false)bounds.expandByObject(object,true);});
    if(bounds.isEmpty()||!Number.isFinite(bounds.min.y))return;
    const parent=prepared.group.parent;
    const floorY=parent?parent.getWorldPosition(prepared.parentOrigin).y:0;
    const scaleY=parent?Math.abs(parent.getWorldScale(prepared.parentScale).y)||1:1;
    const correction=(floorY-bounds.min.y)/scaleY;
    /* eslint-disable react-hooks/immutability -- Three.js scene nodes are imperative render objects updated per frame. */
    if(Number.isFinite(correction)&&Math.abs(correction)>.0005)prepared.group.position.y+=correction;
    /* eslint-enable react-hooks/immutability */
  });
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

function FixedPoseCharacter({asset,height}){
  const gltf=useGLTF(asset.url);
  const prepared=useMemo(()=>createFrozenCharacterClone(gltf.scene,height,gltf.animations,asset.characterStandingPose),[gltf.scene,gltf.animations,height,asset.characterStandingPose]);
  return <primitive object={prepared.group} dispose={null}/>;
}

// Only independently reimported derivatives can receive fitted clothing.
export default function CostumedCharacter({asset, height=1.7, outfit, playing=false, clip='Idle', holding=false, sitting=false, riding=false, displayName}) {
  if(asset.characterControlMode==='fixed-pose'||asset.characterControlMode==='static-pose')return <FixedPoseCharacter asset={asset} height={height}/>;
  const costume = costumes.find(record => record.baseId === asset.id && record.reimportValidated);
  const costumed = Boolean(costume && outfit && (outfit.scrubs !== false || outfit.coat));
  const url = costumed ? costume.url : asset.url;
  return <AnimatedCharacter key={`${url}:${sitting ? 'seated' : 'standing'}`} assetId={asset.id} url={url}
    costumed={costumed} replacedMeshes={costume?.replacedMeshes} height={height} outfit={outfit} playing={playing} clip={clip} idleClip={asset.idleClip}
    holding={holding} sitting={sitting} riding={riding} displayName={displayName} standingPose={asset.characterStandingPose}/>;
}
