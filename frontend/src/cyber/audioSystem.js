import buildings from '../config/buildingDoors.json' with {type:'json'};

// Original procedural cues: no downloaded samples or third-party recordings.
const ACTIONS=Object.freeze({MOVE:'object-move',JUMP:'jump',JUMP_LAND:'landing',LAND:'landing',
  CAR_ENTER:'door',CAR_EXIT:'door',CAR_DOOR:'door',DOOR:'door',CAR_WINDOWS:'window',CAR_ENGINE:'engine',
  MOTO_ENTER:'vehicle-enter',MOTO_EXIT:'vehicle-exit',MOTO_ENGINE:'engine',SUMMON_VEHICLE:'phone',STORE_VEHICLE:'engine-off',
  BUS_TAKE_WHEEL:'vehicle-enter',BUS_RELEASE_WHEEL:'vehicle-exit',BUS_ENGINE:'engine',BUS_STOP:'engine-off',
  ENGINE_ON:'engine-on',ENGINE_OFF:'engine-off',DRIVE:'vehicle-enter',TRACTOR:'vehicle-enter',BOARD:'vehicle-enter',
  EXIT:'vehicle-exit',PARK:'engine-off',TRAILER:'latch',TELEPORT:'teleport',PICKUP:'pickup',DROP:'drop',
  USE:'use',INTERACT:'use',RETURN:'return',INSPECT:'menu',FLOWER:'flower',DANCE:'dance',
  PLANT:'plant',HARVEST:'harvest',SEEDS:'seeds',CAST:'cast',REEL:'reel',ELEVATOR:'elevator',
  OUTFIT:'cloth',SIT:'cloth',STAND:'cloth',PHONE:'phone',MENU:'menu',JARVIS_ASK:'ask',JARVIS_REPLY:'reply'});
export function actionSound(action){return ACTIONS[typeof action==='string'?action.toUpperCase():action?.type]??null;}
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
const point=state=>state?.position&&[state.position.x,state.position.z].every(Number.isFinite)?state.position:null;

export function createGameAudio(options={}){
  const Ctor=Object.hasOwn(options,'AudioContextCtor')?options.AudioContextCtor:globalThis.AudioContext??globalThis.webkitAudioContext;
  let context=null,master=null,limiter=null,noiseBuffer=null,unlocked=false,disposed=false,volume=.55,muted=false;
  let previousPosition=null,stepDistance=0,time=0,beatTime=0,beat=0,natureTime=0,random=0x53b917;
  let previousJump=false,previousEngine='',previousElevator=false,lastSound=null;
  const voices=new Set(),loops=new Map(),doorState=new Map(),recent=new Map();
  const ready=()=>unlocked&&!disposed&&context?.state==='running';
  const now=()=>context?.currentTime??0;
  function rng(){random^=random<<13;random^=random>>>17;random^=random<<5;return (random>>>0)/4294967296;}
  function parameter(param,value){param.cancelScheduledValues(now());param.setTargetAtTime(value,now(),.06);}
  function stopVoice(voice){
    if(!voice||!voices.has(voice))return;
    voices.delete(voice);if(voice.key&&loops.get(voice.key)===voice)loops.delete(voice.key);
    voice.source.onended=null;
    try{voice.source.stop();}catch{/* already ended */}
    for(const node of voice.nodes)try{node.disconnect();}catch{/* already detached */}
  }
  function stopLoop(key){stopVoice(loops.get(key));}
  function reserve(){
    if(voices.size>=32){const old=[...voices].find(v=>!v.key);if(!old)return false;stopVoice(old);}
    return true;
  }
  function sourceVoice({noise=false,frequency=200,endFrequency=frequency,duration=.15,level=.05,type='sine',cutoff=1400,filterType='lowpass',delay=0,key=null,pan=0}){
    if(!ready()||muted||!reserve())return null;
    const at=now()+delay,source=noise?context.createBufferSource():context.createOscillator();
    const gain=context.createGain(),filter=context.createBiquadFilter(),nodes=[source,filter,gain];
    if(noise){source.buffer=noiseBuffer;source.loop=Boolean(key);}else{source.type=type;source.frequency.setValueAtTime(frequency,at);if(!key)source.frequency.linearRampToValueAtTime(Math.max(15,endFrequency),at+duration);}
    filter.type=filterType;filter.frequency.setValueAtTime(cutoff,at);filter.Q.setValueAtTime(.55,at);
    source.connect(filter);filter.connect(gain);
    if(context.createStereoPanner){const panner=context.createStereoPanner();panner.pan.setValueAtTime(pan,at);gain.connect(panner);panner.connect(master);nodes.push(panner);}else gain.connect(master);
    gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(level,at+Math.min(.02,duration/4));
    if(!key)gain.gain.linearRampToValueAtTime(0,at+duration);
    const voice={source,gain,filter,nodes,key,level};voices.add(voice);if(key)loops.set(key,voice);
    source.onended=()=>{if(voices.has(voice)){voices.delete(voice);if(key&&loops.get(key)===voice)loops.delete(key);for(const node of nodes)node.disconnect();}};
    source.start(at);if(!key)source.stop(at+duration+.025);return voice;
  }
  const tone=(f,end,duration,level=.045,delay=0,type='sine')=>sourceVoice({frequency:f,endFrequency:end,duration,level,delay,type,cutoff:Math.max(f,end)*3});
  const noise=(duration,level=.035,cutoff=700,delay=0,filterType='lowpass')=>sourceVoice({noise:true,duration,level,cutoff,delay,filterType});
  function loop(key,spec){if(!loops.has(key))sourceVoice({...spec,key});return loops.get(key);}
  function cue(kind,detail={}){
    if(!ready()||muted)return false;
    if(now()-(recent.get(kind)??-Infinity)<.075)return false;
    recent.set(kind,now());lastSound=kind;
    switch(kind){
      case 'step':noise(.075,.055,detail.running?900:580);tone(92,48,.085,.04);break;
      case 'jump':noise(.17,.035,1100);tone(160,245,.14,.035);break;
      case 'landing':noise(.13,.085,400);tone(75,30,.14,.065);break;
      case 'engine-on':noise(.34,.055,220);tone(55,130,.44,.045,0,'sawtooth');break;
      case 'engine-off':tone(95,27,.24,.04,0,'triangle');break;
      case 'door':noise(.62,.032,480);tone(380,120,.11,.035,.56,'triangle');break;
      case 'window':noise(.72,.025,460);tone(detail.open===false?310:220,detail.open===false?220:310,.65,.012);break;
      case 'vehicle-enter':case 'vehicle-exit':case 'latch':noise(.10,.04,520);tone(280,120,.09,.025);break;
      case 'teleport':tone(280,1200,.45,.048,0,'triangle');tone(660,880,.22,.025,.15);noise(.32,.02,2300);break;
      case 'pickup':case 'flower':case 'return':noise(.10,.025,1200);tone(430,kind==='return'?330:540,.12,.028);break;
      case 'drop':noise(.13,.055,320);tone(110,50,.11,.035);break;
      case 'object-move':noise(.26,.025,600);break;
      case 'cloth':case 'plant':case 'seeds':noise(.15,.027,1250);break;
      case 'harvest':noise(.16,.04,1100);tone(350,500,.12,.026);tone(660,660,.12,.023,.1);break;
      case 'cast':noise(.23,.025,1900);tone(620,190,.17,.017);break;
      case 'reel':noise(.35,.023,800);tone(180,270,.32,.02,0,'triangle');break;
      case 'elevator':tone(500,500,.18,.03);break;
      case 'elevator-stop':tone(740,740,.25,.035);tone(988,988,.3,.025,.16);break;
      case 'ask':tone(440,660,.1,.025);break;
      case 'reply':tone(660,660,.13,.028);tone(880,880,.2,.025,.12);break;
      case 'phone':case 'menu':tone(530,kind==='phone'?750:530,.075,.018);break;
      case 'dance':tone(110,55,.12,.055);break;
      case 'use':tone(420,420,.1,.025);tone(630,630,.12,.02,.08);break;
      default:return false;
    }return true;
  }
  async function unlock(){
    if(disposed||typeof Ctor!=='function')return false;
    try{
      if(!context){
        context=new Ctor();master=context.createGain();master.gain.setValueAtTime(muted?0:volume,now());
        if(context.createDynamicsCompressor){limiter=context.createDynamicsCompressor();limiter.threshold.setValueAtTime(-14,now());limiter.ratio.setValueAtTime(8,now());master.connect(limiter);limiter.connect(context.destination);}else master.connect(context.destination);
        noiseBuffer=context.createBuffer(1,context.sampleRate*2,context.sampleRate);const samples=noiseBuffer.getChannelData(0);
        for(let i=0;i<samples.length;i++)samples[i]=(rng()*2-1)*.55;
      }
      await context.resume();unlocked=context.state==='running';return unlocked;
    }catch{unlocked=false;return false;}
  }
  function setVolume(value){if(Number.isFinite(value))volume=clamp(value,0,1);if(master&&!disposed)master.gain.setValueAtTime(muted?0:volume,now());return volume;}
  function setMuted(value){muted=Boolean(value);if(master&&!disposed)master.gain.setValueAtTime(muted?0:volume,now());if(muted)for(const voice of [...voices])stopVoice(voice);return muted;}
  function play(actionType,detail={}){
    let kind=actionSound(actionType);if(!kind)return false;
    if(kind==='engine')kind=(detail.engineOn??!previousEngine)?'engine-on':'engine-off';
    return cue(kind,detail);
  }
  function update(state,delta,doors={}){
    if(disposed||!state)return false;
    const p=point(state),dt=Number.isFinite(delta)?clamp(delta,0,.5):0;
    const distance=p&&previousPosition?Math.hypot(p.x-previousPosition.x,p.z-previousPosition.z):0;
    if(p)previousPosition={...p};
    if(!ready())return false;
    time+=dt;
    const jump=Boolean(state.jump)||Number(state.jumpHeight)>0,engine=state.mode==='car'?(state.carControls?.engineOn&&!state.carControls?.doorOpen?'car':''):state.mode==='mototaxi'?(state.motorcycleControls?.engineOn?'mototaxi':''):['bus','bus-brt'].includes(state.mode)?state.liveBuses?.[state.mode]?.engineOn?'bus':'':['truck','tractor','harvester','train'].includes(state.mode)?state.mode:'';
    if(jump&&!previousJump)cue('jump');if(!jump&&previousJump)cue('landing');previousJump=jump;
    if(engine!==previousEngine){if(previousEngine)cue('engine-off');if(engine)cue('engine-on');previousEngine=engine;}
    const elevator=Boolean(state.elevator);if(elevator&&!previousElevator)cue('elevator');if(!elevator&&previousElevator)cue('elevator-stop');previousElevator=elevator;
    for(const [id,door]of Object.entries(doors??{})){
      const old=doorState.get(id),building=buildings.find(b=>b.id===id);
      if(old&&door.revision!==old.revision&&door.open!==old.open&&building&&p&&Math.hypot(p.x-building.center[0],p.z-building.center[2]-building.depth/2)<=12)cue('door');
      doorState.set(id,{revision:door.revision,open:door.open});
    }
    const wanted=new Set(),indoor=Boolean(state.environment?.indoor),night=Boolean(state.environment?.night??state.night??state.clock?.night);
    function want(key,spec,gainLevel=spec.level){wanted.add(key);const voice=loop(key,spec);if(voice)parameter(voice.gain.gain,gainLevel);return voice;}
    if(!muted){
      if(indoor)want('room',{frequency:85,level:.01,cutoff:230,type:'sine'});
      else{
        want('wind',{noise:true,level:.012,cutoff:550},.01+.004*Math.sin(time*.3)**2);
        want('traffic',{noise:true,level:.009,cutoff:150});
        if(night)want('insects',{noise:true,level:.005,cutoff:4300,filterType:'bandpass'});
        if(p&&p.x>=85)want('ocean',{noise:true,level:.025,cutoff:650},(.015+.025*Math.sin(time*.42)**2)*clamp((p.x-85)/15,0,1));
      }
      if(engine){
        const speed=distance>6||dt===0?0:Math.min(22,distance/dt),base={car:55,truck:38,mototaxi:92,tractor:32,harvester:30,bus:42,train:60}[engine];
        const voice=want('engine',{frequency:base,level:.055,type:engine==='train'?'triangle':'sawtooth',cutoff:engine==='mototaxi'?650:400});
        if(voice)parameter(voice.source.frequency,base*(1+speed*.075));
      }
      if(elevator)want('elevator',{frequency:72,level:.028,type:'triangle',cutoff:200});
      if(state.mode==='foot'&&!state.sitting&&!elevator&&!jump&&distance>0&&distance<=6){
        const running=dt>0&&distance/dt>6.5;stepDistance+=distance;
        if(stepDistance>=(running?.85:.62)){stepDistance%=running?.85:.62;cue('step',{running});}
      }else if(distance>6||state.mode!=='foot'||state.sitting||jump)stepDistance=0;
      if(state.action==='Dance'&&state.mode==='foot'&&!state.sitting){
        beatTime+=dt;if(beatTime>=.45){beatTime%=.45;tone(75,32,.13,.06);noise(.04,.012,5000,0,'highpass');if(beat++%2)noise(.1,.025,1700,0,'bandpass');}
      }else{beatTime=0;beat=0;}
      natureTime+=dt;if(natureTime>=6.5){natureTime%=6.5;if(!indoor&&!night){sourceVoice({frequency:1950,endFrequency:2500,duration:.12,level:.01,pan:rng()*1.4-.7,cutoff:5000});tone(2650,2300,.13,.009,.17);}}
    }
    for(const key of [...loops.keys()])if(!wanted.has(key))stopLoop(key);
    return true;
  }
  function dispose(){
    if(disposed)return;disposed=true;unlocked=false;for(const voice of [...voices])stopVoice(voice);
    master?.disconnect();limiter?.disconnect();noiseBuffer=null;doorState.clear();recent.clear();
    try{const closing=context?.close();closing?.catch?.(()=>{});}catch{/* context already closed */}
  }
  function getStatus(){return {supported:typeof Ctor==='function',unlocked,muted,volume,activeVoices:voices.size,loops:[...loops.keys()],lastSound,disposed};}
  return {unlock,setVolume,setMuted,play,update,dispose,getStatus};
}
