const directions={ArrowUp:'w',ArrowDown:'s',ArrowLeft:'a',ArrowRight:'d',w:'w',s:'s',a:'a',d:'d',Shift:'shift'};
export function directionKey(key){return directions[key]??directions[String(key).toLowerCase()]??null;}
export function textEntryTarget(target){return Boolean(target?.closest?.('input,textarea,select,[contenteditable="true"]'));}
export function setDirectionKey(held,key,pressed){
  const direction=directionKey(key);if(!direction)return null;
  const physical=key.length===1?key.toLowerCase():key;
  if(pressed)held.add(physical);else held.delete(physical);
  return {direction,pressed:[...held].some(item=>directionKey(item)===direction)};
}
