import test from 'node:test';
import assert from 'node:assert/strict';
import {createDeploymentConfig} from './deploymentConfig.js';

test('Pages subpath preserves asset paths, query fragments and app navigation',()=>{
  const config=createDeploymentConfig({basePath:'/preparatorio/'});
  assert.equal(config.assetUrl('/assets/characters/a.glb'),'/preparatorio/assets/characters/a.glb');
  assert.equal(config.assetUrl('/assets/knowledge/book.pdf#page=5'),'/preparatorio/assets/knowledge/book.pdf#page=5');
  assert.equal(config.applicationPath('hospital-preview'),'/preparatorio/hospital-preview');
  assert.equal(config.relativeApplicationPath('/preparatorio/hospital-preview'),'/hospital-preview');
  assert.equal(config.applicationPath(''),'/preparatorio/');
});
test('production uses per-file HTTPS shard mapping and preserves non-asset metadata',()=>{
  const config=createDeploymentConfig({basePath:'/preparatorio/',manifest:{'/assets/a.glb':'https://example.github.io/assets-1/a.glb','/assets/book.pdf':null}});
  assert.equal(config.assetUrl('/assets/a.glb'),'https://example.github.io/assets-1/a.glb');
  assert.equal(config.assetUrl('/assets/book.pdf'),null);
  const input={url:'/assets/a.glb',credits:{source:'https://sketchfab.com/model',license:'CC-BY'},parts:[{preview:'/assets/preview.png'}]};
  assert.deepEqual(config.resolveAssetReferences(input),{url:'https://example.github.io/assets-1/a.glb',credits:input.credits,parts:[{preview:'/preparatorio/assets/preview.png'}]});
  assert.equal(input.url,'/assets/a.glb');
});
test('external asset prefix is supported and mappings take precedence',()=>{
  const config=createDeploymentConfig({assetBaseUrl:'https://cdn.example/assets/',manifest:{'/assets/a.glb':'https://shard.example/a.glb'}});
  assert.equal(config.assetUrl('/assets/b.glb'),'https://cdn.example/assets/b.glb');
  assert.equal(config.assetUrl('/assets/a.glb'),'https://shard.example/a.glb');
});
test('public site does not call localhost, and APIs require HTTPS without credentials',()=>{
  assert.equal(createDeploymentConfig({hostname:'romariovicente.github.io'}).apiUrl('/health'),null);
  assert.equal(createDeploymentConfig({development:true,hostname:'127.0.0.1'}).apiUrl('/health'),'http://127.0.0.1:5180/health');
  assert.equal(createDeploymentConfig({development:true,hostname:'my-codespace.github.dev'}).apiUrl('/health'),null);
  assert.equal(createDeploymentConfig({apiBaseUrl:'https://api.example/prep/'}).apiUrl('/health'),'https://api.example/prep/health');
  for(const apiBaseUrl of ['http://api.example','https://localhost','https://u:secret@api.example','https://api.example?token=secret'])assert.throws(()=>createDeploymentConfig({apiBaseUrl}));
  assert.throws(()=>createDeploymentConfig({basePath:'//evil.example/'}));
});
test('development continues to resolve local files even when cloud mappings exist',()=>{
  const config=createDeploymentConfig({development:true,manifest:{'/assets/a.glb':'https://shard.example/a.glb','/assets/book.pdf':null}});
  assert.equal(config.assetUrl('/assets/a.glb'),'/assets/a.glb');
  assert.equal(config.assetUrl('/assets/book.pdf'),'/assets/book.pdf');
});
test('per-file mapping retains reader pages and query strings, including withheld variants',()=>{
  const config=createDeploymentConfig({manifest:{'/assets/book.pdf':'https://cdn.example/book.pdf','/assets/private.pdf':null}});
  assert.equal(config.assetUrl('/assets/book.pdf#page=22'),'https://cdn.example/book.pdf#page=22');
  assert.equal(config.assetUrl('/assets/book.pdf?v=2#page=22'),'https://cdn.example/book.pdf?v=2#page=22');
  assert.equal(config.assetUrl('/assets/private.pdf#page=22'),null);
});
