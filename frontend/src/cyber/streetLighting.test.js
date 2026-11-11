import test from 'node:test';
import assert from 'node:assert/strict';
import {Group,Mesh,Vector3} from 'three';
import {collectStreetLampSites,selectStreetLampSites,STREET_LIGHT_LIMIT} from './streetLighting.js';

test('places light under a visible lamp head using its world position',()=>{
  const model=new Group(),street=new Group(),lampHead=new Mesh(),pole=new Mesh(),hiddenHead=new Mesh();
  street.position.set(10,1,-20);
  model.add(street);
  lampHead.name='LAMP_EAST_WEST_Beam_110';
  lampHead.position.set(4,7,46.3);
  pole.name='LAMP_EAST_WEST_110';
  hiddenHead.name='LAMP_EAST_WEST_Beam_140';
  hiddenHead.visible=false;
  street.add(lampHead,pole,hiddenHead);

  const sites=collectStreetLampSites(model);
  assert.equal(sites.length,1);
  assert.ok(sites[0].distanceTo(new Vector3(14,7.85,26.3))<1e-9);
});

test('keeps only the nearest street lights within the pool and sampling radius',()=>{
  const position={x:100,y:1,z:50};
  const sites=[42,8,25,12,4,6,11,3,2].map(offset=>new Vector3(position.x+offset,7,position.z));

  assert.equal(selectStreetLampSites(sites,position).length,STREET_LIGHT_LIMIT);
  assert.deepEqual(selectStreetLampSites(sites,position).map(site=>site.x-position.x),[2,3,4,6,8,11]);
  assert.deepEqual(selectStreetLampSites(sites.slice(0,1),position),[]);
});
