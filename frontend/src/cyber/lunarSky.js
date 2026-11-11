const RAD = Math.PI / 180;

export function moonOrbitAngle(elapsedSeconds, dayPeriodSeconds, moon) {
  const lunarPeriod = dayPeriodSeconds * moon.periodEarthDays;
  return ((elapsedSeconds % lunarPeriod) / lunarPeriod * 360 + moon.phaseDeg) * RAD;
}

export function cityMoonOffset(clock, distance) {
  if (!clock.night) return null;

  const hour = clock.hour + clock.minute / 60;
  const progress = ((hour + 6) % 24) / 12;
  const azimuth = (-180 + progress * 116) * RAD;
  const altitude = (8 + Math.sin(progress * Math.PI) * 14) * RAD;
  const horizontal = Math.cos(altitude) * distance;
  return [Math.cos(azimuth) * horizontal, Math.sin(altitude) * distance, Math.sin(azimuth) * horizontal];
}
