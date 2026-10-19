import {AnimationClip} from 'three';

export function findAnimationClip(clips,name){
  const wanted=name?.toLowerCase();
  return clips.find(c=>c.name.toLowerCase()===wanted)||clips.find(c=>c.name.toLowerCase().endsWith(`|${wanted}`));
}
export function isCarryRotationTrack(track){
  if(!track.name.endsWith('.quaternion'))return false;
  const bone=track.name.slice(0,-'.quaternion'.length).replace(/[^a-z]/gi,'').toLowerCase();
  return bone.includes('upperarm')||bone.includes('forearm')||bone.includes('hand')
    || /(?:left|right)arm$/.test(bone);
}
// Arm poses come from the supplied Interact animation. Shared loader data is never
// mutated: every derived clip owns cloned tracks, while locomotion retains its legs.
export function createCarryAnimations(originals){
  const interaction=findAnimationClip(originals,'Interact');
  const upperTracks=interaction?.tracks.filter(isCarryRotationTrack)??[];
  if(!upperTracks.length)return {clips:originals,holdingNames:{},overlayName:null,overlayTime:0};
  const overlay=new AnimationClip('PREP_CarryOverlay',interaction.duration,upperTracks.map(t=>t.clone()));
  const holdingNames={},locomotion=[];
  for(const name of ['Idle','Walk']){
    const source=findAnimationClip(originals,name);
    if(!source)continue;
    const derived=new AnimationClip(`PREP_Holding_${name}`,source.duration,source.tracks.filter(t=>!isCarryRotationTrack(t)).map(t=>t.clone()));
    holdingNames[name]=derived.name;locomotion.push(derived);
  }
  return {clips:[...originals,...locomotion,overlay],holdingNames,overlayName:overlay.name,overlayTime:interaction.duration*.5};
}
