import test from 'node:test';
import assert from 'node:assert/strict';
import {BoxGeometry, DoubleSide, Group, Mesh, MeshBasicMaterial, PlaneGeometry, Raycaster} from 'three';
import {collectGroundSurfaces, isWalkableSurface, sampleGroundHeight} from './groundSupport.js';

function floor(name, y, {x=0, z=0, width=4, depth=4, walkable=false}={}) {
  const mesh = new Mesh(new PlaneGeometry(width, depth), new MeshBasicMaterial({side:DoubleSide}));
  mesh.name = name;
  mesh.position.set(x, y, z);
  mesh.rotation.x = -Math.PI / 2;
  mesh.userData.walkable = walkable;
  return mesh;
}

function sample(scene, position={x:0,y:0,z:0}, options) {
  return sampleGroundHeight(new Raycaster(), collectGroundSurfaces(scene), position, options);
}

test('support footprint reaches a 22cm curb missed by the centre ray', () => {
  const scene = new Group();
  scene.add(floor('ENV_ARAP_UrbanPlate', .01));
  scene.add(floor('ROAD_sidewalk', .23, {x:.38,width:.5}));
  assert.ok(Math.abs(sample(scene, undefined, {radius:0}) - .01) < 1e-6);
  assert.ok(Math.abs(sample(scene) - .23) < 1e-6);
});

test('ground whitelist includes explicit floors and excludes road markings and furniture', () => {
  for (const name of ['ENV_ARAP_Base','ENV_ARAP_UrbanPlate','ROAD_ASPHALT','UNDERGROUND_Floor_room','BLD_UndergroundInterior_Floor']) {
    assert.equal(isWalkableSurface(floor(name, 0)), true, name);
  }
  for (const name of ['ROAD_white','ROAD_CentreLine','ROAD_MARK_arrow','PROP_Bench','BLD_Roof']) {
    assert.equal(isWalkableSurface(floor(name, 0)), false, name);
  }
  assert.equal(isWalkableSurface(floor('Classroom_floor', 0, {walkable:true})), true);
  assert.equal(isWalkableSurface(new Group()), false);
});

test('a hidden parent prevents its otherwise visible floor from supporting the player', () => {
  const scene = new Group(), hidden = new Group();
  hidden.visible = false;
  hidden.add(floor('ROAD_hidden', 2.2));
  scene.add(hidden);
  assert.equal(sample(scene, {x:0,y:2,z:0}), 2);
});

test('world face normals reject steep walls and downward facing undersides', () => {
  const scene = new Group(), steep = floor('ROAD_steep', .2), inverted = new Group();
  steep.rotation.x = -.2;
  inverted.rotation.z = Math.PI;
  const underside = floor('ROAD_inverted_parent', .2);
  underside.position.y = -.2;
  inverted.add(underside);
  scene.add(steep, inverted);
  assert.equal(sample(scene), 0);
});

test('an inverted double-sided slab cannot support the player on its hidden bottom face', () => {
  const scene = new Group(), geometry = new BoxGeometry(2, .3, 2);
  geometry.scale(1, -1, 1);
  const inverted = new Mesh(geometry, new MeshBasicMaterial({side:DoubleSide}));
  inverted.name = 'BLD_UndergroundInterior_Floor';
  inverted.position.y = 2.05;
  scene.add(inverted);
  assert.equal(sample(scene, {x:0,y:2,z:0}), 2);
});

test('steps and drops outside the allowed range do not change the baseline', () => {
  const scene = new Group();
  scene.add(floor('ROAD_too_high', .6), floor('UNDERGROUND_Floor_too_deep', -.8));
  assert.equal(sample(scene), 0);
  assert.ok(Math.abs(sample(scene, undefined, {maxStep:.7}) - .6) < 1e-6);
});

test('underground ground is sampled around the current depth rather than the street above it', () => {
  const scene = new Group();
  scene.add(floor('ENV_ARAP_Base', 0), floor('UNDERGROUND_Floor', -4.02));
  assert.ok(Math.abs(sample(scene, {x:0,y:-4,z:0}) + 4.02) < 1e-6);
});

test('normal matrices retain valid slopes under nonuniform parent scaling', () => {
  const scene = new Group(), transformed = new Group(), slope = floor('ROAD_scaled_slope', .1);
  transformed.scale.set(2, 3, 6);
  slope.rotation.x = -Math.PI / 3;
  transformed.add(slope);
  scene.add(transformed);
  assert.ok(Math.abs(sample(scene, undefined, {radius:0}) - .3) < 1e-6);
});

test('normal matrices reject a slope made too steep by nonuniform scaling', () => {
  const scene = new Group(), transformed = new Group(), slope = floor('ROAD_steepened_slope', .1);
  transformed.scale.set(2, 3, .5);
  slope.rotation.x = -Math.PI / 3;
  transformed.add(slope);
  scene.add(transformed);
  assert.equal(sample(scene, undefined, {radius:0}), 0);
});

test('sampling preserves the caller ray distance settings and falls back when no ground exists', () => {
  const scene = new Group(), ray = new Raycaster();
  ray.near = .2;
  ray.far = 20;
  assert.equal(sampleGroundHeight(ray, collectGroundSurfaces(scene), {x:0,y:3,z:0}), 3);
  assert.equal(ray.near, .2);
  assert.equal(ray.far, 20);
});
