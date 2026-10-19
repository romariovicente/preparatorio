export const PLAYER_NAME_KEY='prep.user.name.v1';
export const DEFAULT_PLAYER_NAME='Jogador';
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
  const colors=['#247fba','#37664b','#783874','#c85e26'];
  return {scrubs:value?.scrubs!==false,coat:Boolean(value?.coat),color:colors.includes(value?.color)?value.color:'#247fba'};
}
