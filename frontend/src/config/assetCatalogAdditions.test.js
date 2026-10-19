import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,realpathSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Buffer} from 'node:buffer';
import {isAbsolute,relative,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Texture} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const readJson=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const additions=readJson('./suppliedAdditions20261016.json');
const historical=['suppliedAssets.json','riggedAssets.json','mixamoAssets.json','monumentAssets.json','newDeliveryAssets.json'].flatMap(name=>readJson('./'+name));
const validated=additions.filter(asset=>asset.status==='validated');
const publicRoot=realpathSync(fileURLToPath(new URL('../../public/',import.meta.url)));
const shaPattern=/^[a-f0-9]{64}$/i;
const legacySpecularGlossiness='KHR_materials_pbrSpecularGlossiness';
const pbrFauna=new Set(['FOX','LIONESS','RABBIT','WOLF','HORSE'].map(name=>'FAUNA_'+name+'_20261016'));
// Resolve the actual installed loader plugins, plus its non-plugin handlers.
// The private preview does not configure Draco, KTX2 or Meshopt decoders.
const supportedRequiredExtensions=new Set(new GLTFLoader().pluginCallbacks.map(factory=>factory({}).name));
for(const name of ['KHR_materials_unlit','KHR_texture_transform','KHR_mesh_quantization'])supportedRequiredExtensions.add(name);
for(const name of ['KHR_texture_basisu','KHR_draco_mesh_compression','KHR_meshopt_compression','EXT_meshopt_compression'])supportedRequiredExtensions.delete(name);

function publicFile(url,label){
  assert.equal(typeof url,'string',label+' URL');
  const decoded=decodeURIComponent(url);
  assert.ok(decoded.startsWith('/assets/'),label+' must be a local asset URL');
  assert.ok(!/[?#\\\0]/.test(decoded),label+' URL cannot contain query, fragment or backslash');
  assert.ok(!decoded.split('/').some(part=>part==='..'||part==='.'||part.includes(':')),label+' URL cannot traverse directories');
  const path=realpathSync(resolve(publicRoot,'.'+decoded)),within=relative(publicRoot,path);
  assert.ok(within&&!within.startsWith('..')&&!isAbsolute(within),label+' must stay inside public');
  assert.ok(statSync(path).isFile(),label+' must exist as a file');
  return path;
}

function deliveredGlb(asset){
  const bytes=readFileSync(publicFile(asset.url,asset.id));
  assert.equal(bytes.length,asset.bytes,asset.id+' byte count');
  assert.equal(createHash('sha256').update(bytes).digest('hex'),asset.sha256.toLowerCase(),asset.id+' SHA-256');
  assert.ok(bytes.length>=20,asset.id+' GLB header');
  assert.equal(bytes.toString('ascii',0,4),'glTF',asset.id+' GLB magic');
  assert.equal(bytes.readUInt32LE(4),2,asset.id+' GLB version');
  assert.equal(bytes.readUInt32LE(8),bytes.length,asset.id+' GLB declared length');
  let offset=12,document=null,binaryLength=0;
  while(offset<bytes.length){
    assert.ok(offset+8<=bytes.length,asset.id+' chunk header');
    const length=bytes.readUInt32LE(offset),type=bytes.readUInt32LE(offset+4),end=offset+8+length;
    assert.equal(length%4,0,asset.id+' aligned chunk');
    assert.ok(end<=bytes.length,asset.id+' complete chunk');
    if(offset===12){
      assert.equal(type,0x4e4f534a,asset.id+' first chunk must be JSON');
      document=JSON.parse(bytes.toString('utf8',offset+8,end));
    }else if(type===0x004e4942)binaryLength+=length;
    offset=end;
  }
  assert.equal(offset,bytes.length,asset.id+' chunk boundaries');
  assert.equal(document.asset.version,'2.0',asset.id+' glTF version');
  for(const extension of document.extensionsRequired??[])assert.ok(supportedRequiredExtensions.has(extension),asset.id+' unsupported required extension: '+extension);
  assert.ok(!(document.extensionsUsed??[]).includes(legacySpecularGlossiness),asset.id+' legacy SpecularGlossiness must be converted');
  assert.ok(!(document.extensionsRequired??[]).includes(legacySpecularGlossiness),asset.id+' legacy SpecularGlossiness cannot be required');
  for(const material of document.materials??[])assert.equal(material.extensions?.[legacySpecularGlossiness],undefined,asset.id+' unsupported SpecularGlossiness material');
  assert.ok(document.meshes?.length&&document.scenes?.[document.scene??0]?.nodes?.length,asset.id+' renderable scene');
  for(const resource of [...document.buffers??[],...document.images??[]])assert.equal(resource.uri,undefined,asset.id+' resources must be embedded, without external URI');
  for(const buffer of document.buffers??[])assert.ok(Number.isInteger(buffer.byteLength)&&buffer.byteLength>0&&buffer.byteLength<=binaryLength,asset.id+' embedded binary buffer');
  for(const view of document.bufferViews??[]){
    const buffer=document.buffers?.[view.buffer];
    assert.ok(buffer&&(view.byteOffset??0)>=0&&view.byteLength>=0&&(view.byteOffset??0)+view.byteLength<=buffer.byteLength,asset.id+' buffer view bounds');
  }
  for(const mesh of document.meshes)for(const primitive of mesh.primitives){
    assert.ok(document.accessors?.[primitive.attributes?.POSITION]?.count>0,asset.id+' mesh position accessor');
  }
  return document;
}

test('validated additions have unique identities and hashes outside the historical catalog',()=>{
  assert.ok(Array.isArray(additions));
  assert.ok(validated.length>0,'Publish at least one validated addition before final verification');
  const ids=new Set(historical.map(asset=>asset.id));
  const hashes=new Set(historical.flatMap(asset=>[asset.sha256,asset.sourceSha256]).filter(Boolean).map(hash=>hash.toLowerCase()));
  for(const asset of validated){
    assert.equal(typeof asset.id,'string');assert.ok(asset.id.length&&!ids.has(asset.id),asset.id+' duplicate ID');
    assert.match(asset.sha256,shaPattern,asset.id+' export hash');
    const keys=[asset.sha256,asset.sourceSha256].filter(Boolean).map(hash=>hash.toLowerCase());
    for(const key of keys){assert.match(key,shaPattern);assert.ok(!hashes.has(key),asset.id+' duplicates an existing export or source');}
    ids.add(asset.id);keys.forEach(key=>hashes.add(key));
    assert.ok(Number.isSafeInteger(asset.bytes)&&asset.bytes>0,asset.id+' positive byte count');
  }
});

test('the five converted fauna retain embedded base-color textures and a core PBR fallback',()=>{
  for(const asset of validated.filter(entry=>pbrFauna.has(entry.id))){
    const glb=deliveredGlb(asset);
    assert.ok(glb.materials?.length,asset.id+' textured materials');
    for(const material of glb.materials){
      const pbr=material.pbrMetallicRoughness,index=pbr?.baseColorTexture?.index;
      assert.ok(pbr&&Number.isInteger(index),asset.id+' core PBR baseColorTexture');
      const texture=glb.textures?.[index],image=glb.images?.[texture?.source];
      assert.ok(image&&Number.isInteger(image.bufferView)&&glb.bufferViews?.[image.bufferView]?.byteLength>0,asset.id+' embedded base-color image data');
      assert.equal(image.uri,undefined,asset.id+' local base-color image');
      assert.match(image.mimeType,/^image\/(png|jpeg|webp)$/i,asset.id+' supported base-color image format');
      assert.equal(pbr.metallicFactor,0,asset.id+' nonmetallic core fallback');
      assert.ok(Number.isFinite(pbr.roughnessFactor)&&pbr.roughnessFactor>=0&&pbr.roughnessFactor<=1,asset.id+' core roughness');
      assert.equal(material.extensions?.KHR_materials_specular?.specularFactor,0,asset.id+' zero specular intensity');
      assert.equal(material.extensions?.KHR_materials_specular?.specularTexture,undefined,asset.id+' no unsupported specular/glossiness texture mapping');
    }
  }
});

async function cpuMaterials(glb,coreOnly=false){
  // Only the serialized material definitions are passed to the real local
  // loader. Texture placeholders avoid DOM/image decoding and GPU rendering.
  const materials=structuredClone(glb.materials),textures=[];
  if(coreOnly)for(const material of materials)if(material.extensions)delete material.extensions.KHR_materials_specular;
  const document={asset:{version:'2.0'},scene:0,scenes:[{nodes:[]}],nodes:[],materials,
    textures:glb.textures,images:glb.images,samplers:glb.samplers,
    extensionsUsed:(glb.extensionsUsed??[]).filter(name=>!coreOnly||name!=='KHR_materials_specular'),
    extensionsRequired:(glb.extensionsRequired??[]).filter(name=>!coreOnly||name!=='KHR_materials_specular')};
  const loader=new GLTFLoader().register(()=>({name:'PREP_TEST_TEXTURE_PLACEHOLDERS',loadTexture(index){
    const texture=new Texture();texture.userData.sourceTextureIndex=index;textures.push(texture);
    return Promise.resolve(texture);
  }}));
  const parsed=await loader.parseAsync(JSON.stringify(document),'');
  const loaded=await parsed.parser.getDependencies('material');
  return {materials:loaded,dispose:()=>{loaded.forEach(material=>material.dispose());textures.forEach(texture=>texture.dispose());}};
}

test('local Three loader connects converted fauna color maps and preserves the core-only fallback without a DOM',async()=>{
  for(const asset of validated.filter(entry=>pbrFauna.has(entry.id))){
    const glb=deliveredGlb(asset);
    for(const coreOnly of [false,true]){
      const result=await cpuMaterials(glb,coreOnly);
      try{
        assert.equal(result.materials.length,glb.materials.length,asset.id+' material count');
        for(const [index,material] of result.materials.entries()){
          assert.ok(material.isMeshStandardMaterial,asset.id+' supported PBR material');
          assert.ok(material.map?.isTexture,asset.id+' base-color map is connected by the loader');
          assert.equal(material.map.userData.sourceTextureIndex,glb.materials[index].pbrMetallicRoughness.baseColorTexture.index,asset.id+' original base-color texture reference');
          assert.equal(material.metalness,0,asset.id+' nonmetallic fallback');
          if(!coreOnly)assert.equal(material.specularIntensity,0,asset.id+' installed specular extension applied');
        }
      }finally{result.dispose();}
    }
  }
});

test('addition GLB bytes, embedded resources, preview and declared motion match the delivered files',()=>{
  for(const asset of validated){
    const glb=deliveredGlb(asset),animations=glb.animations??[],clips=animations.map(animation=>animation.name);
    assert.ok(Array.isArray(asset.animations),asset.id+' explicit animation list');
    assert.ok(asset.animations.every(name=>typeof name==='string'&&name.length),asset.id+' named animation list');
    assert.equal(new Set(asset.animations).size,asset.animations.length,asset.id+' unique clip names');
    assert.deepEqual([...clips].sort(),[...asset.animations].sort(),asset.id+' actual exported clip names');
    assert.equal(typeof asset.rigged,'boolean',asset.id+' explicit rig state');
    assert.equal(asset.rigged,Boolean(glb.skins?.length),asset.id+' actual exported skin state');
    if(typeof asset.animated==='boolean')assert.equal(asset.animated,animations.length>0,asset.id+' actual animation state');
    for(const node of glb.nodes??[])if(node.skin!==undefined){
      const skin=glb.skins?.[node.skin];
      assert.ok(skin?.joints?.length&&skin.joints.every(index=>glb.nodes[index]),asset.id+' skin joints');
      assert.ok(glb.meshes[node.mesh],asset.id+' skinned mesh reference');
      for(const primitive of glb.meshes[node.mesh].primitives){
        const positions=glb.accessors[primitive.attributes.POSITION];
        const weights=glb.accessors[primitive.attributes.WEIGHTS_0],joints=glb.accessors[primitive.attributes.JOINTS_0];
        assert.equal(weights?.count,positions.count,asset.id+' vertex weights');
        assert.equal(joints?.count,positions.count,asset.id+' vertex joint indices');
      }
    }
    const preview=readFileSync(publicFile(asset.preview,asset.id+' preview'));
    assert.ok(preview.length>100,asset.id+' nonempty rendered preview');
    assert.ok(preview.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))||
      preview.subarray(0,3).equals(Buffer.from([255,216,255]))||
      (preview.toString('ascii',0,4)==='RIFF'&&preview.toString('ascii',8,12)==='WEBP'),asset.id+' image preview signature');
    if(asset.playable){
      assert.ok(asset.rigged&&asset.reimportValidated,asset.id+' playable rig must be validated');
      assert.ok(clips.some(name=>/idle/i.test(name))&&clips.some(name=>/walk/i.test(name)),asset.id+' playable Idle and Walk clips');
    }
  }
});
