import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {Html} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {DoubleSide,Group} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {disposeAssetPreview} from '../world/assetPreviewResources.js';
import {cityLivingWorldPlan as plan,campusIsNear,habitatAsset,habitatPath,selectLivingWorldResidents,prepareCityCampusScene,prepareCityCampusShadows} from './cityLivingWorld.js';
import {createLivingAnimal} from './livingAnimalModel.js';
import {setWorldShadows} from './modelLighting.js';

// Resident models deliberately do not use the shared useGLTF cache. Leaving the
// district aborts fetches and releases only resources privately owned here.
function usePrivateModel(url,prepare){
  const runtime=useRef(null),[object,setObject]=useState(null);
  useEffect(()=>{
    const controller=new AbortController();let disposed=false,released=false,loaded=null,prepared=null;
    const release=()=>{if(released||!loaded)return;released=true;prepared?.stop?.();disposeAssetPreview([loaded.scene,prepared?.object]);};
    (async()=>{
      try{
        const response=await fetch(url,{signal:controller.signal});
        if(!response.ok)throw new Error(`HTTP ${response.status}`);
        const bytes=await response.arrayBuffer();
        if(disposed)return;
        loaded=await new GLTFLoader().parseAsync(bytes,new URL('.',response.url||new URL(url,globalThis.location?.href??'http://localhost/')).href);
        if(disposed){release();return;}
        prepared=prepare(loaded);runtime.current=prepared;setObject(prepared.object);
      }catch(error){
        release();
        if(!disposed&&error.name!=='AbortError')console.warn('Elemento opcional do campus indisponível:',url,error.message);
      }
    })();
    return ()=>{disposed=true;controller.abort();runtime.current=null;release();};
  },[url,prepare]);
  return {object,runtime};
}
function prepareCampus(gltf){
  prepareCityCampusScene(gltf.scene);
  setWorldShadows(gltf.scene);
  prepareCityCampusShadows(gltf.scene);
  return {object:gltf.scene};
}
function CampusModel({onInspect}){
  const {object}=usePrivateModel(plan.campus.url,prepareCampus);
  const inspect=event=>{event.stopPropagation();onInspect?.({asset:{id:plan.campus.assetId,name:plan.campus.label,category:'Campus',playable:false},placement:plan.campus});};
  return object?<group position={plan.campus.position} name="CITY_CAMPUS_COURTYARD" onClick={inspect}>
    <primitive object={object} dispose={null}/>
  </group>:null;
}
function prepareOak(gltf){setWorldShadows(gltf.scene);return {object:gltf.scene};}
function OakGrove({onInspect}){
  const {object}=usePrivateModel(plan.vegetation.asset.url,prepareOak);
  const grove=useMemo(()=>{
    if(!object)return null;
    const group=new Group();group.name='CITY_CAMPUS_OAK_GROVE';
    for(const placement of plan.vegetation.placements){
      const tree=object.clone(true);tree.name=`CITY_${placement.id}`;
      tree.position.fromArray(placement.position);tree.rotation.y=placement.rotationY;tree.userData.vegetationAsset=plan.vegetation.asset.id;
      group.add(tree);
    }
    return group;
  },[object]);
  const inspect=event=>{event.stopPropagation();onInspect?.({asset:plan.vegetation.asset,placement:{id:'campus-oak-grove',label:'Bosque de carvalhos do campus'}});};
  return grove?<primitive object={grove} dispose={null} onClick={inspect}/>:null;
}
function Resident({habitat,onInspect}){
  const asset=habitatAsset(habitat);
  const prepare=useCallback(gltf=>createLivingAnimal(gltf,habitat),[habitat]);
  const {object,runtime}=usePrivateModel(asset.url,prepare);
  useFrame((state,delta)=>runtime.current?.update(delta,habitatPath(habitat,state.clock.elapsedTime)));
  const inspect=event=>{event.stopPropagation();onInspect?.({asset,placement:{id:habitat.id,label:habitat.label}});};
  return object?<group position={habitat.position} name={`CITY_${habitat.id}`} userData={{actor:true}} onClick={inspect}>
    <primitive object={object} dispose={null}/>
  </group>:null;
}
function HabitatStructure({habitat:h}){
  const [w,d]=h.size,height=h.fenceHeight,aquarium=h.kind==='aquarium';
  const walls=[{id:'west',at:[-w/2,height/2,0],size:[.16,height,d]},
    {id:'east',at:[w/2,height/2,0],size:[.16,height,d]},
    {id:'north',at:[0,height/2,-d/2],size:[w,height,.16]},
    {id:'south',at:[0,height/2,d/2],size:[w,height,.16]}];
  return <group position={h.position} name={`BOUNDARY_${h.id}`}>
    <mesh position={[0,-.115,0]} receiveShadow userData={{walkable:true}}>
      <boxGeometry args={[w,.23,d]}/><meshStandardMaterial color={aquarium?'#a3b9bc':'#718369'} roughness={.95}/>
    </mesh>
    {walls.map(wall=><group key={wall.id}>
      <mesh position={wall.at} receiveShadow>
        <boxGeometry args={wall.size}/><meshStandardMaterial color={aquarium?'#8bd9e6':'#96bab9'}
          transparent opacity={aquarium?.16:.095} side={DoubleSide} depthWrite={false} roughness={.18} metalness={.1}/>
      </mesh>
      <mesh position={[wall.at[0],height,wall.at[2]]} castShadow>
        <boxGeometry args={[wall.size[0],.12,wall.size[2]]}/><meshStandardMaterial color="#364e55" metalness={.7} roughness={.35}/>
      </mesh>
      {!aquarium&&<mesh position={[wall.at[0],height*.45,wall.at[2]]}>
        <boxGeometry args={[wall.size[0],.08,wall.size[2]]}/><meshStandardMaterial color="#607a7f" metalness={.5} roughness={.5}/>
      </mesh>}
    </group>)}
    {[-1,1].flatMap(x=>[-1,1].map(z=><mesh key={`${x}-${z}`} position={[x*w/2,height/2,z*d/2]} castShadow>
      <boxGeometry args={[.2,height,.2]}/><meshStandardMaterial color="#344a50" metalness={.6} roughness={.4}/>
    </mesh>))}
    {aquarium&&<>
      <mesh position={[0,h.waterSurfaceY,0]} rotation={[-Math.PI/2,0,0]}>
        <planeGeometry args={[w-.18,d-.18]}/><meshStandardMaterial color="#45bad2" transparent opacity={.25} side={DoubleSide} depthWrite={false} roughness={.2}/>
      </mesh>
      <mesh position={[0,.4,-d/2+.14]}><boxGeometry args={[w-.4,.35,.12]}/><meshBasicMaterial color="#35c6d4" toneMapped={false}/></mesh>
    </>}
    <group position={[0,0,d/2+.25]}>
      <mesh position={[0,.75,0]}><boxGeometry args={[.1,1.5,.1]}/><meshStandardMaterial color="#344a50"/></mesh>
      <mesh position={[0,1.55,0]}><boxGeometry args={[3,.65,.12]}/><meshStandardMaterial color="#143c46"/></mesh>
      <Html position={[0,1.57,.09]} center distanceFactor={9} zIndexRange={[1,0]} style={{pointerEvents:'none'}}>
        <span className="cyber-world-label">{h.label}<br/><small>{aquarium?'Observação pelo vidro · ambiente aquático':'Observação pelo lado externo'}</small></span>
      </Html>
    </group>
  </group>;
}
export default function CityLivingWorld({simulation,onInspect,includeGround=true,enabled=true}){
  const status=useRef({ids:[],campus:false}),timer=useRef(Infinity);
  const [visible,setVisible]=useState({ids:[],campus:false});
  useFrame((state,delta)=>{
    timer.current+=delta;if(timer.current<plan.district.updateIntervalSeconds)return;timer.current=0;
    const position=simulation?.current?.position??state.camera.position;
    const ids=enabled?selectLivingWorldResidents(position,status.current.ids):[];
    const campus=enabled&&campusIsNear(position,status.current.campus);
    if(campus!==status.current.campus||ids.join('|')!==status.current.ids.join('|')){
      status.current={ids,campus};setVisible({ids,campus});
    }
  });
  const ground=plan.district.ground,access=plan.district.access;
  const length=Math.hypot(access.to[0]-access.from[0],access.to[2]-access.from[2]);
  return <group name="PREP_CITY_CAMPUS_AND_HABITATS">
    {includeGround&&<>
      <mesh position={[ground.center[0],ground.topY-ground.thickness/2,ground.center[2]]} receiveShadow userData={{walkable:true}}>
        <boxGeometry args={[ground.size[0],ground.thickness,ground.size[1]]}/><meshStandardMaterial color="#6d786c" roughness={1}/>
      </mesh>
      <mesh position={[(access.from[0]+access.to[0])/2,.115,(access.from[2]+access.to[2])/2]}
        rotation={[0,Math.atan2(access.to[0]-access.from[0],access.to[2]-access.from[2]),0]} receiveShadow userData={{walkable:true}}>
        <boxGeometry args={[access.width,.23,length]}/><meshStandardMaterial color="#a8b7b7" roughness={.9}/>
      </mesh>
    </>}
    <Html position={[plan.campus.approach[0],2.4,plan.campus.approach[2]]} center distanceFactor={12} zIndexRange={[1,0]} style={{pointerEvents:'none'}}>
      <span className="cyber-world-label">Campus PREPARATÓRIO<br/><small>Anatomia · estudos · observação da fauna</small></span>
    </Html>
    {visible.campus&&<><CampusModel onInspect={onInspect}/><OakGrove onInspect={onInspect}/></>}
    {plan.habitats.map(h=><HabitatStructure key={h.id} habitat={h}/>)}
    {plan.habitats.filter(h=>visible.ids.includes(h.id)).map(h=><Resident key={h.id} habitat={h} onInspect={onInspect}/>)}
  </group>;
}
