import assert from 'node:assert/strict';
import test from 'node:test';
import solar from '../config/solarSystem.json' with {type:'json'};
import {cityMoonOffset, moonOrbitAngle} from './lunarSky.js';
import {sampleWorldClock, WORLD_CLOCK_DEFAULTS} from './simulation.js';

function localClockAt(time) {
  return sampleWorldClock(0, {
    ...WORLD_CLOCK_DEFAULTS,
    clockMode:'server-wall',
    nowMs:Date.parse(`2026-11-11T${time}:00-03:00`),
  });
}

test('the city moon follows the night arc above the horizon and disappears at dawn', () => {
  const distance=solar.moon.cityDistance;
  const dusk=cityMoonOffset(localClockAt('18:00'),distance);
  const midnight=cityMoonOffset(localClockAt('00:00'),distance);
  const dawn=cityMoonOffset(localClockAt('05:59'),distance);
  for(const offset of [dusk,midnight,dawn]) {
    assert.ok(Math.abs(Math.hypot(...offset)-distance)<1e-8);
    assert.ok(offset[1]>0);
  }
  assert.ok(midnight[1]>dusk[1]&&midnight[1]>dawn[1]);
  assert.notEqual(dusk[2],dawn[2]);
  assert.equal(cityMoonOffset(localClockAt('06:00'),distance),null);
  assert.equal(cityMoonOffset(localClockAt('12:00'),distance),null);
});

test('the planetarium moon completes one orbit per configured lunar period', () => {
  const day=WORLD_CLOCK_DEFAULTS.dayPeriodSeconds;
  const moon=solar.moon;
  const period=day*moon.periodEarthDays;
  const initial=moonOrbitAngle(0,day,moon);
  const halfCycle=moonOrbitAngle(period/2,day,moon);
  assert.ok(Math.abs(halfCycle-initial-Math.PI)<1e-8);
  assert.equal(moonOrbitAngle(period,day,moon),initial);
  assert.ok(moon.orbitRadius>solar.planets.find(planet=>planet.id==='earth').radius+moon.radius);
});
