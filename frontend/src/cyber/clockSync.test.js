import test from 'node:test';
import assert from 'node:assert/strict';
import {createServerClockAnchor,readClockAnchor} from './clockSync.js';
import {sampleWorldClock} from './simulation.js';

test('server clock advances monotonically after network offset correction',()=>{
  const anchor=createServerClockAnchor(1000000,10,110);
  assert.deepEqual(anchor,{wallMs:1000050,monotonicMs:110});
  assert.equal(readClockAnchor(anchor,1110),1001050);
  assert.equal(readClockAnchor(anchor,0),1000050);
  assert.equal(createServerClockAnchor(NaN,10,20),null);
  assert.equal(createServerClockAnchor(100,20,10),null);
});
test('Brasília wall time and sky agree for players with different session ages',()=>{
  const config={clockMode:'server-wall',nowMs:Date.parse('2026-10-05T17:34:56Z'),epochMs:Date.parse('2026-01-01T00:00:00Z'),timeZone:'America/Sao_Paulo',orbitPeriodSeconds:120};
  const fresh=sampleWorldClock(0,config),other=sampleWorldClock(933,config);
  assert.deepEqual(fresh,other);assert.equal(fresh.text,'14:34');assert.equal(fresh.dateText,'05/10/2026');assert.equal(fresh.phase,'Tarde');
  assert.equal(sampleWorldClock(0,{...config,nowMs:Date.parse('2026-10-06T03:00:00Z')}).text,'00:00');
  assert.equal(sampleWorldClock(0,{...config,nowMs:Date.parse('2026-10-06T03:00:00Z')}).night,true);
  const cycle=sampleWorldClock(0,{...config,nowMs:config.nowMs+120000});
  assert.ok(Math.abs(cycle.earthAngle-fresh.earthAngle)<1e-8);
});
