import {useEffect,useMemo} from 'react';
import {DataTexture,LinearFilter,Object3D} from 'three';
import {lowBeamMaskLevel,vehicleLightOutputs} from './vehicleLighting.js';

const LAMP_COLORS={main:'#fff7e4',marker:'#e9f5ff',fog:'#ffe2ae',driving:'#fff7e4',bar:'#fff7e4',work:'#fff7e4'};

function createLowBeamMask(pitch,angle) {
  const width=64,height=128;
  const pixels=new Uint8Array(width*height*4);
  for(let y=0;y<height;y++){
    for(let x=0;x<width;x++){
      const offset=4*(y*width+x);
      const level=Math.round(255*lowBeamMaskLevel(pitch,angle,(x+.5)/width,(y+.5)/height));
      pixels.set([level,level,level,255],offset);
    }
  }
  const texture=new DataTexture(pixels,width,height);
  texture.magFilter=texture.minFilter=LinearFilter;
  texture.needsUpdate=true;
  return texture;
}

function Beam({optic}) {
  const target=useMemo(()=>new Object3D(),[]);
  const low=optic.id==='low';
  const pitch=Math.atan2(optic.origin[1]-optic.target[1],optic.target[2]-optic.origin[2]);
  const cutoff=useMemo(()=>low?createLowBeamMask(pitch,optic.angle):null,[low,pitch,optic.angle]);
  useEffect(()=>()=>cutoff?.dispose(),[cutoff]);
  return <>
    <primitive object={target} position={optic.target}/>
    <spotLight target={target} position={optic.origin} color={optic.color} intensity={optic.power}
      distance={optic.reach} angle={optic.angle} penumbra={.65} decay={2}
      map={cutoff} shadow-camera-near={.05}/>
  </>;
}

export default function VehicleLights({profile,value,powered,illuminate,daylight}) {
  const {lamps,beams}=vehicleLightOutputs(profile,value,powered,illuminate,daylight);
  return <group name="vehicle-lighting">
    {lamps.flatMap(id=>profile.lamps[id].map(({position,size,surfaceZ},index)=>
      <mesh key={`${id}-${index}`} position={[position[0],position[1],surfaceZ??position[2]]}
        rotation={id==='work'?[0,Math.PI,0]:[0,0,0]} scale={[size[0],size[1],1]} raycast={()=>null}>
        <circleGeometry args={[.5,16]}/>
        <meshBasicMaterial color={LAMP_COLORS[id]} toneMapped={false}/>
      </mesh>
    ))}
    {beams.map(optic=><Beam key={optic.id} optic={optic}/>)}
  </group>;
}
