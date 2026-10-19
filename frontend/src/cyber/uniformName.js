import {CanvasTexture, SRGBColorSpace} from 'three';
import {normalizePlayerName} from '../network/playerIdentity.js';

export function uniformDisplayName(value) {
  return normalizePlayerName(value);
}

// This draws the player's own text. Supplied photos, logo and crest stay intact.
export function createUniformNameTexture(value) {
  const canvas = document.createElement('canvas');
  canvas.width = 1024; canvas.height = 384;
  const context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#aa7629'; context.textAlign = 'center'; context.textBaseline = 'middle';
  context.font = 'italic 58px Georgia, serif';
  context.fillText('Técnico de Enfermagem', 512, 116, 950);
  const name = uniformDisplayName(value);
  let font = 76;
  do { context.font = `italic ${font}px Georgia, serif`; font -= 2; }
  while (context.measureText(name).width > 940 && font > 24);
  context.fillText(name, 512, 248, 950);
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace; texture.flipY = false;
  return texture;
}
