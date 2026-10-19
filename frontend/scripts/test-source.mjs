import {readdirSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';

const files=[];
function visit(directory){for(const entry of readdirSync(directory,{withFileTypes:true})){const path=join(directory,entry.name);if(entry.isDirectory())visit(path);else if(path.endsWith('.test.js'))files.push(path);}}
visit('src');
// Binary model checks remain mandatory in the local full `npm test` suite.
// Cloud source CI does not fetch multiple gigabytes on every code commit.
const sourceTests=files.filter(path=>!/(?:readFileSync|statSync|realpathSync|existsSync)/.test(readFileSync(path,'utf8')));
console.log(`Source CI: ${sourceTests.length} test files; ${files.length-sourceTests.length} file/asset suites reserved for full local verification.`);
const result=spawnSync(process.execPath,['--test',...sourceTests],{stdio:'inherit'});
process.exit(result.status??1);
