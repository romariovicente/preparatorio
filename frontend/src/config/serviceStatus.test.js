import test from 'node:test';
import assert from 'node:assert/strict';
import {clockSourceLabel,sharedServiceLabel} from './serviceStatus.js';

test('clock labels distinguish device fallback, pending, stale and confirmed service time',()=>{
  assert.match(clockSourceLabel('unavailable'),/deste dispositivo/);
  assert.match(clockSourceLabel('connecting'),/consultando/);
  assert.match(clockSourceLabel('stale'),/último horário recebido/);
  assert.match(clockSourceLabel('synced'),/sincronizado com o serviço PREPARATÓRIO/);
  for(const state of ['unavailable','connecting','stale','synced'])assert.doesNotMatch(clockSourceLabel(state),/JARVIS/);
});
test('offline exploration does not count the visitor as a connected multiplayer session',()=>{
  assert.match(sharedServiceLabel('offline',20),/Exploração individual/);
  assert.doesNotMatch(sharedServiceLabel('offline',20),/20|jogadores/);
  assert.equal(sharedServiceLabel('connected',1),'1 jogador na sala compartilhada');
  assert.equal(sharedServiceLabel('connected',3),'3 jogadores na sala compartilhada');
});
