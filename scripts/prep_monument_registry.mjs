import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const reports=[JSON.parse(fs.readFileSync(path.join(root,'reports/florence_monument_validation_20261005.json'),'utf8')),JSON.parse(fs.readFileSync(path.join(root,'reports/brain_real_20261005/brain_real_validation.json'),'utf8'))];
const definitions=[{id:'PROP_Florence_Nightingale_Real_20261005',name:'Florence Nightingale · monumento',height:6.6,positions:[[-23,.01,3],[22,.01,-16],[24,.01,-22],[-55,.01,-32]],hidePrefixes:['STAT_Nightingale'],license:'CC-BY-NC-SA-4.0',author:'Scan-the-World',source:'https://zenodo.org/records/21163474'},{id:'PROP_Brain_Real_20261005',name:'Cérebro · Praça do Conhecimento',height:6,positions:[[0,3.1,0]],hidePrefixes:['PLAZA_BrainHemisphere','PLAZA_BrainFold'],license:'CC-BY-4.0',author:'Human Reference Atlas / Allen Institute',source:'https://humanatlas.io/3d-reference-library'}];
const entries=definitions.map((d,i)=>{
  const file=path.join(root,'frontend/public/assets/monuments',d.id+'.glb'),bytes=fs.readFileSync(file),sha256=crypto.createHash('sha256').update(bytes).digest('hex');
  const expected=reports[i].glb?.sha256??reports[i].sha256;
  if(!expected||expected!==sha256)throw Error('Hash mismatch '+d.id);
  if(!(reports[i].actualGlbReimport?.passed||reports[i].reimportValidated))throw Error('Actual reimport unverified '+d.id);
  if(bytes.toString('ascii',0,4)!=='glTF')throw Error('Invalid asset '+d.id);
  return {...d,url:'/assets/monuments/'+d.id+'.glb',bytes:bytes.length,sha256,category:'Monumentos',reimportValidated:true,status:'validated',rigged:false,playable:false,animations:[],credits:{author:d.author,license:d.license,source:d.source}};
});
fs.writeFileSync(path.join(root,'frontend/src/config/monumentAssets.json'),JSON.stringify(entries,null,2)+'\n');
console.log(JSON.stringify(entries.map(({id,bytes,sha256})=>({id,bytes,sha256}))));
