export const PLAYER_NAME_KEY='prep.user.name.v1';
export const DEFAULT_PLAYER_NAME='Jogador';
export const HOSPITAL_SCRUB_COLOR='#ffffff';
export function normalizePlayerName(value){
  if(typeof value!=='string')return DEFAULT_PLAYER_NAME;
  const text=value.normalize('NFKC').replace(/[\p{Cc}\p{Cf}<>]/gu,'').replace(/\s+/gu,' ').trim();
  return Array.from(text).slice(0,48).join('')||DEFAULT_PLAYER_NAME;
}
export function readPlayerName(storage){
  try{return normalizePlayerName(storage?.getItem(PLAYER_NAME_KEY));}catch{return DEFAULT_PLAYER_NAME;}
}
export function savePlayerName(storage,value){
  const name=normalizePlayerName(value);
  try{storage?.setItem(PLAYER_NAME_KEY,name);}catch{/* The current player's name still works in memory. */}
  return name;
}
export function normalizePlayerOutfit(value){
  // The clinical uniform is intentionally white. Normalizing here also
  // migrates colors sent by older clients before multiplayer state is shared.
  return {scrubs:value?.scrubs!==false,coat:Boolean(value?.coat),color:HOSPITAL_SCRUB_COLOR};
}
