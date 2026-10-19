import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, Line } from '@react-three/drei';
import { AdditiveBlending, BufferAttribute, BufferGeometry, DataTexture, RGBAFormat, SRGBColorSpace } from 'three';
import solar from '../config/solarSystem.json';
import { sampleWorldClock } from './simulation.js';

const TAU = Math.PI * 2;
const RAD = Math.PI / 180;
const decodeColor = hex => [1,3,5].map(offset=>parseInt(hex.slice(offset,offset+2),16));
const blend = (first,second,amount) => first.map((value,index)=>Math.round(value+(second[index]-value)*amount));
const wave = (longitude,latitude,seed=0) => .5+.5*Math.sin(longitude*.113+Math.sin(latitude*.19+seed)*2.3+seed)*Math.cos(latitude*.177-longitude*.057);
const inside = (x,y,polygon) => {
  let found=false;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
    const [xi,yi]=polygon[i],[xj,yj]=polygon[j];
    if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi)found=!found;
  }
  return found;
};

function planetTexture(planet) {
  const width=solar.textureWidth,height=solar.textureHeight,data=new Uint8Array(width*height*4);
  const first=decodeColor(planet.colors[0]),second=decodeColor(planet.colors[1]);
  const land=decodeColor(solar.earthLandColor),desert=decodeColor(solar.earthDesertColor);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const longitude=x/(width-1)*360-180,latitude=y/(height-1)*180-90;
    const detail=wave(longitude,latitude,planet.orbitRatio*7);
    let color=blend(first,second,detail*.65+.15);
    if(planet.surface==='bands'){
      const stripe=.5+.5*Math.sin(latitude*.71+Math.sin(longitude*.05)*.7);
      color=blend(first,second,stripe*.7+detail*.3);
    }
    if(planet.surface==='earth'){
      if(solar.continents.some(polygon=>inside(longitude,latitude,polygon))){
        const arid=Math.max(0,1-Math.abs(Math.abs(latitude)-23)/16)*detail;
        color=blend(land,desert,arid);
        color=color.map(value=>Math.round(value*(.82+detail*.24)));
      }
      if(Math.abs(latitude)>76)color=blend(color,[232,242,240],Math.min(1,(Math.abs(latitude)-76)/8));
      // Soft clouds are painted over the illustrated surface, not wireframe.
      const clouds=wave(longitude*1.8,latitude*.85,17)*wave(longitude*.61,latitude*1.9,4);
      if(clouds>.46)color=blend(color,[246,248,247],Math.min(.65,(clouds-.46)*2));
    }
    data.set([...color,255],(y*width+x)*4);
  }
  const texture=new DataTexture(data,width,height,RGBAFormat);
  texture.colorSpace=SRGBColorSpace;texture.needsUpdate=true;
  return texture;
}

function glowTexture() {
  const size=64,data=new Uint8Array(size*size*4);
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const radius=Math.hypot((x+.5)/size*2-1,(y+.5)/size*2-1);
    const alpha=Math.max(0,1-radius)**3;
    data.set([255,255,255,Math.round(alpha*255)],(y*size+x)*4);
  }
  const texture=new DataTexture(data,size,size,RGBAFormat);texture.needsUpdate=true;
  return texture;
}

function orbitOffset(planet,angle,radius) {
  const x=Math.cos(angle)*radius,z=Math.sin(angle)*radius;
  const inclination=planet.inclinationDeg*RAD,node=planet.nodeDeg*RAD;
  const tiltedY=-z*Math.sin(inclination),tiltedZ=z*Math.cos(inclination);
  return [x*Math.cos(node)+tiltedZ*Math.sin(node),tiltedY,-x*Math.sin(node)+tiltedZ*Math.cos(node)];
}

function seededStars() {
  let seed=solar.starSeed>>>0;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const positions=new Float32Array(solar.starCount*3),colors=new Float32Array(solar.starCount*3);
  for(let i=0;i<solar.starCount;i++){
    const y=random()*2-1,angle=random()*TAU,radial=Math.sqrt(1-y*y),r=solar.starRadius;
    positions.set([radial*Math.cos(angle)*r,y*r,radial*Math.sin(angle)*r],i*3);
    const brightness=.4+random()*.55,temperature=random();
    colors.set(temperature<.15?[brightness*.76,brightness*.87,brightness]:temperature>.88?[brightness,brightness*.88,brightness*.71]:[brightness,brightness,brightness],i*3);
  }
  const geometry=new BufferGeometry();
  geometry.setAttribute('position',new BufferAttribute(positions,3));geometry.setAttribute('color',new BufferAttribute(colors,3));
  return geometry;
}

function StarField({texture}) {
  const group=useRef(null),geometry=useMemo(()=>seededStars(),[]);
  useEffect(()=>()=>geometry.dispose(),[geometry]);
  useFrame(({camera})=>group.current?.position.copy(camera.position));
  return <points ref={group} geometry={geometry} frustumCulled={false} renderOrder={-1}>
    <pointsMaterial map={texture} size={2.6} sizeAttenuation={false} transparent alphaTest={.025} vertexColors depthWrite={false} fog={false} toneMapped={false} blending={AdditiveBlending}/>
  </points>;
}

function Planet({planet,simulation,clockConfig,planetarium,glow}) {
  const root=useRef(null),body=useRef(null);
  const texture=useMemo(()=>planetTexture(planet),[planet]);
  const initial=sampleWorldClock(0,clockConfig),radius=initial.orbitRadius*planet.orbitRatio;
  const path=useMemo(()=>Array.from({length:193},(_,index)=>orbitOffset(planet,index/192*TAU,radius)),[planet,radius]);
  useEffect(()=>()=>texture.dispose(),[texture]);
  useFrame(()=>{
    const clock=sampleWorldClock(simulation.current.elapsed,clockConfig);
    const earthPeriod=clockConfig?.orbitPeriodSeconds>0?clockConfig.orbitPeriodSeconds:120;
    const dayPeriod=clockConfig?.dayPeriodSeconds>0?clockConfig.dayPeriodSeconds:240;
    const angle=planet.id==='earth'?clock.earthAngle:clock.elapsedSeconds/earthPeriod/planet.periodEarthYears*TAU+planet.phaseDeg*RAD;
    const position=orbitOffset(planet,angle,clock.orbitRadius*planet.orbitRatio);
    root.current?.position.set(position[0]+clock.sunCenter[0],position[1]+clock.sunCenter[1],position[2]+clock.sunCenter[2]);
    if(body.current)body.current.rotation.y=clock.elapsedSeconds/dayPeriod*TAU*planet.spinRatio;
  });
  const marker=solar.earthCityMarker,lat=marker.latitudeDeg*RAD,lon=marker.longitudeDeg*RAD;
  const markerPosition=[Math.cos(lon)*Math.cos(lat)*planet.radius*1.025,Math.sin(lat)*planet.radius*1.025,-Math.sin(lon)*Math.cos(lat)*planet.radius*1.025];
  return <>
    <group position={initial.sunCenter}><Line points={path} color={planet.orbitColor} lineWidth={planet.id==='earth'?1.2:.65} transparent opacity={planet.id==='earth'?.75:.47} fog={false} toneMapped={false}/></group>
    <group ref={root}>
      <group ref={body} rotation={[0,0,planet.id==='earth'?23.4*RAD:0]}>
        <mesh castShadow={false}>
          <sphereGeometry args={[planet.radius,48,32]}/><meshStandardMaterial map={texture} roughness={planet.surface==='earth'?.72:.88} emissiveMap={texture} emissive="#ffffff" emissiveIntensity={.055} fog={false}/>
        </mesh>
        {planet.id==='earth'&&<>
          <mesh position={markerPosition}><sphereGeometry args={[.047,12,8]}/><meshBasicMaterial color="#ffd571" toneMapped={false} fog={false}/></mesh>
          <mesh><sphereGeometry args={[planet.radius*1.025,48,32]}/><meshBasicMaterial color="#5aa8ff" transparent opacity={.055} depthWrite={false} fog={false}/></mesh>
        </>}
        {planet.rings&&<mesh rotation={[-Math.PI/2,.22,0]}><ringGeometry args={[planet.radius*planet.rings[0],planet.radius*planet.rings[1],96]}/><meshStandardMaterial color="#d6c098" transparent opacity={.55} roughness={.9} side={2} fog={false}/></mesh>}
      </group>
      <sprite scale={[planet.radius*5,planet.radius*5,1]}><spriteMaterial map={glow} color={planet.id==='earth'?'#7fcaff':planet.orbitColor} transparent opacity={.16} depthWrite={false} fog={false} toneMapped={false} blending={AdditiveBlending}/></sprite>
      {(planetarium||planet.id==='earth')&&<Html position={[0,planet.radius+1.25,0]} center zIndexRange={[1,0]} style={{pointerEvents:'none',whiteSpace:'nowrap',color:planet.id==='earth'?'#bce8ff':'#ddd6c9',fontSize:planet.id==='earth'?12:10,textShadow:'0 1px 8px #000'}}>{planet.label}</Html>}
    </group>
  </>;
}

export default function SolarSky({simulation,clockConfig,planetarium=false}) {
  const clock=sampleWorldClock(0,clockConfig),glow=useMemo(()=>glowTexture(),[]);
  const sun=useMemo(()=>planetTexture({colors:['#ff9b35','#fff2c2'],surface:'cloud',orbitRatio:2.3}),[]);
  useEffect(()=>()=>{glow.dispose();sun.dispose();},[glow,sun]);
  return <group name="PREP_SOLAR_SKY_EARTH_LOCAL">
    <StarField texture={glow}/>
    <group position={clock.sunCenter}>
      <mesh><sphereGeometry args={[solar.sunRadius,64,40]}/><meshBasicMaterial map={sun} color="#fff2ce" toneMapped={false} fog={false}/></mesh>
      <sprite scale={[solar.sunRadius*7,solar.sunRadius*7,1]}><spriteMaterial map={glow} color={solar.sunGlowColor} transparent opacity={.75} depthWrite={false} fog={false} toneMapped={false} blending={AdditiveBlending}/></sprite>
      <sprite scale={[solar.sunRadius*3.9,solar.sunRadius*3.9,1]}><spriteMaterial map={glow} color="#fff4d2" transparent opacity={.85} depthWrite={false} fog={false} toneMapped={false} blending={AdditiveBlending}/></sprite>
      <pointLight color="#fff1d6" intensity={1100} distance={95} decay={2}/>
      {planetarium&&<Html position={[0,-solar.sunRadius-2,0]} center zIndexRange={[1,0]} style={{pointerEvents:'none',color:'#ffd98b',fontSize:12,textShadow:'0 1px 8px #000'}}>SOL</Html>}
    </group>
    {solar.planets.map(planet=><Planet key={planet.id} planet={planet} simulation={simulation} clockConfig={clockConfig} planetarium={planetarium} glow={glow}/>)}
  </group>;
}
