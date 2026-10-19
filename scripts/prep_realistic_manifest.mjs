import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
const root=fileURLToPath(new URL('..',import.meta.url));
const catalog=JSON.parse(readFileSync(resolve(root,'frontend/src/config/suppliedAssets.json'),'utf8'));
function asset(id){
  const row=catalog.find(a=>a.id===id);
  if(!row||row.status!=='validated')throw new Error('Unvalidated supplied model '+id);
  const path=resolve(root,'frontend/public',row.url.slice(1));
  if(!existsSync(path))throw new Error('Missing model '+id);
  const bytes=readFileSync(path),sha256=createHash('sha256').update(bytes).digest('hex');
  if(bytes.length!==row.bytes||sha256!==row.sha256)throw new Error('Changed model '+id);
  return {sourceId:id,url:row.url,bytes:bytes.length,sha256,credits:row.credits,licenseStatus:row.licenseStatus};
}
const environmentReplacements=[];
for(const [i,z] of [-25,-66,70].entries())environmentReplacements.push({id:'real-residence-'+i,...asset('SUP_cyberpunk_background_appartment_building'),height:30,position:[-80,3.9,z],rotation:[0,0,0],hidePrefixes:i===0?Array.from({length:9},(_,n)=>'BLD_Residential_'+n+'_'):[]});
for(const [id,source,height,position,heading] of [
  ['hospital-sports','SUP_2010_mercedes_sls_amg',1.26,[15,.1,-54.2],Math.PI/2],
  ['hospital-suv','SUP_volkswagen_atlas_teramont_cross_sport_2025',1.73,[15,.1,-46.2],Math.PI/2],
  ['store-car','SUP_2010_mercedes_sls_amg',1.26,[-34,0,43],0],
  ['moto-showcase','SUP_cyberpunk_kawasaki_ninja',1.3,[-43,0,55],0],
  ['dealer-sports','SUP_2010_mercedes_sls_amg',1.26,[62,0,56],Math.PI/2],
  ['dealer-suv','SUP_volkswagen_atlas_teramont_cross_sport_2025',1.73,[71,0,56],0],
])environmentReplacements.push({id,...asset(source),height,position,rotation:[0,heading,0],hidePrefixes:[]});
const manifest={version:1,author:'Romario Vicente Amaro',validatedSourceCatalog:true,
  environmentReplacements,dynamicReplacements:{mototaxi:{...asset('SUP_cyberpunk_kawasaki_ninja'),height:1.3},truck:{...asset('SUP_volvo_concept_truck'),height:1.8},car:{...asset('SUP_2010_mercedes_sls_amg'),height:1.26}},
  status:'Detailed supplied residences and vehicles; remaining environments are still being adapted to realism.'};
writeFileSync(resolve(root,'frontend/src/config/realisticWorldManifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({placements:environmentReplacements.length,dynamicVehicles:Object.keys(manifest.dynamicReplacements),sourceFilesVerified:true}));
