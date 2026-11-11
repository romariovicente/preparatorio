import {Vector3} from 'three';

export const STREET_LIGHT_LIMIT=6;
export const STREET_LIGHT_DISTANCE=26;
const SELECTION_RADIUS=STREET_LIGHT_DISTANCE+10;
const LAMP_HEAD=/^LAMP_.+_Beam_\d+(?:[._]\d+)?$/i;

export function collectStreetLampSites(model) {
  const sites=[];
  model.updateWorldMatrix(true,true);
  model.traverseVisible(object=>{
    if(!object.isMesh||!LAMP_HEAD.test(object.name))return;
    const site=object.getWorldPosition(new Vector3());
    site.y-=.15;
    sites.push(site);
  });
  return sites;
}

export function selectStreetLampSites(sites,position) {
  return sites
    .map(site=>({site,distanceSquared:(site.x-position.x)**2+(site.z-position.z)**2}))
    .filter(({distanceSquared})=>distanceSquared<=SELECTION_RADIUS**2)
    .sort((a,b)=>a.distanceSquared-b.distanceSquared)
    .slice(0,STREET_LIGHT_LIMIT)
    .map(({site})=>site);
}
