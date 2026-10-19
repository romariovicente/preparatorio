import {useCallback,useEffect,useRef,useState} from 'react';
import {useFrame} from '@react-three/fiber';
import {createGameAudio} from './audioSystem.js';

const volumeKey='prep.audio.volume.v1',mutedKey='prep.audio.muted.v1';
function initialSettings(){
  try{
    const saved=globalThis.localStorage?.getItem(volumeKey),number=saved==null ? .55 : Number(saved);
    return {volume:Number.isFinite(number)?Math.max(0,Math.min(1,number)):.55,muted:globalThis.localStorage?.getItem(mutedKey)==='true'};
  }catch{return {volume:.55,muted:false};}
}
function initialStatus(settings){return {supported:typeof(globalThis.AudioContext??globalThis.webkitAudioContext)==='function',unlocked:false,
  ...settings,activeVoices:0,loops:[],lastSound:null,disposed:false};}

// The hook and frame component intentionally share one integration module.
// eslint-disable-next-line react-refresh/only-export-components
export function useGameAudio(){
  const [settings,setSettings]=useState(initialSettings),settingsRef=useRef(settings);
  const [status,setStatus]=useState(()=>initialStatus(settings));
  const audioRef=useRef(null),unlockingRef=useRef(null),lastStatusAt=useRef(-Infinity);
  const syncStatus=useCallback((force=false)=>{
    const audio=audioRef.current;if(!audio)return;
    const at=globalThis.performance?.now?.()??Date.now();
    if(!force&&at-lastStatusAt.current<250)return;
    lastStatusAt.current=at;
    const next=audio.getStatus();
    setStatus(previous=>previous.unlocked===next.unlocked&&previous.supported===next.supported&&previous.muted===next.muted&&
      previous.volume===next.volume&&previous.lastSound===next.lastSound&&previous.activeVoices===next.activeVoices&&
      previous.disposed===next.disposed&&previous.loops.join('|')===next.loops.join('|')?previous:next);
  },[]);
  const unlock=useCallback(()=>{
    const audio=audioRef.current;if(!audio)return Promise.resolve(false);
    if(unlockingRef.current)return unlockingRef.current;
    const pending=audio.unlock().then(result=>{if(audioRef.current===audio)syncStatus(true);return result;})
      .finally(()=>{if(unlockingRef.current===pending)unlockingRef.current=null;});
    unlockingRef.current=pending;return pending;
  },[syncStatus]);
  useEffect(()=>{
    const audio=createGameAudio();audio.setVolume(settingsRef.current.volume);audio.setMuted(settingsRef.current.muted);
    audioRef.current=audio;
    const onGesture=event=>{if(event.repeat||audio.getStatus().unlocked||!audio.getStatus().supported)return;void unlock();};
    const target=globalThis.document;
    target?.addEventListener('pointerdown',onGesture,{capture:true,passive:true});
    target?.addEventListener('keydown',onGesture,{capture:true});
    return()=>{
      target?.removeEventListener('pointerdown',onGesture,true);target?.removeEventListener('keydown',onGesture,true);
      if(audioRef.current===audio){audioRef.current=null;unlockingRef.current=null;}
      audio.dispose();
    };
  },[unlock]);
  const saveSettings=useCallback(next=>{
    settingsRef.current=next;setSettings(next);
    try{globalThis.localStorage?.setItem(volumeKey,String(next.volume));globalThis.localStorage?.setItem(mutedKey,String(next.muted));}catch{/* preferences remain active for this session */}
    syncStatus(true);
  },[syncStatus]);
  const setVolume=useCallback(value=>{
    const parsed=Number(value),volume=Number.isFinite(parsed)?Math.max(0,Math.min(1,parsed)):settingsRef.current.volume;
    audioRef.current?.setVolume(volume);saveSettings({...settingsRef.current,volume});return volume;
  },[saveSettings]);
  const toggleMute=useCallback(()=>{
    const muted=!settingsRef.current.muted;audioRef.current?.setMuted(muted);saveSettings({...settingsRef.current,muted});return muted;
  },[saveSettings]);
  const play=useCallback((type,detail={})=>{
    const audio=audioRef.current;if(!audio)return false;
    if(audio.getStatus().unlocked){const result=audio.play(type,detail);syncStatus();return result;}
    // A capture-phase user gesture may still be resuming the audio context when
    // React handles that same key or click. Keep that first cue, but never create
    // or unlock a context from an unprompted game action.
    if(unlockingRef.current){void unlockingRef.current.then(ok=>{if(ok&&audioRef.current===audio){audio.play(type,detail);syncStatus();}});return true;}
    return false;
  },[syncStatus]);
  return {audioRef,status,volume:settings.volume,muted:settings.muted,unlock,setVolume,toggleMute,play,syncStatus};
}

// Mount inside Canvas. It follows the game's existing frame loop and has no
// requestAnimationFrame, timer, or background polling of its own.
export function GameAudioLoop({audioRef,simulation,doors={},onStatus}){
  const elapsed=useRef(0);
  useFrame((_,delta)=>{
    audioRef.current?.update(simulation.current,delta,doors);
    elapsed.current+=delta;
    if(elapsed.current>=1){elapsed.current%=1;onStatus?.();}
  });
  return null;
}
