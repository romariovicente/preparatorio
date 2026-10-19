import {Suspense,useMemo,useRef,useState} from 'react';
import {Html,useGLTF} from '@react-three/drei';
import {useFrame} from '@react-three/fiber';
import {BoxGeometry,Group,Mesh} from 'three';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
import {setWorldShadows} from './modelLighting.js';
import {classroomWorld,createClassroomRuntime,stepClassroomDoor,toggleClassroomDoor} from './classroomWorld.js';

function AnatomyHologram({onInspect}){
  const asset=classroomWorld.educational,gltf=useGLTF(asset.url);
  const model=useMemo(()=>{
    const scene=clone(gltf.scene);
    scene.traverse(mesh=>{
      if(!mesh.isMesh)return;
      // Clone materials only for this exhibit; preserve anatomical layers and
      // the supplied model's bone, tissue and transparent skin colors.
      const illuminated=material=>{
        const copy=material.clone();copy.emissive.copy(copy.color);copy.emissiveIntensity=.22;
        if(copy.transparent)copy.depthWrite=false;
        return copy;
      };
      mesh.material=Array.isArray(mesh.material)?mesh.material.map(illuminated):illuminated(mesh.material);
      mesh.castShadow=false;mesh.receiveShadow=false;
    });
    return scene;
  },[gltf.scene]);
  const inspect=event=>{event?.stopPropagation();onInspect?.({asset:{...asset,id:asset.assetId,name:asset.label,category:'Anatomia',playable:false},placement:{id:'classroom-anatomy',label:asset.label}});};
  return <group name="CLASSROOM_ANATOMY_HOLOGRAM" position={asset.position} onClick={inspect}>
    <mesh position={[0,-.095,0]} receiveShadow><cylinderGeometry args={[.48,.48,.15,48]}/><meshStandardMaterial color="#263b46" metalness={.7} roughness={.35}/></mesh>
    <mesh position={[0,-.013,0]} rotation={[-Math.PI/2,0,0]}><ringGeometry args={[.38,.44,48]}/><meshBasicMaterial color="#6ae9ff" toneMapped={false}/></mesh>
    <primitive object={model} dispose={null}/>
    <pointLight position={[0,.85,.35]} color="#7ae7ef" intensity={1.3} distance={2.5} decay={2}/>
    <Html position={[0,2.12,-.03]} center distanceFactor={7} zIndexRange={[2,0]}>
      <button className="cyber-world-label" onClick={inspect}>{asset.label}<br/><small>Ossos · órgãos · camadas</small></button>
    </Html>
  </group>;
}

function ClassroomModels({simulation,runtime,onDoorState,onInspect}){
  const architecture=useGLTF(classroomWorld.assets[0].url),students=useGLTF(classroomWorld.assets[1].url);
  const [doorLabel,setDoorLabel]=useState('Abrir porta');
  const lastLabel=useRef('Abrir porta'),lastOpen=useRef(false),roomRef=useRef(null);
  const models=useMemo(()=>{
    const room=clone(architecture.scene),people=clone(students.scene),hinge=new Group();
    hinge.name='DOOR_Classroom_Animated';hinge.userData.dynamicCollider=true;
    hinge.position.fromArray(classroomWorld.door.hinge);room.add(hinge);
    room.updateMatrixWorld(true);
    for(const name of [classroomWorld.door.leafNode,classroomWorld.door.handleNode]){
      const leaf=room.getObjectByName(name);if(leaf)hinge.attach(leaf);
    }
    const infill=classroomWorld.door.openingInfill,wall=room.getObjectByName('BLD_Classroom_RearWallLeft');
    if(wall?.material){
      const closure=new Mesh(new BoxGeometry(...infill.size),wall.material);
      closure.name=infill.name;closure.position.fromArray(infill.center);room.add(closure);
    }
    setWorldShadows(room);setWorldShadows(people);
    people.traverse(object=>{if(object.isSkinnedMesh)object.frustumCulled=false;});
    people.userData.actor=true;
    return {room,people,hinge};
  },[architecture.scene,students.scene]);
  useFrame((_,delta)=>{
    const player=simulation?.current,door=stepClassroomDoor(runtime,player?.position,delta,player?.mode??'foot');
    if(!door)return;
    const hinge=roomRef.current?.getObjectByName('DOOR_Classroom_Animated');
    if(hinge){hinge.rotation.y=classroomWorld.door.angleRadians*door.progress;hinge.userData.openProgress=door.progress;}
    const label=door.occupied?'Passagem ocupada · porta aberta':door.open?door.progress<.99?'Abrindo porta…':'Fechar porta':'Abrir porta';
    if(label!==lastLabel.current){lastLabel.current=label;setDoorLabel(label);}
    if(door.open!==lastOpen.current){lastOpen.current=door.open;onDoorState?.({...door});}
  });
  const toggle=event=>{event?.stopPropagation();toggleClassroomDoor(runtime);};
  return <>
    <primitive ref={roomRef} object={models.room} dispose={null} onClick={event=>{if(event.object.parent===models.hinge)toggle(event);}}/>
    <primitive object={models.people} dispose={null}/>
    <group position={[5.53,1.22,-5.98]}>
      <Html position={[0,1.7,-.18]} center distanceFactor={8} zIndexRange={[2,0]}>
        <button className="cyber-world-label" onClick={toggle} aria-label={`${doorLabel} · Sala de aula PREPARATÓRIO`}>{doorLabel}<br/>Sala de aula · PREPARATÓRIO</button>
      </Html>
    </group>
    <AnatomyHologram onInspect={onInspect}/>
    <pointLight position={[0,3.1,0]} color="#edf8ff" intensity={28} distance={16} decay={2}/>
  </>;
}

export default function FuturisticClassroom({simulation,runtime,onDoorState,onInspect}){
  const ownedRuntime=useRef(null);
  if(ownedRuntime.current===null)ownedRuntime.current=createClassroomRuntime();
  return <group name="PREP_FUTURISTIC_CLASSROOM_20261008" position={classroomWorld.center}
    userData={{dynamicCollider:true,classroomId:classroomWorld.id,students:12}}>
    <Suspense fallback={null}><ClassroomModels simulation={simulation} runtime={runtime??ownedRuntime}
      onDoorState={onDoorState} onInspect={onInspect}/></Suspense>
  </group>;
}
