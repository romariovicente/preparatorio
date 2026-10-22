const fold=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const finitePoint=point=>Array.isArray(point)&&point.length===3&&point.every(Number.isFinite);
const asPoint=value=>Array.isArray(value)?value:[value?.x,value?.y??0,value?.z];
const seatedIds=new Set(['SUP_woman_seated_v15']);
const relaxedIds=new Set(['SUP_japanese_school_girl_v25','SUP_woman_standing_v33','SUP_woman_standing_v38__eko']);
const clipsOf=asset=>(asset.animations??asset.clips??[]).filter(name=>typeof name==='string');
const hasClip=(asset,name)=>clipsOf(asset).some(clip=>fold(clip)===fold(name));
const displayNames={
  CHR_Remy_Mixamo_20261005:'Remy',
  SUP_character_cyberpunk_free_3d_by_oscar_cre:'Personagem cyberpunk',
  SUP_lowpoly_anime_character_cyberstyle:'Personagem anime · CyberStyle',
  SUP_corrupted_fallen_priest___dar:'Sacerdote · fantasia',
  SUP_dark_necromancer___corrupted_staff__:'Necromante · fantasia',
  SUP_desert_nomad_assassin___dark_fantasy:'Nômade do deserto · fantasia',
  SUP_jumpsuit_low_poly:'Macacão futurista',
  SUP_Stylized_Female_Futuristic_Pilot___Ferra:'Pilota futurista · Ferra',
};

export function characterRosterCategory(asset){
  return ['personagens','personagem','character','characters'].includes(fold(asset?.category??asset?.sourceCategory));
}

// Style is a sorting preference, never a filter. Every available character can
// be chosen by the player, while the control mode still states honestly whether
// the model has validated, preliminary or no locomotion animation.
export function buildCharacterRoster(assets,originals=[],reviews=[]){
  const originalById=new Map(originals.map(asset=>[asset.id,asset]));
  const reviewById=new Map(reviews.map(review=>[review.id,review]));
  const seen=new Set(),roster=[];
  for(const asset of assets){
    if(!asset?.id||seen.has(asset.id)||!characterRosterCategory(asset))continue;
    seen.add(asset.id);
    const original=originalById.get(asset.id),review=reviewById.get(asset.id);
    const trusted=review?.sha256===asset.sha256&&review.poseReviewed===true;
    const native=trusted&&review.controlMode==='native'&&review.locomotionValidated===true&&
      asset.rigged===true&&asset.needsRepose!==true&&hasClip(asset,review.idleClip)&&hasClip(asset,review.walkClip);
    const fixed=trusted&&review.controlMode==='fixed-pose'&&Boolean(review.standingPose?.clip)&&hasClip(asset,review.standingPose.clip);
    const available=typeof asset.url==='string'&&asset.url.length>0;
    const prototype=available&&asset.quality==='prototype'&&asset.reimportValidated===true&&asset.rigged===true;
    const prototypeWalk=prototype&&asset.needsRepose!==true&&hasClip(asset,'Idle')&&hasClip(asset,'Walk');
    const controllable=available;
    const pose=seatedIds.has(asset.id)?'seated':relaxedIds.has(asset.id)?'authored-relaxed':asset.needsRepose?'authored-review':'standing';
    const staticSource=asset.needsRepose&&original?.url?original:asset;
    const displayUrl=native||fixed||prototypeWalk?asset.url:staticSource.url;
    const name=displayNames[asset.id]??asset.name??asset.label??asset.id;
    const controlMode=!controllable?'unavailable':native?'native':prototypeWalk?'prototype-motion':fixed?'fixed-pose':'static-pose';
    const reasons=[];
    if(!available)reasons.push('Arquivo indisponível nesta distribuição.');
    if(asset.needsRepose)reasons.push('Pose de origem preservada; exige nova pose/retopologia antes de caminhar.');
    if(prototypeWalk)reasons.push('Rig FK preliminar com Idle e Walk; postura vertical corrigida durante o movimento.');
    else if(asset.quality==='prototype')reasons.push('Rig FK de protótipo preservado somente para pose e ações seguras.');
    if(!trusted)reasons.push('Sem revisão de postura e locomoção vinculada ao hash atual.');
    if(fixed)reasons.push('Deslocamento em pose fixa; não contém caminhada validada.');
    if(native)reasons.push('Idle e caminhada nativos verificados neste arquivo.');
    const standingPose=trusted?review.standingPose:prototype&&asset.needsRepose!==true&&hasClip(asset,'Idle')?{clip:'Idle',time:0}:null;
    const playerStandingPose=native||prototypeWalk?null:prototype&&hasClip(asset,'Idle')?{clip:'Idle',time:0}:standingPose;
    const actionClips=native?(review.allowedActions??[]):prototypeWalk?clipsOf(asset):[];
    const playerAsset=controllable?{...asset,name,characterControlMode:controlMode,characterStandingPose:playerStandingPose,
      allowedCharacterActions:actionClips,idleClip:review?.idleClip??(hasClip(asset,'Idle')?'Idle':null),walkClip:review?.walkClip??(prototypeWalk?'Walk':null),
      characterCapabilities:{animatedLocomotion:Boolean(native||prototypeWalk),sitting:asset.id==='CHR_Remy_Mixamo_20261005',riding:asset.id==='CHR_Remy_Mixamo_20261005',driving:true},
      rigged:asset.rigged===true||Boolean(asset.originalRig),playable:true,reimportValidated:true,
      visualStyle:review?.visualStyle??asset.visualStyle,characterControlLabel:native?'animações nativas':prototypeWalk?'caminhada preliminar com correção de postura':'pose original · sem passos'}:null;
    roster.push({id:asset.id,name,asset,playerAsset,controlMode,controllable,locomotionValidated:Boolean(native),
      walkingAnimationAvailable:Boolean(native||prototypeWalk),patientEligible:Boolean(native),
      // Every playable/resident wrapper uses the same adult reference height as
      // Remy. The authored pose can be seated or relaxed without shrinking the
      // body itself; pose height and character height are separate concerns.
      pose,height:1.7,
      figures:Math.max(1,Number(asset.figures)||1),available:Boolean(displayUrl),displayUrl,
      displayBytes:staticSource.bytes??asset.bytes??0,standingPose,reviewReport:trusted?review.report:null,
      visualStyle:review?.visualStyle??asset.visualStyle??'authored',reasons,
      statusLabel:native?'Escolher · caminhada validada':prototypeWalk?'Escolher · caminhada preliminar':'Escolher · pose original',
      context:pose==='seated'?'Leitura e descanso':pose==='authored-relaxed'||pose==='authored-review'?'Exposição cultural':'Praça e acolhimento',
    });
  }
  // Keep placement order tied to source metadata. Translating a visible label
  // must not move an existing resident to another Blender/runtime position.
  return roster.sort((a,b)=>Number(b.visualStyle==='realistic')-Number(a.visualStyle==='realistic')||Number(b.controllable)-Number(a.controllable)||String(a.asset.name??a.asset.label??a.id).localeCompare(String(b.asset.name??b.asset.label??b.id),'pt-BR')||a.id.localeCompare(b.id));
}

export function characterSelectionOptions(roster){
  return roster.map(entry=>({id:entry.id,label:`${entry.name}${entry.controlMode==='prototype-motion'?' · caminhada preliminar':entry.walkingAnimationAvailable?'':' · pose original'}`,disabled:!entry.controllable,
    controlMode:entry.controlMode,reason:entry.walkingAnimationAvailable?'Disponível para jogar com animação de caminhada.':'Disponível para jogar na pose original.',asset:entry.playerAsset}));
}

export function hospitalPatientCharacters(roster,limit=2){
  return roster.filter(entry=>entry.patientEligible&&entry.playerAsset?.walkClip&&entry.playerAsset?.idleClip).slice(0,Math.max(0,limit));
}

export function resolveRosterCharacter(roster,id){
  return roster.find(entry=>entry.id===id&&entry.controllable)?.playerAsset??null;
}

function blocked(point,colliders,radius){
  return colliders.some(box=>Number.isFinite(box?.x)&&Number.isFinite(box?.z)&&box.w>0&&box.d>0&&
    Math.abs(point[0]-box.x)<box.w/2+radius&&Math.abs(point[2]-box.z)<box.d/2+radius);
}

export function createCharacterRosterPlacements(roster,{anchors=[],colliders=[],bounds={minX:-118,maxX:118,minZ:-118,maxZ:118},spacing=3.8,radius=.65}={}){
  const candidates=anchors.filter(finitePoint).map(position=>[...position]);
  // The plaza ring is outside the central monument. Extra candidates and the
  // collider check keep a newly added model from replacing an existing actor.
  const ringCount=Math.max(20,roster.length);
  for(const ring of [25,29,32])for(let index=0;index<ringCount;index++){
    const angle=index/ringCount*Math.PI*2;candidates.push([Math.cos(angle)*ring,0,Math.sin(angle)*ring]);
  }
  for(let z=-105;z<=105;z+=10)for(let x=-105;x<=105;x+=10)if(Math.hypot(x,z)>24)candidates.push([x,0,z]);
  const used=[],unplaced=[];
  const placements=roster.map(entry=>{
    const position=candidates.find(point=>point[0]-radius>=bounds.minX&&point[0]+radius<=bounds.maxX&&
      point[2]-radius>=bounds.minZ&&point[2]+radius<=bounds.maxZ&&!blocked(point,colliders,radius)&&
      used.every(other=>Math.hypot(point[0]-other[0],point[2]-other[2])>=spacing));
    if(position)used.push(position);else unplaced.push(entry.id);
    return {...entry,position:position?[...position]:null,heading:position?Math.atan2(-position[0],-position[2]):0,
      actorId:`roster:${entry.id}`,staticNpc:!entry.walkingAnimationAvailable,autonomousNpc:Boolean(entry.walkingAnimationAvailable)};
  });
  return {placements,unplaced,allRepresented:unplaced.length===0};
}

export function characterRosterColliders(placements){
  return placements.filter(entry=>finitePoint(entry.position)).map(entry=>({id:entry.actorId,x:entry.position[0],z:entry.position[2],w:entry.figures>1?1.6:1.05,d:entry.pose==='seated'?1.2:.85}));
}

export function nearbyCharacterPlacements(placements,observer,{distance=18,maxVisible=4,maxBytes=140*1024*1024}={}){
  const position=asPoint(observer);if(!finitePoint(position))return [];
  const nearby=placements.filter(entry=>finitePoint(entry.position)&&entry.available)
    .map(entry=>({...entry,distance:Math.hypot(position[0]-entry.position[0],position[2]-entry.position[2])}))
    .filter(entry=>entry.distance<=distance).sort((a,b)=>a.distance-b.distance||a.id.localeCompare(b.id));
  let bytes=0;const visible=[];
  for(const entry of nearby){
    if(visible.length>=maxVisible)break;
    const size=Math.max(0,entry.displayBytes??0);if(bytes+size>maxBytes)continue;
    bytes+=size;visible.push(entry);
  }
  return visible;
}
