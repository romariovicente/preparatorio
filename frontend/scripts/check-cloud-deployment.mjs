import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {createDeploymentConfig} from '../src/config/deploymentConfig.js';

const manifest=JSON.parse(readFileSync(new URL('../src/config/cloudAssetManifest.json',import.meta.url),'utf8'));
const references=new Set();
function visit(directory){for(const entry of readdirSync(directory,{withFileTypes:true})){const path=join(directory,entry.name);if(entry.isDirectory())visit(path);else if(/\.(js|jsx|json)$/.test(path)&&!path.endsWith('.test.js')&&!path.endsWith('cloudAssetManifest.json')&&!path.endsWith('deploymentConfig.js'))for(const match of readFileSync(path,'utf8').matchAll(/["'](\/assets\/[^"']+)["']/g))references.add(match[1]);}}
visit('src');
const config=createDeploymentConfig({basePath:process.env.VITE_BASE_PATH||'/',assetBaseUrl:process.env.VITE_ASSET_BASE_URL,apiBaseUrl:process.env.VITE_API_BASE_URL,development:false,manifest});
if(process.env.VITE_EXTERNAL_ASSETS_ONLY!=='true')throw new Error('O build Pages deve definir VITE_EXTERNAL_ASSETS_ONLY=true para não copiar os modelos pesados.');
const missing=[];
let withheld=0;
for(const path of references){
  const resolved=config.assetUrl(path);
  if(resolved===null){withheld++;continue;}
  if(typeof resolved!=='string'||!resolved.startsWith('https://'))missing.push(path);
}
if(missing.length)throw new Error(`Faltam URLs HTTPS para ${missing.length} arquivos do acervo: ${missing.slice(0,8).join(', ')}`);
console.log(`Cloud configuration verified: ${references.size} referenced files, ${withheld} explicitly withheld; API ${config.apiBaseUrl?'configured':'disabled (local exploration only)'}.`);
