// Convert the server timestamp at response reception into a monotonic anchor.
// Half the measured round trip estimates the remaining response travel time.
export function createServerClockAnchor(serverTimeMs,startedAt,receivedAt) {
  if(![serverTimeMs,startedAt,receivedAt].every(Number.isFinite)||receivedAt<startedAt||Math.abs(serverTimeMs)>8.64e15)return null;
  return {wallMs:serverTimeMs+(receivedAt-startedAt)/2,monotonicMs:receivedAt};
}
export function readClockAnchor(anchor,monotonicNow) {
  return anchor.wallMs+Math.max(0,monotonicNow-anchor.monotonicMs);
}
