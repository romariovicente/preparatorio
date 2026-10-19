import {useCallback,useEffect,useRef,useState} from 'react';
import {createInteractionState} from '../world/interactionState.js';
import {interactionRooms} from './roomConfig.js';
import {createSharedTransport} from './sharedTransport.js';

export function useSharedObjects(room) {
  const [state,setState]=useState(()=>createInteractionState(interactionRooms[room].templates));
  const [actorId,setActorId]=useState(null),[status,setStatus]=useState('connecting'),[message,setMessage]=useState('');
  const transport=useRef(null),revision=useRef(-1),identity=useRef(null);
  useEffect(()=>{
    let alive=true;
    revision.current=-1;
    const connection=createSharedTransport({
      onSnapshot(data){
        if(!alive)return;
        if(data.actorId && data.actorId!==identity.current){identity.current=data.actorId;revision.current=-1;setActorId(data.actorId);}
        if(data.revision>=revision.current){revision.current=data.revision;setState(data.state);}
      },
      onStatus(next,id){if(alive){setStatus(next);if(id){if(next==='connected' && id!==identity.current){identity.current=id;revision.current=-1;}setActorId(id);}}},
    });
    transport.current=connection;connection.connect(room);
    return ()=>{alive=false;connection.close();};
  },[room]);
  const dispatch=useCallback(async command=>{
    if(status !== 'connected')return {ok:false,message:'Inicie o servidor local para compartilhar as interações.'};
    const result=await transport.current.action(command);setMessage(result.message ?? '');return result;
  },[status]);
  const publishPosition=useCallback((position,extra)=>transport.current?.publishPosition(position,extra),[]);
  const door=useCallback((id,open)=>transport.current?.door(id,open),[]);
  return {state,actorId,status,message,dispatch,publishPosition,door};
}
