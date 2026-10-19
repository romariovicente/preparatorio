import test from 'node:test';
import assert from 'node:assert/strict';
import {createElement} from 'react';
import {renderToString} from 'react-dom/server';
import CityAssetBoundary from './CityAssetBoundary.js';

test('a pending optional model does not hide already loaded city siblings',()=>{
  const pending=new Promise(()=>{});
  function WaitingVehicle(){throw pending;}
  const html=renderToString(createElement('section',null,
    createElement('span',{'data-ready':'ground'},'Chão carregado'),
    createElement(CityAssetBoundary,{label:'veículo lento'},createElement(WaitingVehicle)),
    createElement('span',{'data-ready':'player'},'Personagem carregado')));
  assert.match(html,/data-ready="ground"/);
  assert.match(html,/data-ready="player"/);
  assert.doesNotMatch(html,/Carregando cidade/);
});

test('a ready optional model renders its own geometry content',()=>{
  const html=renderToString(createElement(CityAssetBoundary,{label:'banco'},createElement('span',null,'Banco carregado')));
  assert.match(html,/Banco carregado/);
});
