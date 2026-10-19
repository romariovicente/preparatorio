import {copyFileSync,existsSync,statSync,readdirSync} from 'node:fs';
import {join} from 'node:path';

copyFileSync('dist/index.html','dist/404.html');
if(existsSync('public/favicon.svg'))copyFileSync('public/favicon.svg','dist/favicon.svg');
function bytes(directory){return readdirSync(directory,{withFileTypes:true}).reduce((size,entry)=>size+(entry.isDirectory()?bytes(join(directory,entry.name)):statSync(join(directory,entry.name)).size),0);}
const total=bytes('dist');
if(total>900*1024*1024)throw new Error('O artefato Pages excedeu o limite interno de segurança (900 MiB).');
console.log(`Pages artifact: ${total} bytes. Binary models are served separately.`);
